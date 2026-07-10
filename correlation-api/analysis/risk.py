from typing import Optional

import pandas as pd

from analysis.util import clean_series


ABSOLUTE_CORRELATION_FLOOR = 0.5
MIN_BASELINE_OBSERVATIONS = 60
MIN_POSITIVE_BASELINE_CORRELATION = 0.1


def _iso_date(index_value) -> str:
    parsed = pd.to_datetime(index_value, errors="coerce")
    if not pd.isna(parsed):
        return parsed.date().isoformat()
    return str(index_value)


def _safe_current(series: pd.Series) -> Optional[float]:
    if series.empty or pd.isna(series.iloc[-1]):
        return None
    return float(series.iloc[-1])


def detect_correlation_breakdown(
    series_a: pd.Series,
    series_b: pd.Series,
    recent_window: int = 60,
    baseline_window: int = 252,
    threshold: float = 0.5,
) -> dict:
    """
    Detect whether a pair's recent rolling correlation has broken down.

    The detector compares the latest recent-window correlation with the
    trailing baseline mean of those recent-window correlations. The baseline is
    shifted by one row so the current correlation does not dilute its own
    comparison point. It only evaluates breakdowns when the baseline indicates
    an established positive relationship.
    """
    if recent_window < 2:
        raise ValueError("recent_window must be at least 2")
    if baseline_window < 1:
        raise ValueError("baseline_window must be at least 1")
    if threshold <= 0:
        raise ValueError("threshold must be positive")

    aligned = pd.concat(
        [clean_series(series_a).rename("a"), clean_series(series_b).rename("b")],
        axis=1,
        join="inner",
    ).dropna()

    if len(aligned) < recent_window + 1:
        return {
            "current_corr": None,
            "baseline_corr": None,
            "broken": False,
            "broken_since": None,
        }

    rolling_corr = aligned["a"].rolling(window=recent_window).corr(aligned["b"])
    min_baseline_periods = min(baseline_window, MIN_BASELINE_OBSERVATIONS)
    baseline_corr = (
        rolling_corr.shift(1)
        .rolling(window=baseline_window, min_periods=min_baseline_periods)
        .mean()
    )

    current_corr = _safe_current(rolling_corr)
    current_baseline = _safe_current(baseline_corr)

    valid_comparison = rolling_corr.notna() & baseline_corr.notna()
    positive_baseline = baseline_corr > MIN_POSITIVE_BASELINE_CORRELATION
    relative_breakdown = rolling_corr < baseline_corr * threshold
    absolute_breakdown = rolling_corr < ABSOLUTE_CORRELATION_FLOOR
    broken_points = (
        valid_comparison
        & positive_baseline
        & (relative_breakdown | absolute_breakdown)
    )

    broken = bool(broken_points.iloc[-1]) if not broken_points.empty else False
    broken_since = None

    if broken:
        current_run = broken_points[broken_points].index
        last_index = broken_points.index[-1]

        for idx in reversed(broken_points.index):
            if idx == last_index and not broken_points.loc[idx]:
                break
            if not broken_points.loc[idx]:
                break
            broken_since = idx

        if broken_since is None and len(current_run) > 0:
            broken_since = current_run[-1]

    return {
        "current_corr": current_corr,
        "baseline_corr": current_baseline,
        "broken": broken,
        "broken_since": _iso_date(broken_since) if broken_since is not None else None,
    }
