import pandas as pd
import numpy as np
from numbers import Integral
from typing import Tuple, Dict


def _safe_divisor(divisor, tol=1e-12):
    """Replace zero or near-zero values with NaN to avoid division errors."""
    if np.isscalar(divisor):
        return np.nan if abs(divisor) < tol else divisor
    return divisor.where(divisor.abs() >= tol, np.nan)


def calculate_price_difference_spread(series_a: pd.Series, series_b: pd.Series, hedge_ratio: float = 1.0) -> pd.Series:
    """Calculate simple price difference spread."""
    return series_a - hedge_ratio * series_b


def calculate_ratio_spread(series_a: pd.Series, series_b: pd.Series, hedge_ratio: float = 1.0) -> pd.Series:
    """Calculate price ratio spread."""
    return series_a / _safe_divisor(hedge_ratio * series_b)


def calculate_log_ratio_spread(series_a: pd.Series, series_b: pd.Series, hedge_ratio: float = 1.0) -> pd.Series:
    """Calculate log price ratio spread."""
    log_a = np.log(series_a.where(series_a > 0, np.nan))
    log_b = np.log(series_b.where(series_b > 0, np.nan))
    return log_a - hedge_ratio * log_b


def calculate_zscore_components(
    spread: pd.Series, window: int = 60
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    if isinstance(window, bool) or not isinstance(window, Integral) or window < 2:
        raise ValueError("window must be an integer of at least 2")

    mean = spread.rolling(window=window, min_periods=window).mean()
    std = spread.rolling(window=window, min_periods=window).std()
    return mean, std, (spread - mean) / _safe_divisor(std)


def calculate_zscore(spread: pd.Series, window: int | None = 60) -> pd.Series:
    """
    Calculate z-score of the spread.
    
    Args:
        spread: The spread series
        window: Rolling window size.
    
    Returns:
        Z-score normalized spread
    """
    _, _, zscore = calculate_zscore_components(spread, window=window)
    return zscore


def calculate_spread_metrics(df: pd.DataFrame, ticker_a: str, ticker_b: str, 
                             spread_type: str = 'log_ratio', hedge_ratio: float = 1.0, window: int = 60) -> Tuple[pd.DataFrame, Dict]:
    """
    Calculate spread and basic metrics for a pair of stocks.
    
    Args:
        df: DataFrame with Close_{ticker_a} and Close_{ticker_b} columns
        ticker_a: First ticker symbol
        ticker_b: Second ticker symbol
        spread_type: Type of spread ('difference', 'ratio', or 'log_ratio')
        hedge_ratio: Ratio for hedging the B ticker
        
    Returns:
        Tuple of (result DataFrame, metrics dict)
    """
    # Extract price series and ensure they're 1D
    series_a = df[f'Close_{ticker_a}'].squeeze()
    series_b = df[f'Close_{ticker_b}'].squeeze()
 
    if isinstance(series_a, pd.DataFrame):
        series_a = pd.Series(series_a.values.flatten(), index=df.index)
    if isinstance(series_b, pd.DataFrame):
        series_b = pd.Series(series_b.values.flatten(), index=df.index)
    
    if spread_type == 'difference':
        spread = calculate_price_difference_spread(series_a, series_b, hedge_ratio)
    elif spread_type == 'ratio':
        spread = calculate_ratio_spread(series_a, series_b, hedge_ratio)
    elif spread_type == 'log_ratio':
        spread = calculate_log_ratio_spread(series_a, series_b, hedge_ratio)
    else:
        raise ValueError(f"Unknown spread_type: {spread_type}")
    
    rolling_mean, rolling_std, zscore = calculate_zscore_components(
        spread, window=window
    )
    band_1_upper = rolling_mean + rolling_std
    band_1_lower = rolling_mean - rolling_std
    band_2_upper = rolling_mean + 2 * rolling_std
    band_2_lower = rolling_mean - 2 * rolling_std
    
    result_df = pd.DataFrame({
        'Date': df['Date'].values,
        f'{ticker_a}_price': series_a.values,
        f'{ticker_b}_price': series_b.values,
        'spread': spread.values,
        'rolling_mean': rolling_mean.values,
        'rolling_std': rolling_std.values,
        'band_1_upper': band_1_upper.values,
        'band_1_lower': band_1_lower.values,
        'band_2_upper': band_2_upper.values,
        'band_2_lower': band_2_lower.values,
        'zscore': zscore.values,
    })
    
    clean_spread = spread.dropna()

    def finite_value(value):
        if pd.isna(value):
            return None
        value = float(value)
        return value if np.isfinite(value) else None

    def current_value(series):
        if series.empty or pd.isna(series.iloc[-1]):
            return None
        return finite_value(series.iloc[-1])

    metrics = {
        'spread_type': spread_type,
        'ticker_a': ticker_a,
        'ticker_b': ticker_b,
        'zscore_window': window,
        'num_observations': len(clean_spread),
        'descriptive_mean': finite_value(clean_spread.mean()),
        'descriptive_std': finite_value(clean_spread.std()),
        'descriptive_min': finite_value(clean_spread.min()),
        'descriptive_max': finite_value(clean_spread.max()),
        'current': current_value(spread),
        'current_mean': current_value(rolling_mean),
        'current_std': current_value(rolling_std),
        'current_band_1_upper': current_value(band_1_upper),
        'current_band_1_lower': current_value(band_1_lower),
        'current_band_2_upper': current_value(band_2_upper),
        'current_band_2_lower': current_value(band_2_lower),
        'current_zscore': current_value(zscore),
    }
    
    return result_df, metrics
