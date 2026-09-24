# Correlation Trading

Wat Street research app for finding unusual moves between related stocks. It
supports two different kinds of analysis: a two-stock **Pair Explorer** and a
multi-stock **Strategy Lab**.

> **Current status:** The Pair Explorer interface is available on `main`. The
> Strategy Lab market-data and scanner APIs are also on `main`, but the
> walk-forward backtester and visible Strategy Lab pages are still in progress
> in PRs [#28](https://github.com/Wat-Street/correlation-trading/pull/28) and
> [#29](https://github.com/Wat-Street/correlation-trading/pull/29).

## Pair Selector, Pair Explorer, and Strategy Lab

The **Pair Selector** is the first screen of the Pair Explorer. It lets you pick
one of 15 prepared pairs or enter two custom stock symbols. It is not a separate
trading model.

| | Pair Explorer | Strategy Lab |
|---|---|---|
| Main question | Are these two stocks moving differently from normal? | Is one stock moving differently from a group of similar stocks? |
| Stocks compared | Exactly 2 | 1 target stock against 3-7 peers |
| Comparison | Direct price relationship between the pair | Weighted peer basket built by the model |
| Main signal | 60-day log-ratio z-score | 252-day peer-residual z-score |
| Output | Long, Short, or Hold for the pair | Long Target, Short Target, or Hold, plus peer weights |
| Availability | Complete interface on `main` | Scanner API on `main`; backtester and interface still in progress |

Example: Pair Explorer compares MSFT directly with GOOGL. Strategy Lab can
compare MSFT with a basket made from GOOGL, META, and AMZN, then measure the
part of MSFT's move that those peers do not explain.

## Features Available on `main`

### Pair Explorer

- 15 prepared stock pairs across technology, healthcare, consumer, industrial,
  financial, energy, telecom, and retail groups
- Custom pair entry with ticker validation and duplicate-pair protection
- Long, Short, or Hold labels on the pair cards
- Adjustable research dates with correctly aligned trading sessions
- Lagged Pearson correlation of daily log returns
- Normalized price, log-ratio spread, rolling mean, one- and two-standard-
  deviation bands, z-score, and spread-distribution charts
- A correlation-breakdown warning when a previously related pair weakens
- Advisory pair-model diagnostics: hedge ratio, cointegration, stationarity,
  mean-reversion half-life, observation count, and clear caution reasons
- Plain-language explanations beside charts, signals, and model values

### Strategy Lab foundation

- Adjusted daily Open, High, Low, Close, and Volume data, with raw prices and
  corporate actions retained for auditing
- One aligned data load for an entire peer group instead of repeated pair loads
- 12 editable peer-universe presets, including platforms, semiconductors,
  cloud software, pharma, banks, payments, energy, and telecom
- A sector scanner that accepts 4-8 stocks and evaluates every stock as the
  target against the remaining peers
- Nonnegative peer weights that sum to 100%, with no peer above 60%
- Hedge beta, residual z-score, Long/Short/Hold research direction, model-
  quality label, stationarity checks, half-life, fit, and concentration cautions
- Candidate ranking by the size of each stock's peer-relative move
- Structured validation errors for invalid tickers, dates, universes, or data

The scanner backend is usable through `GET /api/strategy/universes` and
`POST /api/strategy/scan`. The Strategy Lab screen and historical backtester
are not part of `main` yet.

### Data and reliability

- Split- and dividend-adjusted research prices so corporate actions do not look
  like trading signals
- Raw OHLC prices, adjusted OHLC prices, volume, dividends, and stock splits in
  the versioned v5 cache
- Validation for dates, duplicate sessions, prices, volume, requested coverage,
  and stale data
- Node.js 20.20.2, an audit-clean frontend lockfile, frontend builds, dependency
  audits, and backend analysis tests in CI

## Plain-English Terms

- **Correlation:** how similarly two return series move. It does not prove that
  one stock causes the other to move.
- **Spread:** a number representing the gap between two stocks or between a
  target stock and its peer basket.
- **Z-score:** how unusual the current spread is compared with its recent
  history. `+2` means about two standard deviations above its average; `-2`
  means about two below.
- **OHLCV:** Open, High, Low, Close, and Volume for each trading day.
- **Universe:** the list of stocks a strategy is allowed to compare.

The app is split into:

- Next.js frontend at the repo root
- Flask API in `correlation-api/`
- Shared frontend types in `lib/correlationTypes.ts` and `lib/strategyTypes.ts`

## Research Experiences

- **Pair Explorer** shows lagged return correlation, normalized performance,
  spread behavior, rolling z-scores, and directional pair signals.
- **Strategy Lab** scans editable peer groups, estimates a target stock's
  residual relative to a constrained peer basket, and reports Long, Short, or
  Hold research signals.
- **Strategy backtests** refit the model using past data only, execute on the
  next adjusted open, charge transaction and borrow costs, enforce a liquidity
  cap, and report both full-history and recent-holdout results.

The Strategy Lab is statistical-arbitrage research, not risk-free arbitrage or
investment advice. A signal can fail to mean-revert, and a positive historical
result does not guarantee future profit.

## Architecture

```text
Browser -> Next.js frontend -> /api/* rewrite -> Flask API -> yfinance
```

The frontend calls `/api/*`. `next.config.mjs` rewrites those requests to the Flask API URL configured by `CORRELATION_API_URL` or `CORRELATION_API_HOST`, falling back to `http://localhost:5050` for local development.

## Running Locally

Use Node.js 20.20.2 for the frontend. Version managers such as `nvm`, `fnm`,
and `asdf` will pick up the checked-in runtime version files automatically.

Run the frontend and API in two terminals.

### Terminal 1: Frontend

```bash
npm ci
npm run dev
```

The frontend runs at `http://localhost:3000`.

### Terminal 2: API

```bash
cd correlation-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

The API runs at `http://localhost:5050`. Health check:

```bash
curl http://localhost:5050/api/pairs
```

Run the automated checks with:

```bash
npm run lint
npm run build
cd correlation-api && python -m unittest discover -v
```

## Research Limitations

- Signals describe historical relationships; they do not guarantee that a
  spread will return to its average or that a trade will make money.
- Yahoo Finance is useful for prototypes but can revise historical data and
  does not provide execution-quality quotes or verified borrow availability.
- The Strategy Lab presets use today's peer lists, so historical results can
  contain survivorship bias.
- This project is for research and education, not investment advice.

## Deployment

The included `render.yaml` defines two Render services:

- `correlation-trading`: Next.js frontend
- `correlation-api`: Flask API

Render wires the frontend to the API with `CORRELATION_API_HOST`, using the API service's generated hostname.

If deploying the frontend separately from the API, set:

```text
CORRELATION_API_URL=<deployed Flask API URL>
```
