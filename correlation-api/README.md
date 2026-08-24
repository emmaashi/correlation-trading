# Correlation Trading API

Flask backend powering the **Correlation Trading** app. Computes lagged correlation and spread metrics for stock pairs on demand, using Yahoo Finance data fetched via `yfinance`.

## Run

```bash
cd correlation-api
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Defaults to **port 5050**. Override with `CORRELATION_API_PORT=5060 python app.py`.

The Next dev server (`npm run dev` in the repo root) rewrites browser requests from `/api/*` to `http://localhost:5050/api/*`, so the app works once both processes are running.

## Test

From `correlation-api`, run the same command used in CI:

```bash
python -m unittest discover -v
```

The suite mocks market-data downloads and does not require network access.

## Endpoints

| Method | Path | Query | Returns |
|--------|------|-------|---------|
| GET | `/api/pairs` | — | The 15 pre-configured pairs (tickers, names, sector) |
| GET | `/api/validate` | `ticker` | `{valid, ticker, name}` — used to validate custom ticker input |
| GET | `/api/correlation` | `ticker_a`, `ticker_b`, `start`, `end`, `max_lag` | Lagged Pearson correlation of daily log returns across `[-max_lag, +max_lag]` |
| GET | `/api/spread` | `ticker_a`, `ticker_b`, `start`, `end`, `spread_type` | Spread series, z-score, and metrics for the pair |
| GET | `/api/risk/breakdown` | `ticker_a`, `ticker_b`, optional `end`, optional `start` override | Return-correlation breakdown signal with its own lookback window, current 60d correlation, baseline, reason, and `broken_since` |

Dates are `YYYY-MM-DD`. `spread_type` is one of the values supported by `analysis/spread.py` (default `log_ratio`).

## How data is pulled

1. **Browser request** lands on the Flask endpoint (e.g. `/api/correlation?ticker_a=MSFT&ticker_b=GOOGL&start=2023-01-01&end=2026-01-01`).
2. **`load_pair_data`** (`analysis/data_loader.py`) fetches each ticker via `get_stock_data`, then inner-joins on `Date`.
3. **`get_stock_data`** is the cache layer:
   - Looks for `data/raw/<TICKER>_<start>_to_<end>_<VERSION>_raw.csv` — if present and valid, reads it and returns immediately.
   - Otherwise calls `yfinance.download(ticker, start, end)`, normalises columns to `[Date, Close, Ticker]`, writes the CSV, and returns.
4. **Analysis modules** (`correlation.py`, `spread.py`) consume the merged DataFrame and produce the JSON the frontend renders.

The cache key is the **exact** `(ticker, start, end)` tuple, so different date ranges produce different files. Cache files live under `correlation-api/data/raw/` and are gitignored — wipe them anytime to force a fresh fetch.

```
correlation-api/
├── app.py                    # Flask app + route handlers
├── analysis/
│   ├── data_loader.py        # yfinance fetch + CSV cache
│   ├── correlation.py        # Lagged Pearson correlation of log returns
│   └── spread.py             # Spread series, rolling z-score, metrics
├── data/raw/                 # CSV cache (gitignored)
└── requirements.txt
```

## Configuring the pair list

Keep the `PAIRS` lists in `app.py` and `../lib/correlationTypes.ts` synchronized. Each entry needs `ticker_a`, `ticker_b`, `name_a`, `name_b`, and `sector`.

## Troubleshooting

- **`Connection refused` from the site** → Flask isn't running, or it's on a port other than 5050. Check the rewrite in `../next.config.mjs`.
- **`yfinance` returns empty** → ticker symbol invalid, or Yahoo throttled the IP. Delete the cached CSV (if any) and retry; switch networks if it persists.
- **Stale data** → cache is keyed by date range. Delete files in `data/raw/` to refetch.
