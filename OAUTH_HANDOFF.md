# OAuth Debug Handoff

Date: 2026-05-07  
Project: `gmail-cleaner`

## Goal

Fix OAuth flow where clicking **Sign in** / **Add account** sometimes stalls and does not complete account linking.

## Current Observations

- App is using work OAuth client from `global.env`:
  - `306721041110-hq0eo4g3ah7df6smi56b73rroji7a7ic.apps.googleusercontent.com`
- Runtime check showed backend can start OAuth and listen on callback port:
  - `127.0.0.1:8767` in `LISTENING` state after `POST /api/sign-in`
- User still reports stall in browser/OAuth completion path.

## Changes Applied

### 1) Add-account path now forces fresh OAuth + account picker

File: `static/js/accounts.js`
- `GmailCleaner.Accounts.addAccount()` now calls:
  - `POST /api/accounts/add`
- Added error handling on non-200 response.

File: `app/api/actions.py`
- `/api/accounts/add` now runs:
  - `background_tasks.add_task(get_gmail_service, True, "select_account")`

### 2) Auth service supports explicit OAuth prompt control

File: `app/services/auth.py`
- Updated signature:
  - `get_gmail_service(force_oauth: bool = False, oauth_prompt: str | None = None)`
- If `force_oauth` is true, bypasses active creds and starts OAuth.
- Passes `oauth_prompt` through both OAuth paths:
  - `flow.authorization_url(...)`
  - `flow.run_local_server(...)`

### 3) Main sign-in path now also forces account chooser

File: `app/api/actions.py`
- `/api/sign-in` now runs:
  - `background_tasks.add_task(get_gmail_service, False, "select_account")`

## Validation Done

- Test suite passed after changes:
  - `uv run pytest -q` -> `134 passed`
- Focused tests passed:
  - `uv run pytest -q tests/unit/api/test_api_actions.py tests/unit/services/auth/test_sign_in_api.py` -> `38 passed`
- Lint check on edited files: no issues.

## Likely Remaining Root Cause

Not a static config mismatch. Most likely runtime flow robustness issue:

- Repeated sign-in clicks causing overlapping OAuth attempts
- OAuth thread state not surfaced to UI
- Callback wait state not visible to user, appears as "stuck"
- Potential stale browser/session interaction despite `select_account`

## Next Recommended Implementation

1. Add explicit auth state machine in backend:
   - `idle`, `starting`, `waiting_for_callback`, `token_received`, `completed`, `failed`, `timeout`
2. Expose auth-progress endpoint:
   - e.g. `GET /api/auth-progress`
3. In frontend:
   - disable sign-in/add-account buttons while in progress
   - show progress text and terminal failure reason
4. Add timeout reset and retry mechanism for hung OAuth attempts.
5. Add concise structured logging for OAuth transitions.

## Quick Runtime Checks

Use these commands from repo root:

```powershell
python -c "import requests; print(requests.get('http://127.0.0.1:8766/api/web-auth-status',timeout=2).text); print(requests.get('http://127.0.0.1:8766/api/auth-status',timeout=2).text)"
```

```powershell
python -c "import requests; print(requests.post('http://127.0.0.1:8766/api/sign-in',timeout=5).text)"
netstat -ano | findstr 8767
```

## Notes

- OAuth consent screen must include intended users under **Test users** while app is in testing mode.
- Project must match current client ID above when editing consent/test-user settings.
