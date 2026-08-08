"""Point-in-time peer-basket signals for the strategy lab."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from statsmodels.tsa.stattools import adfuller


DEFAULT_FORMATION_WINDOW = 252
DEFAULT_RIDGE_ALPHA = 1e-3
MAX_PEER_WEIGHT = 0.60
MIN_PEERS = 3
MAX_PEERS = 7
ENTRY_Z = 2.0


def _finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _normalized_tickers(tickers: Iterable[str]) -> List[str]:
    normalized = []
    for ticker in tickers:
        value = str(ticker).strip().upper()
        if not value:
            raise ValueError("tickers must not contain empty values")
        if value not in normalized:
            normalized.append(value)
    return normalized


def _validated_prices(
    frame: pd.DataFrame, target: str, peers: List[str]
) -> tuple[pd.DatetimeIndex, np.ndarray]:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError("Strategy market data is empty")
    if "Date" not in frame:
        raise ValueError("Strategy market data is missing Date")

    tickers = [target, *peers]
    columns = [f"Close_{ticker}" for ticker in tickers]
    missing = [column for column in columns if column not in frame]
    if missing:
        raise ValueError(
            "Strategy market data is missing required columns: "
            + ", ".join(missing)
        )

    dates = pd.DatetimeIndex(pd.to_datetime(frame["Date"], errors="coerce"))
    if dates.isna().any() or dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise ValueError("Strategy dates must be valid, unique, and sorted")

    prices = frame[columns].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    if not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError("Strategy prices must be finite and strictly positive")
    return dates, prices


def _fit_nonnegative_ridge(
    target_returns: np.ndarray,
    peer_returns: np.ndarray,
    ridge_alpha: float,
    max_peer_weight: float,
) -> tuple[float, np.ndarray]:
    peer_count = peer_returns.shape[1]

    initial, *_ = np.linalg.lstsq(peer_returns, target_returns, rcond=None)
    initial = np.clip(initial, 1e-4, None)
    if initial.sum() <= 1e-8:
        initial = np.ones(peer_count)

    def objective(coefficients: np.ndarray) -> float:
        residual = target_returns - peer_returns @ coefficients
        return float(residual @ residual + ridge_alpha * (coefficients @ coefficients))

    constraints = [
        {
            "type": "ineq",
            "fun": lambda coefficients, index=index: (
                max_peer_weight * coefficients.sum() - coefficients[index]
            ),
        }
        for index in range(peer_count)
    ]
    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=[(0.0, None)] * peer_count,
        constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-12},
    )
    if not result.success or not np.isfinite(result.x).all():
        raise ValueError("Could not fit a stable nonnegative peer basket")

    coefficients = np.asarray(result.x, dtype=float)
    beta = float(coefficients.sum())
    if beta <= 1e-8:
        raise ValueError("Peer basket hedge beta is zero")
    intercept = float(
        target_returns.mean() - peer_returns.mean(axis=0) @ coefficients
    )
    return intercept, coefficients


def _fit_residual_process(residual_returns: np.ndarray) -> Dict[str, Any]:
    state = np.cumsum(residual_returns)
    lagged = state[:-1]
    current = state[1:]
    design = np.column_stack([np.ones(len(lagged)), lagged])
    params, *_ = np.linalg.lstsq(design, current, rcond=None)
    ar_intercept, phi = (float(params[0]), float(params[1]))
    innovations = current - design @ params
    innovation_std = float(np.std(innovations, ddof=1)) if len(innovations) > 1 else 0.0

    mean = None
    equilibrium_std = None
    half_life = None
    zscore = None
    zscore_method = "empirical"
    if 0 < phi < 1:
        mean = ar_intercept / (1 - phi)
        half_life = -math.log(2) / math.log(phi)
        if innovation_std > 1e-12:
            equilibrium_std = innovation_std / math.sqrt(1 - phi * phi)
            zscore = (state[-1] - mean) / equilibrium_std
            zscore_method = "ou_equilibrium"
    if zscore is None:
        empirical_std = float(np.std(state, ddof=1)) if len(state) > 1 else 0.0
        if empirical_std > 1e-12:
            mean = float(np.mean(state))
            equilibrium_std = empirical_std
            zscore = (state[-1] - mean) / empirical_std

    try:
        adf_pvalue = float(adfuller(state, regression="c", autolag="AIC")[1])
    except (ValueError, np.linalg.LinAlgError):
        adf_pvalue = None

    return {
        "state": state,
        "ar1_coefficient": _finite_float(phi),
        "equilibrium_mean": _finite_float(mean),
        "equilibrium_std": _finite_float(equilibrium_std),
        "half_life_days": _finite_float(half_life),
        "adf_pvalue": _finite_float(adf_pvalue),
        "zscore": _finite_float(zscore),
        "zscore_method": zscore_method,
    }


def _direction(zscore: float | None) -> str:
    if zscore is None:
        return "unavailable"
    if zscore >= ENTRY_Z:
        return "short_target"
    if zscore <= -ENTRY_Z:
        return "long_target"
    return "hold"


def _diagnostics(
    adf_pvalue: float | None,
    half_life: float | None,
    ar1: float | None,
    r_squared: float | None,
    largest_weight: float,
) -> tuple[str, List[str]]:
    cautions = []
    if adf_pvalue is None or adf_pvalue > 0.05:
        cautions.append("Residual ADF stationarity threshold is not met")
    if ar1 is None or not 0 < ar1 < 1:
        cautions.append("Residual path does not show positive mean reversion")
    if half_life is None:
        cautions.append("A finite residual half-life could not be estimated")
    elif half_life > 60:
        cautions.append("Estimated mean reversion takes longer than 60 sessions")
    if r_squared is None or r_squared < 0.25:
        cautions.append("Peer basket explains less than 25% of target return variance")
    if largest_weight >= 0.55:
        cautions.append("Peer basket is concentrated near the 60% weight cap")

    strong = (
        adf_pvalue is not None
        and adf_pvalue <= 0.05
        and half_life is not None
        and 1 <= half_life <= 60
        and r_squared is not None
        and r_squared >= 0.50
    )
    moderate = (
        ar1 is not None
        and 0 < ar1 < 1
        and half_life is not None
        and half_life <= 126
        and r_squared is not None
        and r_squared >= 0.25
    )
    return ("strong" if strong else "moderate" if moderate else "weak"), cautions


def fit_peer_basket(
    frame: pd.DataFrame,
    target: str,
    peers: Iterable[str],
    *,
    formation_window: int = DEFAULT_FORMATION_WINDOW,
    ridge_alpha: float = DEFAULT_RIDGE_ALPHA,
    max_peer_weight: float = MAX_PEER_WEIGHT,
    include_series: bool = False,
) -> Dict[str, Any]:
    """Fit a current signal using only the trailing formation window."""
    normalized_target = str(target).strip().upper()
    normalized_peers = _normalized_tickers(peers)
    if normalized_target in normalized_peers:
        raise ValueError("target must not also appear in peers")
    if not MIN_PEERS <= len(normalized_peers) <= MAX_PEERS:
        raise ValueError(f"peers must contain between {MIN_PEERS} and {MAX_PEERS} tickers")
    if formation_window < 60:
        raise ValueError("formation_window must be at least 60 sessions")
    if ridge_alpha < 0:
        raise ValueError("ridge_alpha must be non-negative")
    if not 0 < max_peer_weight <= 1:
        raise ValueError("max_peer_weight must be between 0 and 1")

    dates, prices = _validated_prices(frame, normalized_target, normalized_peers)
    if len(prices) < formation_window + 1:
        raise ValueError(
            f"At least {formation_window + 1} overlapping sessions are required; "
            f"received {len(prices)}"
        )

    prices = prices[-(formation_window + 1):]
    dates = dates[-(formation_window + 1):]
    returns = np.diff(np.log(prices), axis=0)
    target_returns = returns[:, 0]
    peer_returns = returns[:, 1:]
    intercept, coefficients = _fit_nonnegative_ridge(
        target_returns, peer_returns, ridge_alpha, max_peer_weight
    )
    fitted_returns = intercept + peer_returns @ coefficients
    # The tradeable long-short return cannot earn the fitted cash intercept.
    # Keep alpha for diagnostics, but form the residual portfolio from assets.
    residual_returns = target_returns - peer_returns @ coefficients
    residual_model = _fit_residual_process(residual_returns)

    total_variance = float(np.sum((target_returns - target_returns.mean()) ** 2))
    residual_variance = float(np.sum(residual_returns ** 2))
    r_squared = None if total_variance <= 1e-12 else 1 - residual_variance / total_variance
    beta = float(coefficients.sum())
    weights = coefficients / beta
    peer_weights = [
        {"ticker": ticker, "weight": float(weight)}
        for ticker, weight in zip(normalized_peers, weights)
    ]

    quality, cautions = _diagnostics(
        residual_model["adf_pvalue"],
        residual_model["half_life_days"],
        residual_model["ar1_coefficient"],
        _finite_float(r_squared),
        float(weights.max()),
    )
    zscore = residual_model["zscore"]
    report: Dict[str, Any] = {
        "target": normalized_target,
        "peers": normalized_peers,
        "as_of": dates[-1].date().isoformat(),
        "action": _direction(zscore),
        "zscore": zscore,
        "formation_window": formation_window,
        "observation_count": formation_window,
        "intercept": _finite_float(intercept),
        "hedge_beta": _finite_float(beta),
        "peer_weights": peer_weights,
        "r_squared": _finite_float(r_squared),
        "adf_pvalue": residual_model["adf_pvalue"],
        "ar1_coefficient": residual_model["ar1_coefficient"],
        "half_life_days": residual_model["half_life_days"],
        "equilibrium_mean": residual_model["equilibrium_mean"],
        "equilibrium_std": residual_model["equilibrium_std"],
        "current_residual_state": _finite_float(residual_model["state"][-1]),
        "zscore_method": residual_model["zscore_method"],
        "model_quality": quality,
        "cautions": cautions,
        "methodology_note": (
            "The signal is a point-in-time estimate from adjusted daily data. "
            "Diagnostics are advisory and do not guarantee future mean reversion."
        ),
    }
    if include_series:
        state = residual_model["state"]
        report["residual_series"] = [
            {
                "date": timestamp.date().isoformat(),
                "residual_return": _finite_float(residual_return),
                "residual_state": _finite_float(residual_state),
                "equilibrium_mean": residual_model["equilibrium_mean"],
                "entry_upper": (
                    None
                    if residual_model["equilibrium_std"] is None
                    else residual_model["equilibrium_mean"]
                    + ENTRY_Z * residual_model["equilibrium_std"]
                ),
                "entry_lower": (
                    None
                    if residual_model["equilibrium_std"] is None
                    else residual_model["equilibrium_mean"]
                    - ENTRY_Z * residual_model["equilibrium_std"]
                ),
            }
            for timestamp, residual_return, residual_state in zip(
                dates[1:], residual_returns, state
            )
        ]
    return report


def scan_peer_universe(
    frame: pd.DataFrame,
    tickers: Iterable[str],
    *,
    formation_window: int = DEFAULT_FORMATION_WINDOW,
) -> List[Dict[str, Any]]:
    normalized = _normalized_tickers(tickers)
    if not 4 <= len(normalized) <= 8:
        raise ValueError("tickers must contain between 4 and 8 unique symbols")

    candidates = [
        fit_peer_basket(
            frame,
            target,
            [ticker for ticker in normalized if ticker != target],
            formation_window=formation_window,
        )
        for target in normalized
    ]
    return sorted(
        candidates,
        key=lambda candidate: abs(candidate["zscore"] or 0.0),
        reverse=True,
    )
