# Correlation Trading API

Flask backend powering the **Correlation Trading** app. It computes pair
correlation and spread metrics, model diagnostics, risk warnings, and
peer-basket scanner results from Yahoo Finance data fetched through `yfinance`.

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

| Method | Path | Inputs | Returns |
|--------|------|-------|---------|
| GET | `/api/pairs` | — | The 15 pre-configured pairs (tickers, names, sector) |
| GET | `/api/strategy/universes` | — | The 12 editable peer-group presets and supported universe size |
| POST | `/api/strategy/scan` | JSON body with `tickers`, optional `start`, optional `end` | Every ticker ranked as a target against the remaining peer basket |
| GET | `/api/validate` | `ticker` | `{valid, ticker, name}` — used to validate custom ticker input |
| GET | `/api/correlation` | `ticker_a`, `ticker_b`, `start`, `end`, `max_lag` | Lagged Pearson correlation of daily log returns across `[-max_lag, +max_lag]` |
| GET | `/api/spread` | `ticker_a`, `ticker_b`, `start`, `end`, `spread_type`, `window` | Descriptive spread series plus current pair-model eligibility and residual signal diagnostics |
| GET | `/api/signal` | `ticker_a`, `ticker_b`, `start`, `end`, `window` | Compact log-ratio z-score and Short, Long, or Hold direction for pair cards |
| GET | `/api/risk/breakdown` | `ticker_a`, `ticker_b`, optional `end`, optional `start` override | Return-correlation breakdown signal with its own lookback window, current 60d correlation, baseline, reason, and `broken_since` |

Dates are `YYYY-MM-DD`. `spread_type` is one of the values supported by `analysis/spread.py` (default `log_ratio`).

## Strategy scanner

The Strategy Lab scanner accepts 4-8 unique ticker strings. For each ticker, it
uses the other 3-7 stocks as a peer basket and fits the latest 252 daily returns.
Peer weights are nonnegative, sum to one after normalization, and are capped at
60% each. The response includes:

- Long Target, Short Target, or Hold based on a residual z-score threshold of
  `-2` or `+2`
- Hedge beta and normalized peer weights
- R-squared, ADF p-value, AR(1) coefficient, and estimated half-life
- Strong, moderate, or weak model quality plus specific cautions
- Observation dates, data-quality warnings, and survivorship-bias disclosure

The endpoint ranks candidates by absolute residual z-score. Diagnostics remain
advisory: a weak model can still return a directional research signal with
cautions. The visible Strategy Lab and walk-forward backtester are not on
`main` yet.

## Pair-model diagnostics

The spread response includes a supplemental `pair_model` object for evaluating
the historical relationship behind a pair. The validator aligns
positive prices, models `log(A) = intercept + hedge_ratio * log(B) + residual`,
and reports:

- OLS intercept and hedge ratio
- Engle-Granger cointegration and residual ADF p-values
- Residual AR(1) coefficient and estimated mean-reversion half-life
- Current fitted residual, trailing-window mean, standard deviation, and z-score
- Aligned observation count, eligibility, thresholds, and machine-readable
  rejection reasons

`current_residual_zscore` uses the OLS residual and the same trailing `window`
requested for the descriptive spread (60 observations by default).
`signal_zscore` is that residual z-score when every model check passes and
`null` otherwise. The frontend treats these checks as advisory diagnostics. Its
Short, Long, and Hold decision uses `metrics.current_zscore` from the fixed
60-day log-ratio spread, preserving a signal even when model cautions exist.

Eligibility requires at least 252 observations, a positive finite hedge ratio,
both p-values at or below 0.05, stable `0 < AR(1) < 1` dynamics, and a half-life
between 1 and 126 trading days. Rejection reasons are
`insufficient_history`, `invalid_data`, `invalid_hedge_ratio`,
`cointegration_not_significant`, `residual_not_stationary`,
`non_mean_reverting`, and `implausible_half_life`.

This endpoint is a current-snapshot diagnostic: the OLS model is fit over the
full selected history and the latest residual is standardized against its
trailing window. It does not produce a point-in-time historical simulation or
backtest. These tests are statistical evidence, not guarantees of future mean
reversion or trading performance.

## How data is pulled

1. **Browser request** lands on the Flask endpoint (e.g. `/api/correlation?ticker_a=MSFT&ticker_b=GOOGL&start=2023-01-01&end=2026-01-01`).
2. **`load_pair_data`** delegates to `load_universe_data`, which fetches every
   unique ticker once and inner-joins all rows on `Date`.
3. **`get_stock_data`** is the cache layer:
   - Looks for `data/raw/<TICKER>_<start>_to_<end>_<VERSION>_raw.csv` — if present and valid, reads it and returns immediately.
   - Otherwise calls `yfinance.download` with `auto_adjust=False` and
     `actions=True`. This preserves raw OHLCV, adjusted close, and available
     corporate-action data in one response.
   - Rejects downloads without `Adj Close`; research prices never silently fall back to raw close.
   - Uses `Adj Close / RawClose` as the daily adjustment factor for adjusted
     Open, High, and Low prices.
   - Validates the requested date range, row dates, OHLC prices, volume, and
     action values before writing the CSV.
4. **Analysis modules** consume the aligned DataFrame and produce pair metrics,
   risk warnings, model diagnostics, or peer-basket scanner results.

### Market data contract

`get_stock_data` returns one row per trading date with the following columns:

| Column | Meaning |
|--------|---------|
| `Date` | Unique, ascending, timezone-naive trading date |
| `Open`, `High`, `Low` | Raw Yahoo OHLC multiplied by the daily close-adjustment factor |
| `Close` | Yahoo `Adj Close`, used by research return and spread calculations |
| `RawOpen`, `RawHigh`, `RawLow`, `RawClose` | Yahoo unadjusted OHLC, retained for auditing and execution research |
| `Volume` | Yahoo daily share volume |
| `Dividends` | Cash dividend action amount reported by Yahoo; zero on other rows |
| `StockSplits` | Split ratio reported by Yahoo; zero on other rows |
| `CapitalGains` | Capital-gains distribution when Yahoo supplies it, mainly for funds |
| `Ticker` | Uppercase ticker symbol |

All price columns must be finite and strictly positive. Volume and action
columns must be finite and non-negative. Aligned data suffixes every non-date
field with its ticker, such as `Close_MSFT`, `Open_MSFT`, and `Volume_MSFT`.

The cache key is the **exact** `(ticker, start, end)` tuple, so different date
ranges produce different files. Cache schema `v5` is required. Older cache
files do not contain the complete adjusted and raw OHLCV contract and are not
reused. Cache files live under `correlation-api/data/raw/` and are gitignored.
Delete them anytime to force a fresh fetch.

Yahoo's adjusted prices reflect its current split and distribution history,
which Yahoo can revise. They are appropriate for historical research but are
not point-in-time execution prices. Raw prices and action columns improve
auditability but do not provide intraday quotes, publication timestamps, fees,
slippage, verified borrow availability, or survivorship-bias controls.

```
correlation-api/
├── app.py                    # Flask app + route handlers
├── analysis/
│   ├── data_loader.py        # yfinance fetch + CSV cache
│   ├── correlation.py        # Lagged Pearson correlation of log returns
│   ├── pair_model.py         # Cointegration and mean-reversion quality gate
│   ├── peer_basket.py        # Peer-basket weights, residual signal, diagnostics
│   ├── risk.py               # Correlation-breakdown warnings
│   ├── spread.py             # Spread series, rolling z-score, metrics
│   └── universes.py          # Editable Strategy Lab peer groups
├── data/raw/                 # CSV cache (gitignored)
└── requirements.txt
```

## Configuring the pair list

Keep the `PAIRS` lists in `app.py` and `../lib/correlationTypes.ts` synchronized. Each entry needs `ticker_a`, `ticker_b`, `name_a`, `name_b`, and `sector`.

## Troubleshooting

- **`Connection refused` from the site** → Flask isn't running, or it's on a port other than 5050. Check the rewrite in `../next.config.mjs`.
- **`yfinance` returns empty** → ticker symbol invalid, or Yahoo throttled the IP. Delete the cached CSV (if any) and retry; switch networks if it persists.
- **Stale data** → cache is keyed by date range. Delete files in `data/raw/` to refetch.
