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

The frontend calls `/api/*`. `next.config.mjs` rewrites those requests to the Flask API URL configured by `CORRELATION_API_URL` or `CORRELATION_API_HOST`, falling back to `http://localhost:5050` for local development.

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

## Deployment

The included `render.yaml` defines two Render services:

- `correlation-trading`: Next.js frontend
- `correlation-api`: Flask API

Render wires the frontend to the API with `CORRELATION_API_HOST`, using the API service's generated hostname.

If deploying the frontend separately from the API, set:

```text
CORRELATION_API_URL=<deployed Flask API URL>
```
