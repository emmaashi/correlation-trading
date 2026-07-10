import pandas as pd


def clean_series(series: pd.Series) -> pd.Series:
    cleaned = series.copy()
    if not cleaned.empty and not pd.api.types.is_numeric_dtype(cleaned.iloc[0]):
        cleaned = cleaned.iloc[1:]

    numeric = pd.to_numeric(cleaned, errors="coerce")
    if not isinstance(numeric, pd.Series):
        numeric = pd.Series(numeric, index=cleaned.index)
    return numeric
