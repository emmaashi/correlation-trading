import os
import math
from datetime import date, datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd

import yfinance as yf

from analysis.data_loader import load_pair_data
from analysis.correlation import compute_lagged_correlation
from analysis.spread import calculate_spread_metrics
from analysis.risk import detect_correlation_breakdown

app = Flask(__name__)
CORS(app)

RISK_LOOKBACK_DAYS = 540
DEFAULT_SIGNAL_WINDOW = 60

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


@app.route("/api/pairs", methods=["GET"])
def get_pairs():
    return jsonify(PAIRS)


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
        df = load_pair_data(ticker_a, ticker_b, start, end)
        df = _valid_pair_rows(df, ticker_a, ticker_b)
        if len(df) < window:
            raise ValueError(
                "At least "
                f"{window} overlapping observations are required "
                f"for window={window}; "
                f"received {len(df)}"
            )
        spread_df, metrics = calculate_spread_metrics(
            df,
            ticker_a,
            ticker_b,
            spread_type=spread_type,
            window=window,
        )

        price_a = spread_df[f"{ticker_a}_price"]
        price_b = spread_df[f"{ticker_b}_price"]
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


if __name__ == "__main__":
    port = int(os.environ.get("CORRELATION_API_PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=True)
