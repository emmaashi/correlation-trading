import os
import threading
import pandas as pd
import yfinance as yf

CACHE_VERSION = "v3"
DOWNLOAD_LOCK = threading.Lock()


def _exclusive_download_end(end_date):
    """Convert the API's inclusive end date to yfinance's exclusive end date."""
    return (pd.to_datetime(end_date) + pd.Timedelta(days=1)).date().isoformat()


def get_data_path(ticker, start_date, end_date, folder="data/raw"):
    """
    Generate the file path for storing or loading a stock's raw data CSV.

    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL').
        start_date (str): Start date of the data (YYYY-MM-DD).
        end_date (str): End date of the data (YYYY-MM-DD).
        folder (str): Folder where the file should be stored or searched.

    Returns:
        str: Full file path for the cached CSV file.
    """
    filename = f"{ticker}_{start_date}_to_{end_date}_{CACHE_VERSION}_raw.csv"
    return os.path.join(folder, filename)


def _cache_is_valid(df, ticker, start_date, end_date):
    required_columns = {"Date", "Close", "Ticker"}
    if df.empty or not required_columns.issubset(df.columns):
        return False

    dates = pd.to_datetime(df["Date"], errors="coerce")
    closes = pd.to_numeric(df["Close"], errors="coerce")
    tickers = df["Ticker"].astype(str).str.upper()

    if dates.isna().any() or closes.isna().all():
        return False
    if not (tickers == ticker.upper()).all():
        return False

    requested_start = pd.to_datetime(start_date)
    requested_end = pd.to_datetime(end_date)
    first_date = dates.min()
    last_date = dates.max()

    # Allow a few calendar days for weekends and holidays. Long Max ranges can
    # legitimately start late for newer listings, such as BJ's 2018 IPO.
    requested_days = max((requested_end - requested_start).days, 1)
    actual_days = max((last_date - first_date).days, 0)
    long_range_with_later_listing = (
        requested_days >= 365 * 7 and actual_days / requested_days >= 0.75
    )

    if first_date > requested_start + pd.Timedelta(days=7) and not long_range_with_later_listing:
        return False
    if last_date < requested_end - pd.Timedelta(days=7):
        return False

    return True


def _normalize_downloaded_data(df, ticker):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    if "Date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "Date"})

    df = df.loc[:, ~df.columns.duplicated()]
    close_col = df["Close"]
    if isinstance(close_col, pd.DataFrame):
        close_col = close_col.iloc[:, 0]

    return pd.DataFrame({"Date": df["Date"], "Close": close_col, "Ticker": ticker})


def _write_cache_atomic(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
    try:
        df.to_csv(temp_path, index=False)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def get_stock_data(ticker, start_date, end_date, cache=True):
    """
    Fetch historical stock price data using yfinance, with optional caching.

    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL').
        start_date (str): Start date of the data (YYYY-MM-DD).
        end_date (str): End date of the data (YYYY-MM-DD).
        cache (bool): If True, load from or save to local CSV cache.

    Returns:
        pd.DataFrame: DataFrame with columns ['Date', 'Close', 'Ticker'].
    """
    path = get_data_path(ticker, start_date, end_date)
    if cache and os.path.exists(path):
        cached = pd.read_csv(path, parse_dates=["Date"])
        cached = cached.loc[:, ~cached.columns.duplicated()]
        if isinstance(cached["Close"], pd.DataFrame):
            cached["Close"] = cached["Close"].iloc[:, 0]
        cached = cached[["Date", "Close", "Ticker"]]
        if _cache_is_valid(cached, ticker, start_date, end_date):
            return cached

    # yfinance uses shared module-level state during downloads. Concurrent
    # single-ticker downloads can leak one ticker's data into another result.
    with DOWNLOAD_LOCK:
        downloaded = yf.download(
            ticker,
            start=start_date,
            end=_exclusive_download_end(end_date),
            progress=False,
            auto_adjust=False,
            threads=False,
        ).copy()

    df = _normalize_downloaded_data(downloaded, ticker)
    if not _cache_is_valid(df, ticker, start_date, end_date):
        raise ValueError(f"Downloaded data for {ticker} does not cover the requested date range")
    
    if cache:
        _write_cache_atomic(df, path)
    
    return df


def load_pair_data(ticker_a, ticker_b, start_date, end_date, cache=True):
    """
    Load and align historical price data for a pair of stocks.

    Args:
        ticker_a (str): First stock ticker (e.g., 'AAPL').
        ticker_b (str): Second stock ticker (e.g., 'MSFT').
        start_date (str): Start date for both stocks.
        end_date (str): End date for both stocks.
        cache (bool): Whether to cache individual stock data locally.

    Returns:
        pd.DataFrame: Merged DataFrame with aligned 'Date', 'Close_<ticker>' columns.
    """
    print(f"Loading data for {ticker_a}")
    df_a = get_stock_data(ticker_a, start_date, end_date, cache)

    print(f"Loading data for {ticker_b}")
    df_b = get_stock_data(ticker_b, start_date, end_date, cache)

    # Rename columns before merging to ensure consistent naming
    df_a = df_a.rename(columns={'Close': f'Close_{ticker_a}', 'Ticker': f'Ticker_{ticker_a}'})
    df_b = df_b.rename(columns={'Close': f'Close_{ticker_b}', 'Ticker': f'Ticker_{ticker_b}'})
    
    # Merge on Date
    merged = pd.merge(df_a, df_b, on="Date")
    return merged


def load_multiple_pairs(pairs, start_date, end_date, cache=True):
    """
    Load and align historical data for multiple stock pairs.

    Args:
        pairs (list of tuples): List of (ticker_a, ticker_b) pairs.
        start_date (str): Start date for all data fetches.
        end_date (str): End date for all data fetches.
        cache (bool): Whether to cache and reuse raw data.

    Returns:
        dict: Dictionary mapping (ticker_a, ticker_b) → merged DataFrame.
    """
    pair_data = {}
    for ticker_a, ticker_b in pairs:
        df = load_pair_data(ticker_a, ticker_b, start_date, end_date, cache)
        pair_data[(ticker_a, ticker_b)] = df
    return pair_data
