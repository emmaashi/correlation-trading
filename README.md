# Correlation Trading

Standalone Wat Street project for researching relative-value signals between
stocks. Pair Explorer studies two-stock relationships, while Strategy Lab ranks
stocks against curated peer baskets and tests the resulting rules with a
walk-forward simulation.

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
npm install
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

## Deployment

The included `render.yaml` defines two Render services:

- `correlation-trading`: Next.js frontend
- `correlation-api`: Flask API

Render wires the frontend to the API with `CORRELATION_API_HOST`, using the API service's generated hostname.

If deploying the frontend separately from the API, set:

```text
CORRELATION_API_URL=<deployed Flask API URL>
```
