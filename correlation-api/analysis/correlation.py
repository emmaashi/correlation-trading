import pandas as pd

from analysis.util import clean_series


def compute_lagged_correlation(series_a: pd.Series, series_b: pd.Series, max_lag: int) -> pd.DataFrame:
    """
    Compute lagged correlation between two series.
    Args:
        series_a (pd.Series): First time series (e.g., df['Close_<ticker_a>']).
        series_b (pd.Series): Second time series (e.g., df['Close_<ticker_b>']).
        max_lag (int): Maximum lag (both positive and negative) to compute.
    Returns:
        pd.DataFrame: DataFrame with columns 'Lag' and 'Correlation'.
    """
    series_a = clean_series(series_a)
    series_b = clean_series(series_b)

    lags = range(-max_lag, max_lag + 1)
    correlations = []
    for lag in lags:
        if lag > 0:
            shifted_a = series_a.shift(lag)
            aligned_a, aligned_b = shifted_a.align(series_b, join='inner')
        elif lag < 0:
            shifted_b = series_b.shift(-lag)
            aligned_a, aligned_b = series_a.align(shifted_b, join='inner')
        else:
            aligned_a, aligned_b = series_a.align(series_b, join='inner')

        corr = aligned_a.corr(aligned_b) # uses Pearson formula by default for calculating the coefficient
        correlations.append(corr)
    return pd.DataFrame({"Lag": list(lags), "Correlation": correlations})
