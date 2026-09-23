"""Statistical validation for a two-asset mean-reversion model.

These diagnostics provide evidence that a historical relationship may support a
pair model. They do not guarantee that the relationship or its mean reversion
will persist out of sample.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from statsmodels.tsa.stattools import adfuller, coint


MIN_OBSERVATIONS = 252
SIGNIFICANCE_LEVEL = 0.05
MIN_HALF_LIFE_DAYS = 1.0
MAX_HALF_LIFE_DAYS = 126.0

INSUFFICIENT_HISTORY = "insufficient_history"
INVALID_DATA = "invalid_data"
INVALID_HEDGE_RATIO = "invalid_hedge_ratio"
FAILED_COINTEGRATION = "cointegration_not_significant"
FAILED_STATIONARITY = "residual_not_stationary"
NON_MEAN_REVERTING = "non_mean_reverting"
IMPLAUSIBLE_HALF_LIFE = "implausible_half_life"

METHODOLOGY_NOTE = (
    "This current-snapshot diagnostic fits the full selected history. The tests "
    "provide evidence, not a backtest, a point-in-time historical simulation, or "
    "a guarantee of future mean reversion or trading performance."
)


def _finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _empty_report(
    observation_count: int,
    zscore_window: int | None,
    min_observations: int,
    significance_level: float,
    min_half_life_days: float,
    max_half_life_days: float,
) -> Dict[str, Any]:
    return {
        "eligible": False,
        "rejection_reasons": [],
        "observation_count": observation_count,
        "intercept": None,
        "hedge_ratio": None,
        "cointegration_pvalue": None,
        "adf_pvalue": None,
        "ar1_coefficient": None,
        "half_life_days": None,
        "residual_zscore_window": zscore_window,
        "residual_zscore_observations": 0,
        "current_residual": None,
        "current_residual_mean": None,
        "current_residual_std": None,
        "current_residual_zscore": None,
        "signal_zscore": None,
        "diagnostic_scope": "current_snapshot",
        "thresholds": {
            "min_observations": min_observations,
            "significance_level": significance_level,
            "min_half_life_days": min_half_life_days,
            "max_half_life_days": max_half_life_days,
        },
        "methodology_note": METHODOLOGY_NOTE,
    }


def _append_reason(reasons: List[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def validate_pair_model(
    prices_a: pd.Series,
    prices_b: pd.Series,
    *,
    zscore_window: int | None = 60,
    min_observations: int = MIN_OBSERVATIONS,
    significance_level: float = SIGNIFICANCE_LEVEL,
    min_half_life_days: float = MIN_HALF_LIFE_DAYS,
    max_half_life_days: float = MAX_HALF_LIFE_DAYS,
) -> Dict[str, Any]:
    """Fit and validate ``log(A) = intercept + hedge_ratio * log(B) + spread``.

    Inputs are aligned by index before validation. Missing, infinite, or
    nonpositive aligned prices invalidate the model instead of being silently
    discarded.
    """

    aligned = pd.concat(
        [
            pd.to_numeric(pd.Series(prices_a), errors="coerce").rename("price_a"),
            pd.to_numeric(pd.Series(prices_b), errors="coerce").rename("price_b"),
        ],
        axis=1,
        join="inner",
    )
    observation_count = len(aligned)
    report = _empty_report(
        observation_count,
        zscore_window,
        min_observations,
        significance_level,
        min_half_life_days,
        max_half_life_days,
    )
    reasons: List[str] = report["rejection_reasons"]

    if observation_count < min_observations:
        reasons.append(INSUFFICIENT_HISTORY)
        return report

    values = aligned.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        reasons.append(INVALID_DATA)
        return report

    log_a = np.log(values[:, 0])
    log_b = np.log(values[:, 1])
    design = add_constant(log_b, has_constant="add")
    if np.linalg.matrix_rank(design) < design.shape[1]:
        reasons.append(INVALID_HEDGE_RATIO)
        return report

    ols_result = OLS(log_a, design).fit()
    intercept = _finite_float(ols_result.params[0])
    hedge_ratio = _finite_float(ols_result.params[1])
    report["intercept"] = intercept
    report["hedge_ratio"] = hedge_ratio

    if intercept is None or hedge_ratio is None or hedge_ratio <= 0:
        _append_reason(reasons, INVALID_HEDGE_RATIO)

    residual = np.asarray(ols_result.resid, dtype=float)
    residual_window = residual if zscore_window is None else residual[-zscore_window:]
    report["residual_zscore_observations"] = len(residual_window)
    report["current_residual"] = _finite_float(residual[-1])
    if len(residual_window) > 0:
        residual_mean = _finite_float(np.mean(residual_window))
        report["current_residual_mean"] = residual_mean
    if len(residual_window) > 1:
        residual_std = _finite_float(np.std(residual_window, ddof=1))
        report["current_residual_std"] = residual_std
        if residual_std is not None and residual_std > 1e-12:
            report["current_residual_zscore"] = _finite_float(
                (residual[-1] - residual_mean) / residual_std
            )

    try:
        cointegration_pvalue = _finite_float(
            coint(log_a, log_b, trend="c", autolag="aic")[1]
        )
    except (ValueError, np.linalg.LinAlgError):
        cointegration_pvalue = None
    report["cointegration_pvalue"] = cointegration_pvalue
    if cointegration_pvalue is None or cointegration_pvalue > significance_level:
        _append_reason(reasons, FAILED_COINTEGRATION)

    try:
        adf_pvalue = _finite_float(
            adfuller(residual, regression="n", autolag="AIC")[1]
        )
    except (ValueError, np.linalg.LinAlgError):
        adf_pvalue = None
    report["adf_pvalue"] = adf_pvalue
    if adf_pvalue is None or adf_pvalue > significance_level:
        _append_reason(reasons, FAILED_STATIONARITY)

    lagged_residual = residual[:-1]
    current_residual = residual[1:]
    ar_design = add_constant(lagged_residual, has_constant="add")
    if np.linalg.matrix_rank(ar_design) < ar_design.shape[1]:
        ar1_coefficient = None
    else:
        ar1_coefficient = _finite_float(
            OLS(current_residual, ar_design).fit().params[1]
        )
    report["ar1_coefficient"] = ar1_coefficient

    half_life_days = None
    if ar1_coefficient is None or not 0 < ar1_coefficient < 1:
        _append_reason(reasons, NON_MEAN_REVERTING)
    else:
        half_life_days = _finite_float(-math.log(2) / math.log(ar1_coefficient))
    report["half_life_days"] = half_life_days

    if half_life_days is not None and not (
        min_half_life_days <= half_life_days <= max_half_life_days
    ):
        _append_reason(reasons, IMPLAUSIBLE_HALF_LIFE)

    report["eligible"] = not reasons
    if report["eligible"]:
        report["signal_zscore"] = report["current_residual_zscore"]
    return report
