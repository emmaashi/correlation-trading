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
| GET | `/api/spread` | `ticker_a`, `ticker_b`, `start`, `end`, `spread_type`, `window` | Descriptive spread series plus current pair-model eligibility and residual signal diagnostics |
| GET | `/api/signal` | `ticker_a`, `ticker_b`, `start`, `end`, `window` | Compact log-ratio z-score and Short, Long, or Hold direction for pair cards |
| GET | `/api/risk/breakdown` | `ticker_a`, `ticker_b`, optional `end`, optional `start` override | Return-correlation breakdown signal with its own lookback window, current 60d correlation, baseline, reason, and `broken_since` |
| GET | `/api/strategy/universes` | - | Versioned, editable peer-group presets and research caveats |
| POST | `/api/strategy/scan` | JSON peer group, `start`, and `end` | Ranked target signals, diagnostics, peer weights, and data warnings |
| POST | `/api/strategy/backtest` | JSON target, peers, dates, and optional strategy config | Current signal, walk-forward curves, metrics, trades, costs, holdout results, and 126/252/504-session sensitivity runs |

Dates are `YYYY-MM-DD`. `spread_type` is one of the values supported by `analysis/spread.py` (default `log_ratio`).

## Peer-basket Strategy Lab

For every target in a peer group, the scanner models adjusted daily log returns
against the remaining 3-7 stocks. The constrained ridge fit uses non-negative
peer weights that sum to one, caps each weight at 60%, and reports the fitted
beta separately as the basket hedge size. The accumulated return residual is
standardized with an AR(1)/OU equilibrium estimate when valid and an empirical
fallback when the model is weak.

Signals use fixed, predeclared rules: z-score at or below -2 is Long Target / Short
Peers, z-score at or above 2 is Short Target / Long Peers, and the interval
between is Hold. ADF results, half-life, fit, concentration, and data cautions
remain visible and advisory; they never hide an otherwise calculable signal.

The backtest refits every 21 sessions using only prior data. A close signal is
filled at the next adjusted open, exits inside +/-0.5, stops outside +/-4, and
times out after three estimated half-lives clamped to 5-60 sessions. Defaults
are $100,000 initial capital, 1.0x gross exposure, 5 bps per dollar traded, 3%
annualized short borrow, and a 1% share of 20-day median dollar volume. It
reports the full walk-forward history and final 30% holdout separately. The
126, 252, and 504-session formation windows are all shown rather than selecting
the best result.

Strategy endpoints require at least 504 overlapping sessions, reject stale or
invalid data with structured 400 responses, limit groups to eight stocks, and
limit backtests to ten years. These outputs are research evidence, not a profit
guarantee or a live execution system.

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
2. **`load_pair_data`** (`analysis/data_loader.py`) fetches each ticker via `get_stock_data`, then inner-joins on `Date`.
3. **`get_stock_data`** is the cache layer:
   - Looks for `data/raw/<TICKER>_<start>_to_<end>_<VERSION>_raw.csv` — if present and valid, reads it and returns immediately.
   - Otherwise calls `yfinance.download` with `auto_adjust=False` and `actions=True`. This preserves Yahoo's adjusted close, raw close, and available action data in one response.
   - Rejects downloads without `Adj Close`; research prices never silently fall back to raw close.
   - Validates the requested date range, row dates, prices, and action values before writing the CSV.
4. **Analysis modules** (`correlation.py`, `spread.py`) consume the merged DataFrame and produce the JSON the frontend renders.

### Market data contract

`get_stock_data` returns one row per trading date with the following columns:

| Column | Meaning |
|--------|---------|
| `Date` | Unique, ascending, timezone-naive trading date |
| `Open`, `High`, `Low`, `Close` | Adjusted OHLC, used for signals and next-open strategy simulation |
| `RawOpen`, `RawHigh`, `RawLow`, `RawClose` | Yahoo unadjusted OHLC, retained for auditing the adjustment factor |
| `Volume` | Reported daily share volume, used for the simulation's capacity limit |
| `Dividends` | Cash dividend action amount reported by Yahoo; zero on other rows |
| `StockSplits` | Split ratio reported by Yahoo; zero on other rows |
| `CapitalGains` | Capital-gains distribution when Yahoo supplies it, mainly for funds |
| `Ticker` | Uppercase ticker symbol |

Both price columns must be finite and strictly positive. Action columns must be finite and non-negative. Pair data suffixes every non-date field with its ticker, so consumers continue to use `Close_<TICKER>` while raw and action fields remain available as `RawClose_<TICKER>`, `Dividends_<TICKER>`, and so on.

The cache key is the **exact** `(ticker, start, end)` tuple, so different date ranges produce different files. Cache schema `v5` is required; older files do not contain the complete adjusted OHLCV contract and are not reused. Cache files live under `correlation-api/data/raw/` and are gitignored. Delete them anytime to force a fresh fetch.

Yahoo's adjusted close reflects its current split and distribution history, which Yahoo can revise. It is appropriate for historical research but is not a point-in-time execution price. `RawClose` and the action columns preserve inputs needed for a future daily execution model, but they do not provide intraday prices, publication timestamps, fees, slippage, or survivorship-bias controls.

```
correlation-api/
├── app.py                    # Flask app + route handlers
├── analysis/
│   ├── data_loader.py        # yfinance fetch + CSV cache
│   ├── correlation.py        # Lagged Pearson correlation of log returns
│   ├── pair_model.py         # Cointegration and mean-reversion quality gate
│   ├── peer_basket.py        # Constrained peer model, diagnostics, and scanner
│   ├── strategy_backtest.py  # Walk-forward execution and portfolio ledger
│   ├── universes.py          # Versioned editable peer presets
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
