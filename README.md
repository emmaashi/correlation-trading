# Correlation Trading

Standalone Wat Street project for analyzing lagged correlations and statistical trading signals between stock pairs.

The app is split into:

- Next.js frontend at the repo root
- Flask API in `correlation-api/`
- Shared frontend types in `lib/correlationTypes.ts`

## Architecture

```text
Browser -> Next.js frontend -> /api/* rewrite -> Flask API -> yfinance
```

The frontend calls `/api/*`. `next.config.mjs` rewrites those requests to the Flask API URL configured by `CORRELATION_API_URL`, falling back to `http://localhost:5050` for local development.

## Running Locally

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
