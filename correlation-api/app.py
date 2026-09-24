import os
import math
import re
from datetime import date, datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd

import yfinance as yf

from analysis.data_loader import load_pair_data, load_universe_data
from analysis.correlation import compute_lagged_correlation
from analysis.pair_model import validate_pair_model
from analysis.spread import calculate_spread_metrics
from analysis.risk import detect_correlation_breakdown
from analysis.universes import serialized_peer_groups
from analysis.peer_basket import DEFAULT_FORMATION_WINDOW, scan_peer_universe
from analysis.strategy_backtest import (
    DEFAULT_ANNUAL_BORROW_RATE,
    DEFAULT_GROSS_EXPOSURE,
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_PARTICIPATION_RATE,
    DEFAULT_TRANSACTION_COST_BPS,
    run_strategy_analysis,
)
from analysis.backtest import generate_zscore_signals, run_backtest

app = Flask(__name__)
CORS(app)

RISK_LOOKBACK_DAYS = 540
DEFAULT_SIGNAL_WINDOW = 60
MIN_STRATEGY_OBSERVATIONS = 504
MAX_STRATEGY_YEARS = 10
STRATEGY_TICKER_PATTERN = re.compile(r"^[A-Z0-9.-]{1,10}$")

PAIRS = [
    {"ticker_a": "MSFT",  "ticker_b": "GOOGL", "name_a": "Microsoft",         "name_b": "Google",            "sector": "Technology"},
    {"ticker_a": "AMD",   "ticker_b": "NVDA",  "name_a": "AMD",               "name_b": "NVIDIA",            "sector": "Technology"},
    {"ticker_a": "DDOG",  "ticker_b": "NET",   "name_a": "Datadog",           "name_b": "Cloudflare",         "sector": "Technology"},
    {"ticker_a": "CVS",   "ticker_b": "JNJ",   "name_a": "CVS Health",        "name_b": "Johnson & Johnson", "sector": "Healthcare"},
    {"ticker_a": "PFE",   "ticker_b": "MRK",   "name_a": "Pfizer",            "name_b": "Merck",             "sector": "Healthcare"},
    {"ticker_a": "CL",    "ticker_b": "KMB",   "name_a": "Colgate-Palmolive", "name_b": "Kimberly-Clark",    "sector": "Consumer"},
    {"ticker_a": "KO",    "ticker_b": "PEP",   "name_a": "Coca-Cola",         "name_b": "PepsiCo",           "sector": "Consumer"},
    {"ticker_a": "COST",  "ticker_b": "BJ",    "name_a": "Costco",            "name_b": "BJ's Wholesale",    "sector": "Consumer"},
    {"ticker_a": "GE",    "ticker_b": "BA",    "name_a": "GE Aerospace",      "name_b": "Boeing",            "sector": "Industrials"},
    {"ticker_a": "V",     "ticker_b": "MA",    "name_a": "Visa",              "name_b": "Mastercard",        "sector": "Financials"},
    {"ticker_a": "MS",    "ticker_b": "GS",    "name_a": "Morgan Stanley",    "name_b": "Goldman Sachs",     "sector": "Financials"},
    {"ticker_a": "JPM",   "ticker_b": "BAC",   "name_a": "JPMorgan Chase",    "name_b": "Bank of America",   "sector": "Financials"},
    {"ticker_a": "XOM",   "ticker_b": "CVX",   "name_a": "ExxonMobil",        "name_b": "Chevron",           "sector": "Energy"},
    {"ticker_a": "T",     "ticker_b": "VZ",    "name_a": "AT&T",              "name_b": "Verizon",           "sector": "Telecom"},
    {"ticker_a": "WMT",   "ticker_b": "TGT",   "name_a": "Walmart",           "name_b": "Target",            "sector": "Retail"},
]


def _safe_float(val):
    try:
        if pd.isna(val):
            return None
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _risk_start_date(end_date):
    try:
        parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("end must be in YYYY-MM-DD format") from exc
    return (parsed_end - timedelta(days=RISK_LOOKBACK_DAYS)).isoformat()


def _parse_integer_arg(name, default, minimum):
    raw_value = request.args.get(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc

    if value < minimum:
        comparator = "non-negative" if minimum == 0 else f"at least {minimum}"
        raise ValueError(f"{name} must be {comparator}")
    return value


def _parse_iso_date(value, name):
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be in YYYY-MM-DD format") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{name} must be in YYYY-MM-DD format")
    return parsed


def _validate_date_range(start, end):
    parsed_start = _parse_iso_date(start, "start")
    parsed_end = _parse_iso_date(end, "end")
    if parsed_start >= parsed_end:
        raise ValueError("start must be before end")


def _validate_pair(ticker_a, ticker_b):
    if not ticker_a or not ticker_b:
        raise ValueError("ticker_a and ticker_b are required")
    if ticker_a == ticker_b:
        raise ValueError("ticker_a and ticker_b must be different")


def _strategy_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object")
    return payload


def _strategy_tickers(payload):
    raw_tickers = payload.get("tickers")
    if not isinstance(raw_tickers, list):
        raise ValueError("tickers must be an array")
    tickers = []
    for raw_ticker in raw_tickers:
        if not isinstance(raw_ticker, str):
            raise ValueError("ticker symbols must be strings")
        ticker = str(raw_ticker).strip().upper()
        if not STRATEGY_TICKER_PATTERN.fullmatch(ticker):
            raise ValueError(f"Invalid ticker symbol: {ticker or '(empty)'}")
        if ticker not in tickers:
            tickers.append(ticker)
    if not 4 <= len(tickers) <= 8:
        raise ValueError("tickers must contain between 4 and 8 unique symbols")
    return tickers


def _strategy_dates(payload):
    today = date.today()
    default_start = today - timedelta(days=365 * 5 + 2)
    start = payload.get("start", default_start.isoformat())
    end = payload.get("end", today.isoformat())
    parsed_start = _parse_iso_date(start, "start")
    parsed_end = _parse_iso_date(end, "end")
    if parsed_start >= parsed_end:
        raise ValueError("start must be before end")
    if (parsed_end - parsed_start).days > 365 * MAX_STRATEGY_YEARS + 3:
        raise ValueError(f"Strategy date range cannot exceed {MAX_STRATEGY_YEARS} years")
    return start, end


def _strategy_error(message, code="invalid_request", status=400):
    return jsonify({"error": {"code": code, "message": str(message)}}), status


def _strategy_number(payload, name, default, minimum, maximum):
    raw_value = payload.get(name, default)
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _strategy_target_and_peers(payload):
    target = str(payload.get("target", "")).strip().upper()
    raw_peers = payload.get("peers")
    if not STRATEGY_TICKER_PATTERN.fullmatch(target):
        raise ValueError(f"Invalid target ticker: {target or '(empty)'}")
    if not isinstance(raw_peers, list):
        raise ValueError("peers must be an array")
    tickers = _strategy_tickers({"tickers": [target, *raw_peers]})
    if tickers[0] != target:
        raise ValueError("target must not also appear in peers")
    peers = [ticker for ticker in tickers if ticker != target]
    if len(peers) != len(raw_peers):
        raise ValueError("target and peers must be unique")
    return target, peers


def _valid_pair_rows(df, ticker_a, ticker_b):
    column_a = f"Close_{ticker_a}"
    column_b = f"Close_{ticker_b}"
    missing_columns = [column for column in (column_a, column_b) if column not in df]
    if missing_columns:
        raise ValueError("Pair data is missing required price columns")

    price_a = pd.to_numeric(df[column_a], errors="coerce")
    price_b = pd.to_numeric(df[column_b], errors="coerce")
    valid = (
        price_a.notna()
        & price_b.notna()
        & price_a.map(math.isfinite)
        & price_b.map(math.isfinite)
        & (price_a > 0)
        & (price_b > 0)
    )
    valid_df = df.loc[valid].copy().reset_index(drop=True)
    valid_df[column_a] = price_a.loc[valid].to_numpy()
    valid_df[column_b] = price_b.loc[valid].to_numpy()
    return valid_df


def _trading_signal_direction(zscore):
    if zscore is None:
        return None
    if zscore >= 2:
        return "short"
    if zscore <= -2:
        return "long"
    return "hold"


@app.route("/api/pairs", methods=["GET"])
def get_pairs():
    return jsonify(PAIRS)


@app.route("/api/strategy/universes", methods=["GET"])
def get_strategy_universes():
    return jsonify(serialized_peer_groups())


@app.route("/api/strategy/scan", methods=["POST"])
def scan_strategy_universe():
    try:
        payload = _strategy_payload()
        tickers = _strategy_tickers(payload)
        start, end = _strategy_dates(payload)
        frame = load_universe_data(tickers, start, end)
        if len(frame) < MIN_STRATEGY_OBSERVATIONS:
            raise ValueError(
                f"At least {MIN_STRATEGY_OBSERVATIONS} overlapping sessions are "
                f"required; received {len(frame)}"
            )

        candidates = scan_peer_universe(
            frame,
            tickers,
            formation_window=DEFAULT_FORMATION_WINDOW,
        )
        first_date = pd.Timestamp(frame["Date"].iloc[0]).date().isoformat()
        last_date = pd.Timestamp(frame["Date"].iloc[-1]).date().isoformat()
        return jsonify({
            "strategy_version": "peer_residual_v1",
            "tickers": tickers,
            "as_of": last_date,
            "candidates": candidates,
            "parameters": {
                "formation_window": DEFAULT_FORMATION_WINDOW,
                "rebalance_sessions": 21,
                "entry_z": 2.0,
                "exit_z": 0.5,
            },
            "data_quality": {
                "observation_count": len(frame),
                "first_date": first_date,
                "latest_date": last_date,
                "warnings": [
                    "Peer membership uses today's editable universe and may contain survivorship bias"
                ],
            },
        })
    except ValueError as exc:
        return _strategy_error(exc)
    except Exception as exc:
        return _strategy_error(exc, code="strategy_scan_failed", status=500)


@app.route("/api/strategy/backtest", methods=["POST"])
def backtest_strategy():
    try:
        payload = _strategy_payload()
        target, peers = _strategy_target_and_peers(payload)
        start, end = _strategy_dates(payload)
        initial_capital = _strategy_number(
            payload, "initial_capital", DEFAULT_INITIAL_CAPITAL, 1_000, 10_000_000
        )
        gross_exposure = _strategy_number(
            payload, "gross_exposure", DEFAULT_GROSS_EXPOSURE, 0.1, 2.0
        )
        transaction_cost_bps = _strategy_number(
            payload,
            "transaction_cost_bps",
            DEFAULT_TRANSACTION_COST_BPS,
            0.0,
            100.0,
        )
        annual_borrow_rate = _strategy_number(
            payload,
            "annual_borrow_rate",
            DEFAULT_ANNUAL_BORROW_RATE,
            0.0,
            1.0,
        )
        participation_rate = _strategy_number(
            payload,
            "participation_rate",
            DEFAULT_PARTICIPATION_RATE,
            0.0001,
            0.10,
        )

        tickers = [target, *peers]
        frame = load_universe_data(tickers, start, end)
        if len(frame) < MIN_STRATEGY_OBSERVATIONS:
            raise ValueError(
                f"At least {MIN_STRATEGY_OBSERVATIONS} overlapping sessions are "
                f"required; received {len(frame)}"
            )
        result = run_strategy_analysis(
            frame,
            target,
            peers,
            initial_capital=initial_capital,
            gross_exposure=gross_exposure,
            transaction_cost_bps=transaction_cost_bps,
            annual_borrow_rate=annual_borrow_rate,
            participation_rate=participation_rate,
        )
        result.update({
            "strategy_version": "peer_residual_v1",
            "target": target,
            "peers": peers,
            "as_of": pd.Timestamp(frame["Date"].iloc[-1]).date().isoformat(),
            "config": {
                "initial_capital": initial_capital,
                "gross_exposure": gross_exposure,
                "transaction_cost_bps": transaction_cost_bps,
                "annual_borrow_rate": annual_borrow_rate,
                "participation_rate": participation_rate,
                "rebalance_sessions": 21,
                "entry_z": 2.0,
                "exit_z": 0.5,
                "stop_z": 4.0,
                "execution": "next_adjusted_open",
            },
            "data_quality": {
                "observation_count": len(frame),
                "first_date": pd.Timestamp(frame["Date"].iloc[0]).date().isoformat(),
                "latest_date": pd.Timestamp(frame["Date"].iloc[-1]).date().isoformat(),
                "warnings": [
                    "Yahoo Finance is research-grade data",
                    "Editable current peer membership may introduce survivorship bias",
                ],
            },
            "methodology_note": (
                "Every historical signal uses only information available by that close "
                "and is filled at the next adjusted open. Results are simulated and do "
                "not guarantee future performance."
            ),
        })
        return jsonify(result)
    except ValueError as exc:
        return _strategy_error(exc)
    except Exception as exc:
        return _strategy_error(exc, code="strategy_backtest_failed", status=500)


@app.route("/api/validate", methods=["GET"])
def validate_ticker():
    ticker = request.args.get("ticker", "").upper()
    if not ticker:
        return jsonify({"valid": False, "error": "No ticker provided"}), 400
    try:
        info = yf.Ticker(ticker).info
        valid = info.get("regularMarketPrice") is not None or info.get("previousClose") is not None
        name = info.get("shortName", ticker)
        return jsonify({"valid": valid, "ticker": ticker, "name": name if valid else None})
    except Exception:
        return jsonify({"valid": False, "ticker": ticker, "name": None})


@app.route("/api/correlation", methods=["GET"])
def get_correlation():
    ticker_a = request.args.get("ticker_a", "").upper()
    ticker_b = request.args.get("ticker_b", "").upper()
    start = request.args.get("start", "2020-01-01")
    end = request.args.get("end", str(date.today()))

    try:
        _validate_pair(ticker_a, ticker_b)
        _validate_date_range(start, end)
        max_lag = _parse_integer_arg("max_lag", default=10, minimum=0)
        df = load_pair_data(ticker_a, ticker_b, start, end)
        df = _valid_pair_rows(df, ticker_a, ticker_b)
        minimum_observations = max_lag + 3
        if len(df) < minimum_observations:
            raise ValueError(
                "At least "
                f"{minimum_observations} overlapping observations are required "
                f"for max_lag={max_lag}; received {len(df)}"
            )
        series_a = df[f"Close_{ticker_a}"]
        series_b = df[f"Close_{ticker_b}"]
        corr_df = compute_lagged_correlation(series_a, series_b, max_lag)

        return jsonify({
            "ticker_a": ticker_a,
            "ticker_b": ticker_b,
            "data": [
                {"lag": int(row["Lag"]), "correlation": _safe_float(row["Correlation"])}
                for _, row in corr_df.iterrows()
            ],
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/spread", methods=["GET"])
def get_spread():
    ticker_a = request.args.get("ticker_a", "").upper()
    ticker_b = request.args.get("ticker_b", "").upper()
    start = request.args.get("start", "2023-01-01")
    end = request.args.get("end", str(date.today()))
    spread_type = request.args.get("spread_type", "log_ratio")

    try:
        _validate_pair(ticker_a, ticker_b)
        _validate_date_range(start, end)
        window = _parse_integer_arg(
            "window", default=DEFAULT_SIGNAL_WINDOW, minimum=2
        )
        requested_start = pd.Timestamp(start)
        warmup_days = int(window * 2 + 10)
        warmup_start = (requested_start - pd.Timedelta(days=warmup_days)).strftime("%Y-%m-%d")

        df = load_pair_data(ticker_a, ticker_b, warmup_start, end)
        df = _valid_pair_rows(df, ticker_a, ticker_b)

        spread_df, metrics = calculate_spread_metrics(
            df,
            ticker_a,
            ticker_b,
            spread_type=spread_type,
            window=window,
        )

        spread_df['Date'] = pd.to_datetime(spread_df['Date'])
        valid_idx = spread_df['Date'] >= requested_start
        spread_df = spread_df[valid_idx].reset_index(drop=True)
        
        if len(spread_df) == 0:
            raise ValueError("No data available in the requested date range.")
            
        clean_spread = spread_df['spread'].dropna()
        def finite_value(value):
            if pd.isna(value): return None
            val = float(value)
            return val if math.isfinite(val) else None
            
        metrics['num_observations'] = len(clean_spread)
        metrics['descriptive_mean'] = finite_value(clean_spread.mean())
        metrics['descriptive_std'] = finite_value(clean_spread.std())
        metrics['descriptive_min'] = finite_value(clean_spread.min())
        metrics['descriptive_max'] = finite_value(clean_spread.max())

        price_a = spread_df[f"{ticker_a}_price"]
        price_b = spread_df[f"{ticker_b}_price"]
        pair_model = validate_pair_model(
            price_a,
            price_b,
            zscore_window=window,
        )
        norm_a = price_a / price_a.iloc[0] * 100
        norm_b = price_b / price_b.iloc[0] * 100

        data = []
        for i, row in spread_df.iterrows():
            date_val = row["Date"]
            date_str = str(date_val.date()) if hasattr(date_val, "date") and not pd.isna(date_val) else str(date_val)
            data.append({
                "date": date_str,
                "price_a": _safe_float(price_a.iloc[i]),
                "price_b": _safe_float(price_b.iloc[i]),
                "norm_a": _safe_float(norm_a.iloc[i]),
                "norm_b": _safe_float(norm_b.iloc[i]),
                "spread": _safe_float(row["spread"]),
                "rolling_mean": _safe_float(row["rolling_mean"]),
                "rolling_std": _safe_float(row["rolling_std"]),
                "band_1_upper": _safe_float(row["band_1_upper"]),
                "band_1_lower": _safe_float(row["band_1_lower"]),
                "band_2_upper": _safe_float(row["band_2_upper"]),
                "band_2_lower": _safe_float(row["band_2_lower"]),
                "zscore": _safe_float(row["zscore"]),
            })

        clean_metrics = {k: _safe_float(v) if isinstance(v, (float, int)) else v for k, v in metrics.items()}

        return jsonify({
            "ticker_a": ticker_a,
            "ticker_b": ticker_b,
            "spread_type": spread_type,
            "data": data,
            "metrics": clean_metrics,
            "pair_model": pair_model,
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/signal", methods=["GET"])
def get_signal():
    ticker_a = request.args.get("ticker_a", "").upper()
    ticker_b = request.args.get("ticker_b", "").upper()
    start = request.args.get("start", "2023-01-01")
    end = request.args.get("end", str(date.today()))

    try:
        _validate_pair(ticker_a, ticker_b)
        _validate_date_range(start, end)
        window = _parse_integer_arg(
            "window", default=DEFAULT_SIGNAL_WINDOW, minimum=2
        )
        df = load_pair_data(ticker_a, ticker_b, start, end)
        df = _valid_pair_rows(df, ticker_a, ticker_b)
        if len(df) < window:
            raise ValueError(
                "At least "
                f"{window} overlapping observations are required "
                f"for window={window}; received {len(df)}"
            )

        _, metrics = calculate_spread_metrics(
            df,
            ticker_a,
            ticker_b,
            spread_type="log_ratio",
            window=window,
        )
        zscore = _safe_float(metrics["current_zscore"])

        return jsonify({
            "ticker_a": ticker_a,
            "ticker_b": ticker_b,
            "zscore": zscore,
            "direction": _trading_signal_direction(zscore),
            "window": window,
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/risk/breakdown", methods=["GET"])
def get_risk_breakdown():
    ticker_a = request.args.get("ticker_a", "").upper()
    ticker_b = request.args.get("ticker_b", "").upper()
    end = request.args.get("end", str(date.today()))

    try:
        _validate_pair(ticker_a, ticker_b)
        start = request.args.get("start") or _risk_start_date(end)
        _validate_date_range(start, end)
        df = load_pair_data(ticker_a, ticker_b, start, end)
        date_index = pd.to_datetime(df["Date"])
        series_a = pd.Series(df[f"Close_{ticker_a}"].values, index=date_index)
        series_b = pd.Series(df[f"Close_{ticker_b}"].values, index=date_index)
        breakdown = detect_correlation_breakdown(series_a, series_b)

        return jsonify({
            "ticker_a": ticker_a,
            "ticker_b": ticker_b,
            "current_corr": _safe_float(breakdown["current_corr"]),
            "baseline_corr": _safe_float(breakdown["baseline_corr"]),
            "broken": bool(breakdown["broken"]),
            "broken_since": breakdown["broken_since"],
            "breakdown_reason": breakdown["breakdown_reason"],
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/backtest", methods=["GET"])
def get_backtest():
    ticker_a = request.args.get("ticker_a", "").upper()
    ticker_b = request.args.get("ticker_b", "").upper()
    start = request.args.get("start", "2020-01-01")
    end = request.args.get("end", str(date.today()))
    spread_type = request.args.get("spread_type", "log_ratio")

    if not ticker_a or not ticker_b:
        return jsonify({"error": "ticker_a and ticker_b are required"}), 400

    try:
        window = int(request.args.get("window", "60"))  # 20-day rolling window
        entry_z = float(request.args.get("entry_z", "2.0"))  # z-score entry threshold
        exit_z = float(request.args.get("exit_z", "0.0"))  # z-score exit threshold
        hedge_ratio = float(request.args.get("hedge_ratio", "1.0")) 
    except ValueError:
        return jsonify({"error": "Invalid numerical parameters"}), 400

    try:
        requested_start = pd.Timestamp(start)
        # Pad by enough calendar days to ensure we have 'window' number of trading days
        warmup_days = int(window * 2 + 10)
        warmup_start = (requested_start - pd.Timedelta(days=warmup_days)).strftime("%Y-%m-%d")
        df = load_pair_data(ticker_a, ticker_b, warmup_start, end)
        if len(df) == 0:
            return jsonify({"error": "No data found for the given tickers and date range"}), 400

        # Sanitize yfinance data by forward-filling and dropping any remaining NaNs
        df = df.ffill().dropna()

        df = df[pd.to_datetime(df["Date"]) >= pd.Timestamp(warmup_start)].copy()
        df = df[pd.to_datetime(df["Date"]) < pd.Timestamp(end) + pd.Timedelta(days=1)].copy()

        spread_df, _ = calculate_spread_metrics(df, ticker_a, ticker_b, spread_type, hedge_ratio=hedge_ratio, window=window)
        
        spread_df = spread_df.set_index(pd.to_datetime(spread_df["Date"]))

        prices_a = spread_df[f"{ticker_a}_price"]
        prices_b = spread_df[f"{ticker_b}_price"]
        spread_series = spread_df["spread"]

        # Generate rolling z-score and walk-forward signals ON THE PADDED DATA
        signals, rolling_zscore = generate_zscore_signals(
            spread_series,
            window=window,
            entry_z=entry_z,
            exit_z=exit_z
        )

        # Now truncate everything to the valid requested start date
        valid_start = pd.Timestamp(requested_start)
        valid_idx = spread_df.index >= valid_start
        prices_a = prices_a[valid_idx]
        prices_b = prices_b[valid_idx]
        signals = signals[valid_idx]

        # Run backtest
        results = run_backtest(prices_a, prices_b, signals, hedge_ratio)

        tearsheet = {
            "ticker_a": ticker_a,
            "ticker_b": ticker_b,
            "window": window,
            "entry_z": entry_z,
            "exit_z": exit_z,
            "hedge_ratio": hedge_ratio,
            "spread_type": spread_type,
            "metrics": {
                "sharpe": _safe_float(results["sharpe"]),
                "max_drawdown": _safe_float(results["max_dd"]),
                "num_trades": int(results["num_trades"]),
                "win_rate": _safe_float(results["win_rate"]),
            },
            "equity_curve": results["equity_curve"],
            "trade_log": results["trade_log"]
        }

        return jsonify(tearsheet)
    except Exception:
        return jsonify({"error": "Backtest request failed"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("CORRELATION_API_PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=True)
