# Correlation Trading

Wat Street research application for studying relative-value relationships
between public stocks. It now includes two connected workflows:

- **Pair Explorer** for investigating one two-stock relationship in detail.
- **Strategy Lab (Beta)** for scanning groups of related stocks and
  walk-forward testing peer-basket strategies.

This is a research and education tool. It does not place trades or provide
investment advice.

## Features

### Pair Selector and Pair Explorer

The Pair Selector is the landing screen for Pair Explorer. It lets you:

- Browse 15 predefined pairs grouped by sector.
- See each predefined pair's current Long, Short, Hold, or Unavailable signal.
- Enter and validate any two custom Yahoo Finance ticker symbols.
- Reject pairs without enough overlapping data for a 60-session signal.

After selecting a pair, Pair Explorer provides:

- Lagged Pearson correlation of daily log returns.
- A correlation-breakdown warning with the current value, historical baseline,
  reason, and first detected date.
- Adjusted normalized-price and log-ratio spread charts.
- Rolling 60-session mean, standard deviation, and z-score.
- Long, Short, or Hold direction from the current log-ratio z-score.
- Spread and z-score distributions.
- Advisory pair-model diagnostics: hedge ratio, cointegration, residual
  stationarity, AR(1) behavior, half-life, and rejection reasons.

The pair-model checks add context but do not suppress an otherwise calculable
Pair Explorer signal. Pair Explorer is a current-snapshot diagnostic, not a
historical portfolio backtest.

### Strategy Lab (Beta)

Strategy Lab works with a group rather than a single pair. It lets you:

- Start from curated industry peer groups or edit a universe of 4-8 tickers.
- Model each stock against a basket made from the other 3-7 stocks.
- Rank candidates by residual z-score and show model quality and cautions.
- Inspect the peer weights and hedge beta behind each candidate.
- Open a dedicated candidate page with the current research signal.
- Preserve the selected group, universe, and dates in navigation links.

Each candidate page runs a walk-forward simulation that:

- Fits using historical data available at each signal date.
- Refits every 21 sessions and executes a close signal at the next adjusted
  open.
- Uses fixed entry, exit, stop, and maximum-holding rules.
- Includes transaction costs, short-borrow costs, and a recent-volume capacity
  limit.
- Reports an equity curve, target benchmark, drawdown, trade ledger, turnover,
  win rate, costs, and the final 30% holdout period.
- Displays 126-, 252-, and 504-session sensitivity results without selecting
  whichever window happened to perform best.

### Pair Selector vs. Strategy Lab

| | Pair Selector / Pair Explorer | Strategy Lab |
|---|---|---|
| Main question | How are these two stocks behaving relative to each other now? | Which stock in this related group is unusual versus its peers, and how would the rule have performed historically? |
| Input | Exactly two tickers | An editable universe of 4-8 tickers |
| Comparison | Stock A versus Stock B | Each target versus a weighted basket of the remaining peers |
| Signal | Fixed 60-session log-ratio z-score | Peer-residual z-score with fixed +/-2 entry bands |
| Model diagnostics | Pair hedge ratio, cointegration, ADF, AR(1), and half-life | Constrained peer weights, hedge beta, ADF, fit, concentration, and half-life |
| Historical simulation | No | Yes: walk-forward backtest with next-open execution and costs |
| Best use | Inspecting a known pair | Discovering and testing candidates across a related group |

The Pair Selector is therefore not a smaller version of Strategy Lab. It is
the entry screen for a two-stock diagnostic workflow; Strategy Lab is a
multi-stock scanner and backtester.

## Market Data and Research Safeguards

- Market data comes from Yahoo Finance through yfinance.
- Analysis uses adjusted OHLC prices. Raw OHLC, reported volume, dividends,
  splits, and available capital-gains actions are retained for auditing.
- Pair and universe data are inner-aligned so every calculation uses dates
  shared by all required tickers.
- Strategy signals use past rows only and execute on the following adjusted
  open to avoid same-close execution look-ahead.
- Transaction costs, annualized short-borrow costs, and a 1% share of recent
  median dollar volume are included by default.
- Structured validation rejects missing, stale, non-finite, duplicate, or
  insufficient market data.

Important limitations remain:

- Yahoo can revise historical adjusted prices when its corporate-action history
  changes, so adjusted prices are research-grade rather than immutable
  point-in-time execution records.
- Curated peer membership reflects today's editable universes and can introduce
  survivorship bias.
- The app does not model intraday liquidity, bid/ask spreads, taxes, broker
  margin rules, or live order execution.
- Statistical relationships and backtest results do not guarantee future
  mean reversion or profit.

## Architecture

~~~text
Browser -> Next.js frontend -> /api/* rewrite -> Flask API -> yfinance
~~~

- Next.js 16 frontend at the repository root.
- Flask analysis API in correlation-api/.
- Shared frontend contracts in lib/correlationTypes.ts and
  lib/strategyTypes.ts.
- Versioned market-data cache under correlation-api/data/raw/ (gitignored).

next.config.mjs rewrites browser requests under /api/* to the Flask API
configured by CORRELATION_API_URL or CORRELATION_API_HOST. Local development
defaults to http://localhost:5050.

The main API surfaces are:

| Workflow | Endpoints |
|---|---|
| Pair Explorer | /api/pairs, /api/validate, /api/correlation, /api/spread, /api/signal, /api/risk/breakdown |
| Strategy Lab | /api/strategy/universes, /api/strategy/scan, /api/strategy/backtest |

See [the API README](correlation-api/README.md) for endpoint contracts, model
rules, data fields, and cache behavior.

## Running Locally

Requirements:

- Node.js 20.20.2 (the checked-in version files configure common version
  managers).
- Python 3.12.

Run the API and frontend in separate terminals.

### Terminal 1: API

~~~bash
cd correlation-api
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
~~~

The API runs at [http://localhost:5050](http://localhost:5050). Check it with:

~~~bash
curl http://localhost:5050/api/pairs
~~~

### Terminal 2: Frontend

~~~bash
npm ci
npm run dev
~~~

Open [http://localhost:3000](http://localhost:3000). Use the top navigation to
switch between Pair Explorer and Strategy Lab.

## Validation

Frontend:

~~~bash
npm audit --audit-level=moderate
npm run lint
npm run build
~~~

Backend:

~~~bash
cd correlation-api
python -m unittest discover -v
~~~

The backend test suite mocks market-data downloads and does not require network
access.

## Deployment

render.yaml defines two Render services:

- correlation-trading: Next.js frontend.
- correlation-api: Flask API.

Render deploys from main after checks pass and connects the frontend through
CORRELATION_API_HOST. For a separately hosted API, set:

~~~text
CORRELATION_API_URL=<deployed Flask API URL>
~~~
