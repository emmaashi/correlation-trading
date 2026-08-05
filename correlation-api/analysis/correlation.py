import pandas as pd

from analysis.util import calculate_log_returns


def compute_lagged_correlation(series_a: pd.Series, series_b: pd.Series, max_lag: int) -> pd.DataFrame:
    """
    Compute lagged correlation between the daily log returns of two price series.
    Args:
        series_a (pd.Series): First time series (e.g., df['Close_<ticker_a>']).
        series_b (pd.Series): Second time series (e.g., df['Close_<ticker_b>']).
        max_lag (int): Maximum lag (both positive and negative) to compute.
    Returns:
        pd.DataFrame: DataFrame with columns 'Lag' and 'Correlation'.
    """
    returns_a = calculate_log_returns(series_a)
    returns_b = calculate_log_returns(series_b)

    lags = range(-max_lag, max_lag + 1)
    correlations = []
    for lag in lags:
        if lag > 0:
            shifted_a = returns_a.shift(lag)
            aligned_a, aligned_b = shifted_a.align(returns_b, join='inner')
        elif lag < 0:
            shifted_b = returns_b.shift(-lag)
            aligned_a, aligned_b = returns_a.align(shifted_b, join='inner')
        else:
            aligned_a, aligned_b = returns_a.align(returns_b, join='inner')

        corr = aligned_a.corr(aligned_b)
        correlations.append(corr)
    return pd.DataFrame({"Lag": list(lags), "Correlation": correlations})
