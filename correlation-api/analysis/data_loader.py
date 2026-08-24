import os
import threading

import numpy as np
import pandas as pd
import yfinance as yf

CACHE_VERSION = "v4"
DOWNLOAD_LOCK = threading.Lock()

REQUIRED_DATA_COLUMNS = (
    "Date",
    "Close",
    "RawClose",
    "Dividends",
    "StockSplits",
    "Ticker",
)
REQUIRED_NUMERIC_COLUMNS = (
    "Close",
    "RawClose",
    "Dividends",
    "StockSplits",
)
OPTIONAL_ACTION_COLUMNS = ("CapitalGains",)
DOWNLOAD_FIELD_MAP = {
    "Adj Close": "Close",
    "Close": "RawClose",
    "Dividends": "Dividends",
    "Stock Splits": "StockSplits",
}


def _parse_requested_date(value, label):
    try:
        if isinstance(value, str):
            parsed = pd.to_datetime(value, format="%Y-%m-%d", errors="raise")
        else:
            parsed = pd.to_datetime(value, errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a valid YYYY-MM-DD date") from exc

    if not isinstance(parsed, pd.Timestamp) or pd.isna(parsed):
        raise ValueError(f"{label} must be a single valid date")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_localize(None)
    return parsed.normalize()


def _validate_date_range(start_date, end_date):
    requested_start = _parse_requested_date(start_date, "start_date")
    requested_end = _parse_requested_date(end_date, "end_date")
    if requested_start > requested_end:
        raise ValueError("start_date must be on or before end_date")
    return requested_start, requested_end


def _exclusive_download_end(end_date):
    """Convert the API's inclusive end date to yfinance's exclusive end date."""
    requested_end = _parse_requested_date(end_date, "end_date")
    return (requested_end + pd.Timedelta(days=1)).date().isoformat()


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
    requested_start, requested_end = _validate_date_range(start_date, end_date)
    start = requested_start.date().isoformat()
    end = requested_end.date().isoformat()
    filename = f"{ticker}_{start}_to_{end}_{CACHE_VERSION}_raw.csv"
    return os.path.join(folder, filename)


def _validated_market_data(df, ticker, start_date, end_date):
    """Return a type-normalized market-data frame or raise for invalid data."""
    requested_start, requested_end = _validate_date_range(start_date, end_date)
    if not isinstance(df, pd.DataFrame):
        raise ValueError("market data must be a DataFrame")
    missing_columns = set(REQUIRED_DATA_COLUMNS).difference(df.columns)
    if df.empty:
        raise ValueError("market data is empty")
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"market data is missing required columns: {missing}")

    output_columns = list(REQUIRED_DATA_COLUMNS)
    output_columns.extend(
        column for column in OPTIONAL_ACTION_COLUMNS if column in df.columns
    )
    validated = df.loc[:, output_columns].copy()

    dates = pd.to_datetime(validated["Date"], errors="coerce")
    if dates.isna().any():
        raise ValueError("Date contains invalid or missing values")
    dates = dates.dt.tz_localize(None).dt.normalize()
    if dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise ValueError("Date values must be unique and sorted in ascending order")
    validated["Date"] = dates

    numeric_columns = list(REQUIRED_NUMERIC_COLUMNS)
    numeric_columns.extend(
        column for column in OPTIONAL_ACTION_COLUMNS if column in validated.columns
    )
    for column in numeric_columns:
        values = pd.to_numeric(validated[column], errors="coerce")
        if values.isna().any() or not np.isfinite(values).all():
            raise ValueError(f"{column} contains invalid or missing numeric values")
        validated[column] = values.astype(float)

    for column in ("Close", "RawClose"):
        if (validated[column] <= 0).any():
            raise ValueError(f"{column} must contain strictly positive prices")
    for column in ("Dividends", "StockSplits", *OPTIONAL_ACTION_COLUMNS):
        if column in validated.columns and (validated[column] < 0).any():
            raise ValueError(f"{column} must contain non-negative action values")

    tickers = validated["Ticker"].astype("string").str.strip().str.upper()
    if tickers.isna().any() or not (tickers == ticker.upper()).all():
        raise ValueError(f"Ticker values must all match {ticker.upper()}")
    validated["Ticker"] = ticker.upper()

    first_date = dates.min()
    last_date = dates.max()

    # Allow a few calendar days for weekends and holidays. Long Max ranges can
    # legitimately start late for newer listings, such as BJ's 2018 IPO.
    requested_days = max((requested_end - requested_start).days, 1)
    actual_days = max((last_date - first_date).days, 0)
    long_range_with_later_listing = (
        requested_days >= 365 * 7 and actual_days / requested_days >= 0.75
    )

    if (
        first_date > requested_start + pd.Timedelta(days=7)
        and not long_range_with_later_listing
    ):
        raise ValueError("market data starts too late for the requested date range")
    if last_date < requested_end - pd.Timedelta(days=7):
        raise ValueError("market data ends too early for the requested date range")

    return validated


def _cache_is_valid(df, ticker, start_date, end_date):
    try:
        _validated_market_data(df, ticker, start_date, end_date)
    except (AttributeError, TypeError, ValueError):
        return False
    return True


def _download_field(df, field, ticker, required=True):
    """Select one field from a single-ticker yfinance download."""
    if isinstance(df.columns, pd.MultiIndex):
        matching_levels = [
            level
            for level in range(df.columns.nlevels)
            if field in df.columns.get_level_values(level)
        ]
        if not matching_levels:
            selected = None
        elif len(matching_levels) > 1:
            raise ValueError(
                f"Downloaded data for {ticker} has an ambiguous {field!r} field"
            )
        else:
            selected = df.xs(field, axis="columns", level=matching_levels[0])
    else:
        selected = df[field] if field in df.columns else None

    if selected is None:
        if required:
            raise ValueError(
                f"Downloaded data for {ticker} is missing required {field!r} data"
            )
        return None

    if isinstance(selected, pd.DataFrame):
        if selected.shape[1] != 1:
            raise ValueError(
                f"Downloaded data for {ticker} contains multiple {field!r} series"
            )
        selected = selected.iloc[:, 0]

    return selected.reset_index(drop=True)


def _normalize_downloaded_data(df, ticker):
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError(f"Downloaded data for {ticker} is empty")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"Downloaded data for {ticker} does not have a date index")

    normalized = {"Date": pd.Series(df.index).reset_index(drop=True)}
    for download_field, output_field in DOWNLOAD_FIELD_MAP.items():
        normalized[output_field] = _download_field(df, download_field, ticker)

    capital_gains = _download_field(df, "Capital Gains", ticker, required=False)
    if capital_gains is not None:
        normalized["CapitalGains"] = capital_gains
    normalized["Ticker"] = ticker

    return pd.DataFrame(normalized)


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
        pd.DataFrame: Adjusted research close, raw close, and action data.
    """
    requested_start, requested_end = _validate_date_range(start_date, end_date)
    start = requested_start.date().isoformat()
    end = requested_end.date().isoformat()
    path = get_data_path(ticker, start_date, end_date)
    if cache and os.path.exists(path):
        try:
            cached = pd.read_csv(path)
            return _validated_market_data(cached, ticker, start, end)
        except (OSError, TypeError, UnicodeError, ValueError, pd.errors.ParserError):
            pass

    # yfinance uses shared module-level state during downloads. Concurrent
    # single-ticker downloads can leak one ticker's data into another result.
    with DOWNLOAD_LOCK:
        downloaded = yf.download(
            ticker,
            start=start,
            end=_exclusive_download_end(end),
            progress=False,
            auto_adjust=False,
            actions=True,
            threads=False,
        ).copy()

    df = _normalize_downloaded_data(downloaded, ticker)
    try:
        df = _validated_market_data(df, ticker, start, end)
    except ValueError as exc:
        raise ValueError(f"Invalid downloaded data for {ticker}: {exc}") from exc

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

    # Retain each ticker's raw prices and actions without merge suffix ambiguity.
    df_a = df_a.rename(
        columns={column: f"{column}_{ticker_a}" for column in df_a if column != "Date"}
    )
    df_b = df_b.rename(
        columns={column: f"{column}_{ticker_b}" for column in df_b if column != "Date"}
    )

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
