"""Walk-forward portfolio simulation for the peer-residual strategy."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd

from .peer_basket import fit_peer_basket


DEFAULT_INITIAL_CAPITAL = 100_000.0
DEFAULT_GROSS_EXPOSURE = 1.0
DEFAULT_TRANSACTION_COST_BPS = 5.0
DEFAULT_ANNUAL_BORROW_RATE = 0.03
DEFAULT_PARTICIPATION_RATE = 0.01
DEFAULT_REBALANCE_SESSIONS = 21
ENTRY_Z = 2.0
EXIT_Z = 0.5
STOP_Z = 4.0
SENSITIVITY_WINDOWS = (126, 252, 504)
MAX_ADF_PVALUE = 0.05
MIN_HALF_LIFE_DAYS = 2.0
MAX_HALF_LIFE_DAYS = 30.0


def _finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _strategy_columns(target: str, peers: Iterable[str]) -> List[str]:
    tickers = [target, *peers]
    return [
        f"{field}_{ticker}"
        for ticker in tickers
        for field in ("Open", "Close", "Volume")
    ]


def _validated_frame(
    frame: pd.DataFrame, target: str, peers: List[str]
) -> pd.DataFrame:
    required = ["Date", *_strategy_columns(target, peers)]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(
            "Strategy market data is missing required columns: "
            + ", ".join(missing)
        )
    validated = frame.loc[:, required].copy()
    validated["Date"] = pd.to_datetime(validated["Date"], errors="coerce")
    if (
        validated["Date"].isna().any()
        or validated["Date"].duplicated().any()
        or not validated["Date"].is_monotonic_increasing
    ):
        raise ValueError("Strategy dates must be valid, unique, and sorted")

    numeric_columns = [column for column in required if column != "Date"]
    for column in numeric_columns:
        validated[column] = pd.to_numeric(validated[column], errors="coerce")
        values = validated[column].to_numpy(float)
        if not np.isfinite(values).all():
            raise ValueError(f"{column} must contain finite values")
        if column.startswith(("Open_", "Close_")) and (values <= 0).any():
            raise ValueError(f"{column} must contain positive values")
        if column.startswith("Volume_") and (values < 0).any():
            raise ValueError(f"{column} must contain non-negative values")
    return validated.reset_index(drop=True)


def desired_exposures(
    direction: int,
    target: str,
    peer_weights: List[Dict[str, float]],
    hedge_beta: float,
    gross_exposure: float,
) -> Dict[str, float]:
    """Return portfolio fractions whose absolute sum is gross_exposure."""
    if direction not in (-1, 0, 1):
        raise ValueError("direction must be -1, 0, or 1")
    tickers = [target, *[entry["ticker"] for entry in peer_weights]]
    if direction == 0:
        return {ticker: 0.0 for ticker in tickers}
    if hedge_beta <= 0:
        raise ValueError("hedge_beta must be positive")

    target_fraction = gross_exposure / (1.0 + hedge_beta)
    basket_fraction = gross_exposure - target_fraction
    exposures = {target: direction * target_fraction}
    for entry in peer_weights:
        exposures[entry["ticker"]] = (
            -direction * basket_fraction * float(entry["weight"])
        )
    return exposures


def _position_direction(action: str) -> int:
    if action == "long_target":
        return 1
    if action == "short_target":
        return -1
    return 0


def _is_tradable(model: Dict[str, Any]) -> bool:
    """Return whether the fitted residual looks mean-reverting enough to enter."""
    adf_pvalue = _finite_float(model.get("adf_pvalue"))
    half_life = _finite_float(model.get("half_life_days"))
    if adf_pvalue is None or half_life is None:
        return False
    return (
        adf_pvalue < MAX_ADF_PVALUE
        and MIN_HALF_LIFE_DAYS <= half_life <= MAX_HALF_LIFE_DAYS
    )


def _signal_action(zscore: float | None) -> str:
    if zscore is None:
        return "unavailable"
    if zscore <= -ENTRY_Z:
        return "long_target"
    if zscore >= ENTRY_Z:
        return "short_target"
    return "hold"


def _metrics(equity: pd.Series) -> Dict[str, float | None]:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return {
            "total_return": 0.0,
            "annualized_return": None,
            "annualized_volatility": None,
            "sharpe": None,
            "max_drawdown": 0.0,
        }
    returns = equity.pct_change().dropna()
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    years = max((len(equity) - 1) / 252.0, 1 / 252.0)
    annualized_return = None
    if equity.iloc[-1] > 0:
        annualized_return = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
    volatility = returns.std(ddof=1) * math.sqrt(252) if len(returns) > 1 else None
    sharpe = None
    if len(returns) > 1 and returns.std(ddof=1) > 1e-12:
        sharpe = returns.mean() / returns.std(ddof=1) * math.sqrt(252)
    drawdown = equity / equity.cummax() - 1
    return {
        "total_return": _finite_float(total_return),
        "annualized_return": _finite_float(annualized_return),
        "annualized_volatility": _finite_float(volatility),
        "sharpe": _finite_float(sharpe),
        "max_drawdown": _finite_float(drawdown.min()),
    }


def _capacity_scale(
    frame: pd.DataFrame,
    index: int,
    desired_values: Dict[str, float],
    participation_rate: float,
) -> tuple[float, List[str]]:
    if index < 1:
        return 1.0, []
    start = max(0, index - 20)
    scale = 1.0
    warnings = []
    for ticker, desired_value in desired_values.items():
        if abs(desired_value) <= 1e-12:
            continue
        dollar_volume = (
            frame[f"Open_{ticker}"].iloc[start:index]
            * frame[f"Volume_{ticker}"].iloc[start:index]
        )
        median_dollar_volume = float(dollar_volume.median())
        capacity = participation_rate * median_dollar_volume
        if capacity <= 0:
            scale = 0.0
            warnings.append(f"{ticker} has no measurable recent dollar volume")
            continue
        ticker_scale = min(1.0, capacity / abs(desired_value))
        if ticker_scale < 1.0:
            warnings.append(
                f"{ticker} position was scaled to the {participation_rate:.1%} ADV limit"
            )
        scale = min(scale, ticker_scale)
    return scale, warnings


def _serialized_signal(
    model: Dict[str, Any], zscore: float | None, action: str
) -> Dict[str, Any]:
    return {
        "target": model["target"],
        "peers": model["peers"],
        "action": action,
        "zscore": _finite_float(zscore),
        "hedge_beta": model["hedge_beta"],
        "peer_weights": model["peer_weights"],
        "model_quality": model["model_quality"],
        "cautions": model["cautions"],
        "half_life_days": model["half_life_days"],
        "adf_pvalue": model["adf_pvalue"],
        "r_squared": model["r_squared"],
    }


def run_walk_forward_backtest(
    frame: pd.DataFrame,
    target: str,
    peers: Iterable[str],
    *,
    formation_window: int = 252,
    initial_capital: float = DEFAULT_INITIAL_CAPITAL,
    gross_exposure: float = DEFAULT_GROSS_EXPOSURE,
    transaction_cost_bps: float = DEFAULT_TRANSACTION_COST_BPS,
    annual_borrow_rate: float = DEFAULT_ANNUAL_BORROW_RATE,
    participation_rate: float = DEFAULT_PARTICIPATION_RATE,
    rebalance_sessions: int = DEFAULT_REBALANCE_SESSIONS,
    require_tradable: bool = True,
) -> Dict[str, Any]:
    normalized_target = str(target).strip().upper()
    normalized_peers = [str(peer).strip().upper() for peer in peers]
    if normalized_target in normalized_peers or len(set(normalized_peers)) != len(normalized_peers):
        raise ValueError("target and peers must be unique")
    if not 3 <= len(normalized_peers) <= 7:
        raise ValueError("peers must contain between 3 and 7 tickers")
    if initial_capital <= 0:
        raise ValueError("initial_capital must be positive")
    if not 0 < gross_exposure <= 2:
        raise ValueError("gross_exposure must be between 0 and 2")
    if transaction_cost_bps < 0 or annual_borrow_rate < 0:
        raise ValueError("cost assumptions must be non-negative")
    if not 0 < participation_rate <= 0.10:
        raise ValueError("participation_rate must be between 0 and 0.10")
    if rebalance_sessions < 1:
        raise ValueError("rebalance_sessions must be positive")

    tickers = [normalized_target, *normalized_peers]
    data = _validated_frame(frame, normalized_target, normalized_peers)
    if len(data) < formation_window + 22:
        raise ValueError(
            f"At least {formation_window + 22} sessions are required for a "
            f"{formation_window}-session formation window; received {len(data)}"
        )

    cash = float(initial_capital)
    shares = {ticker: 0.0 for ticker in tickers}
    current_direction = 0
    pending_direction = 0
    pending_rebalance = False
    pending_signal_date = None
    pending_signal_z = None
    pending_reason = None
    model = None
    model_state = None
    model_refit_index = None
    held_sessions = 0
    current_trade = None
    trades = []
    curve = []
    signals = []
    capacity_warnings = []
    total_transaction_cost = 0.0
    total_borrow_cost = 0.0
    total_traded_notional = 0.0

    first_execution_index = formation_window + 1
    benchmark_start = float(data[f"Open_{normalized_target}"].iloc[first_execution_index])

    for index in range(first_execution_index, len(data)):
        date_value = data["Date"].iloc[index].date().isoformat()
        open_prices = {
            ticker: float(data[f"Open_{ticker}"].iloc[index]) for ticker in tickers
        }

        short_notional = sum(
            max(0.0, -shares[ticker] * open_prices[ticker]) for ticker in tickers
        )
        daily_borrow = short_notional * annual_borrow_rate / 252.0
        cash -= daily_borrow
        total_borrow_cost += daily_borrow
        if current_trade is not None:
            current_trade["borrow_cost"] += daily_borrow

        equity_before_trade = cash + sum(
            shares[ticker] * open_prices[ticker] for ticker in tickers
        )

        if pending_rebalance:
            if pending_direction == 0 or model is None:
                desired_values = {ticker: 0.0 for ticker in tickers}
            else:
                exposure_fractions = desired_exposures(
                    pending_direction,
                    normalized_target,
                    model["peer_weights"],
                    float(model["hedge_beta"]),
                    gross_exposure,
                )
                desired_values = {
                    ticker: equity_before_trade * exposure_fractions[ticker]
                    for ticker in tickers
                }
                scale, warnings = _capacity_scale(
                    data, index, desired_values, participation_rate
                )
                desired_values = {
                    ticker: value * scale for ticker, value in desired_values.items()
                }
                capacity_warnings.extend(warnings)

            desired_shares = {
                ticker: desired_values[ticker] / open_prices[ticker] for ticker in tickers
            }
            trade_notional = sum(
                abs((desired_shares[ticker] - shares[ticker]) * open_prices[ticker])
                for ticker in tickers
            )
            transaction_cost = trade_notional * transaction_cost_bps / 10_000.0
            for ticker in tickers:
                share_change = desired_shares[ticker] - shares[ticker]
                cash -= share_change * open_prices[ticker]
                shares[ticker] = desired_shares[ticker]
            cash -= transaction_cost
            total_transaction_cost += transaction_cost
            total_traded_notional += trade_notional

            if current_trade is not None:
                current_trade["transaction_cost"] += transaction_cost

            if current_direction != 0 and pending_direction == 0 and current_trade is not None:
                exit_equity = cash + sum(
                    shares[ticker] * open_prices[ticker] for ticker in tickers
                )
                current_trade.update({
                    "exit_date": date_value,
                    "exit_zscore": _finite_float(pending_signal_z),
                    "exit_reason": pending_reason or "signal_exit",
                    "holding_sessions": held_sessions,
                    "gross_pnl": _finite_float(
                        exit_equity
                        - current_trade["entry_equity"]
                        + current_trade["transaction_cost"]
                        + current_trade["borrow_cost"]
                    ),
                    "net_pnl": _finite_float(exit_equity - current_trade["entry_equity"]),
                })
                trades.append(current_trade)
                current_trade = None
                held_sessions = 0

            if current_direction == 0 and pending_direction != 0:
                current_trade = {
                    "signal_date": pending_signal_date,
                    "entry_date": date_value,
                    "direction": "long_target" if pending_direction == 1 else "short_target",
                    "entry_zscore": _finite_float(pending_signal_z),
                    "entry_equity": equity_before_trade,
                    "transaction_cost": transaction_cost,
                    "borrow_cost": 0.0,
                }
                held_sessions = 0

            current_direction = pending_direction
            pending_rebalance = False

        equity = cash + sum(shares[ticker] * open_prices[ticker] for ticker in tickers)
        benchmark = initial_capital * open_prices[normalized_target] / benchmark_start
        curve.append({
            "date": date_value,
            "equity": _finite_float(equity),
            "benchmark": _finite_float(benchmark),
            "position": current_direction,
        })
        if current_direction != 0:
            held_sessions += 1

        signal_index = index
        should_refit = (
            model is None
            or model_refit_index is None
            or signal_index - model_refit_index >= rebalance_sessions
        )
        if should_refit:
            model = fit_peer_basket(
                data.iloc[: signal_index + 1],
                normalized_target,
                normalized_peers,
                formation_window=formation_window,
            )
            model_state = model["current_residual_state"]
            model_refit_index = signal_index
        else:
            previous_close = np.array([
                float(data[f"Close_{ticker}"].iloc[signal_index - 1])
                for ticker in tickers
            ])
            current_close = np.array([
                float(data[f"Close_{ticker}"].iloc[signal_index])
                for ticker in tickers
            ])
            close_return = np.log(current_close / previous_close)
            coefficients = np.array([
                float(model["hedge_beta"]) * float(entry["weight"])
                for entry in model["peer_weights"]
            ])
            model_state = float(model_state + close_return[0] - close_return[1:] @ coefficients)

        equilibrium_mean = model["equilibrium_mean"]
        equilibrium_std = model["equilibrium_std"]
        zscore = None
        if (
            equilibrium_mean is not None
            and equilibrium_std is not None
            and equilibrium_std > 1e-12
        ):
            zscore = (model_state - equilibrium_mean) / equilibrium_std
        action = _signal_action(_finite_float(zscore))
        signals.append({
            "date": date_value,
            "zscore": _finite_float(zscore),
            "action": action,
            "position": current_direction,
            "model_refit": should_refit,
        })

        desired_direction = current_direction
        reason = None
        if current_direction == 0:
            desired_direction = _position_direction(action)
            if (
                desired_direction != 0
                and require_tradable
                and not _is_tradable(model)
            ):
                desired_direction = 0
            if desired_direction != 0:
                reason = "entry_signal"
        else:
            max_holding = 60
            if model["half_life_days"] is not None:
                max_holding = int(
                    min(60, max(5, math.ceil(3 * model["half_life_days"])))
                )
            if zscore is not None and abs(zscore) <= EXIT_Z:
                desired_direction = 0
                reason = "mean_reversion"
            elif zscore is not None and abs(zscore) >= STOP_Z:
                desired_direction = 0
                reason = "zscore_stop"
            elif held_sessions >= max_holding:
                desired_direction = 0
                reason = "maximum_holding_period"

        rebalance_active_position = should_refit and current_direction != 0
        if desired_direction != current_direction or rebalance_active_position:
            pending_direction = desired_direction
            pending_rebalance = True
            pending_signal_date = date_value
            pending_signal_z = zscore
            pending_reason = reason or "model_rebalance"

    if current_direction != 0 and current_trade is not None:
        final_index = len(data) - 1
        final_date = data["Date"].iloc[final_index].date().isoformat()
        final_prices = {
            ticker: float(data[f"Close_{ticker}"].iloc[final_index]) for ticker in tickers
        }
        liquidation_notional = sum(
            abs(shares[ticker] * final_prices[ticker]) for ticker in tickers
        )
        liquidation_cost = liquidation_notional * transaction_cost_bps / 10_000.0
        for ticker in tickers:
            cash += shares[ticker] * final_prices[ticker]
            shares[ticker] = 0.0
        cash -= liquidation_cost
        total_transaction_cost += liquidation_cost
        total_traded_notional += liquidation_notional
        current_trade["transaction_cost"] += liquidation_cost
        current_trade.update({
            "exit_date": final_date,
            "exit_zscore": None,
            "exit_reason": "end_of_test",
            "holding_sessions": held_sessions,
            "gross_pnl": _finite_float(
                cash
                - current_trade["entry_equity"]
                + current_trade["transaction_cost"]
                + current_trade["borrow_cost"]
            ),
            "net_pnl": _finite_float(cash - current_trade["entry_equity"]),
        })
        trades.append(current_trade)
        if curve:
            curve[-1]["equity"] = _finite_float(cash)
            curve[-1]["benchmark"] = _finite_float(
                initial_capital
                * final_prices[normalized_target]
                / benchmark_start
            )
            curve[-1]["position"] = 0

    equity_series = pd.Series([point["equity"] for point in curve], dtype=float)
    running_max = equity_series.cummax()
    drawdowns = equity_series / running_max - 1
    for point, drawdown in zip(curve, drawdowns):
        point["drawdown"] = _finite_float(drawdown)

    summary = _metrics(equity_series)
    holdout_start = int(len(equity_series) * 0.70)
    holdout_equity = equity_series.iloc[holdout_start:].reset_index(drop=True)
    summary.update({
        "final_equity": _finite_float(equity_series.iloc[-1]),
        "benchmark_return": _finite_float(
            curve[-1]["benchmark"] / curve[0]["benchmark"] - 1
        ),
        "trade_count": len(trades),
        "win_rate": _finite_float(
            np.mean([trade["net_pnl"] > 0 for trade in trades]) if trades else 0.0
        ),
        "average_holding_sessions": _finite_float(
            np.mean([trade["holding_sessions"] for trade in trades]) if trades else 0.0
        ),
        "turnover": _finite_float(total_traded_notional / initial_capital),
        "holdout": _metrics(holdout_equity),
    })

    latest_model = fit_peer_basket(
        data,
        normalized_target,
        normalized_peers,
        formation_window=formation_window,
        include_series=True,
    )
    return {
        "formation_window": formation_window,
        "summary": summary,
        "costs": {
            "transaction_cost": _finite_float(total_transaction_cost),
            "borrow_cost": _finite_float(total_borrow_cost),
            "total": _finite_float(total_transaction_cost + total_borrow_cost),
            "transaction_cost_bps": transaction_cost_bps,
            "annual_borrow_rate": annual_borrow_rate,
        },
        "current_signal": _serialized_signal(
            latest_model, latest_model["zscore"], latest_model["action"]
        ),
        "equity_curve": curve,
        "signal_series": signals,
        "residual_series": latest_model.get("residual_series", []),
        "trades": trades,
        "capacity_warnings": sorted(set(capacity_warnings)),
    }


def run_strategy_analysis(
    frame: pd.DataFrame,
    target: str,
    peers: Iterable[str],
    **kwargs,
) -> Dict[str, Any]:
    peers = list(peers)
    base = run_walk_forward_backtest(
        frame, target, peers, formation_window=252, **kwargs
    )
    sensitivity = []
    for window in SENSITIVITY_WINDOWS:
        try:
            result = base if window == 252 else run_walk_forward_backtest(
                frame, target, peers, formation_window=window, **kwargs
            )
            sensitivity.append({
                "formation_window": window,
                "status": "available",
                "summary": result["summary"],
            })
        except ValueError as exc:
            sensitivity.append({
                "formation_window": window,
                "status": "unavailable",
                "error": str(exc),
            })
    base["sensitivity"] = sensitivity
    return base
