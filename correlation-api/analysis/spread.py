import pandas as pd
import numpy as np
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


def calculate_zscore(spread: pd.Series, window: int | None = 60) -> pd.Series:
    """
    Calculate z-score of the spread.
    
    Args:
        spread: The spread series
        window: Rolling window size. If None, uses entire history.
    
    Returns:
        Z-score normalized spread
    """
    if window is None:
        mean = spread.mean()
        std = _safe_divisor(spread.std())
    else:
        mean = spread.rolling(window=window).mean()
        std = _safe_divisor(spread.rolling(window=window).std())
    
    return (spread - mean) / std


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
    
    zscore = calculate_zscore(spread, window=window)
    
    result_df = pd.DataFrame({
        'Date': df['Date'].values,
        f'{ticker_a}_price': series_a.values,
        f'{ticker_b}_price': series_b.values,
        'spread': spread.values,
        'zscore': zscore.values
    })
    
    clean_spread = spread.dropna()
    clean_zscore = zscore.dropna()

    metrics = {
        'spread_type': spread_type,
        'ticker_a': ticker_a,
        'ticker_b': ticker_b,
        'num_observations': len(clean_spread),
        'mean': float(clean_spread.mean()) if len(clean_spread) > 0 else 0.0,
        'std': float(clean_spread.std()) if len(clean_spread) > 0 else 0.0,
        'min': float(clean_spread.min()) if len(clean_spread) > 0 else 0.0,
        'max': float(clean_spread.max()) if len(clean_spread) > 0 else 0.0,
        'current': float(clean_spread.iloc[-1]) if len(clean_spread) > 0 else 0.0,
        'current_zscore': float(clean_zscore.iloc[-1]) if len(clean_zscore) > 0 else 0.0,
    }
    
    return result_df, metrics
