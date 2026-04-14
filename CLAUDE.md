# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install dependencies (uses uv)
uv sync
uv sync --group dev  # includes test deps

# Run the app
uv run python main.py
# OR directly:
python main.py

# Run tests
uv run pytest
uv run pytest tests/test_specific.py::test_function  # single test
uv run pytest --cov=app                               # with coverage

# Linting (via pre-commit)
pre-commit run --all-files
```

The app starts on port **8766** and opens a browser automatically. OAuth callback uses port **8767**.

## Architecture

Single-page web app (vanilla JS frontend + FastAPI backend) that manages Gmail via OAuth2.

```
main.py                   → entry point, starts uvicorn on port 8766
app/main.py               → FastAPI app factory, mounts static/template files
app/api/
  actions.py              → POST endpoints (scan, delete, export, labels, auth)
  status.py               → GET endpoints (progress polling, results)
app/services/
  auth.py                 → OAuth2 flow, token management, multi-account
  gmail/                  → one module per operation (scan, delete, export, etc.)
  state.py                → in-memory operation state
app/core/
  config.py               → Settings loaded from .env / global.env
  state.py                → global AppState container
app/models/schemas.py     → Pydantic request/response models
templates/index.html      → single HTML shell for the SPA
static/js/                → one JS module per feature (no framework)
static/css/               → modular CSS
```

**Key pattern — async background tasks + polling:** Long-running operations (scan, delete, export) are started via POST and run as FastAPI `BackgroundTask`. The frontend polls GET status endpoints (e.g. `/api/status`, `/api/delete-bulk-status`) until `done: true`.

**State is in-memory:** `AppState` in `app/core/state.py` holds all operation progress and results. Nothing is persisted to disk except OAuth tokens.

## Authentication & Multi-Account

- OAuth2 desktop flow: backend starts an HTTP server on port 8767 to receive the Google callback
- Tokens saved as `token_{email_sanitized}.json` (e.g. `token_user_gmail_com.json`)
- `accounts.json` tracks registered accounts and the active account
- All token/credential files are gitignored — never commit them
- `GOOGLE_CREDENTIALS` env var (in `global.env`) embeds the OAuth client JSON for portability

## Configuration

Settings come from `app/core/config.py` via `pydantic-settings`. Priority order:
1. Environment variables
2. `.env` file
3. `global.env` file
4. Defaults

Key settings: `PORT=8766`, `OAUTH_PORT=8767`, `WEB_AUTH=false` (set true for Docker/headless).

## Gmail Service Layer

Each Gmail operation lives in its own module under `app/services/gmail/`. They all:
- Call `get_gmail_service()` from `auth.py` to get an authenticated API client
- Use batch requests (up to 100 per call) for performance
- Update `AppState` with progress/results as they run
- Are called from `actions.py` as background tasks

`helpers.py` contains shared utilities: `build_gmail_query()`, `get_unsubscribe_from_headers()`, batch helpers.

## Docker

```bash
docker compose up
```

In Docker mode, set `WEB_AUTH=true` — the app prints an OAuth URL instead of opening a browser. Tokens are persisted in `/app/data/`.
