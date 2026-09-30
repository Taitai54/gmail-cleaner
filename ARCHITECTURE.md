# Architecture

Gmail Cleaner and Gmail Label Manager live in one repository. They share OAuth files and the Gmail API. They do not share a process, a UI, or a port.

| Product | Entry | UI | Port |
| --- | --- | --- | --- |
| Gmail Cleaner | `main.py` | Vanilla JS SPA served by FastAPI | 8766 |
| Label Manager | `label_manager_ui.py` | Streamlit | 8504 |
| Label Manager CLI | `label_manager.py` | Terminal | none |

OAuth callback for both products uses port **8767**. Only one sign-in can run at a time.

## Gmail Cleaner

```
Browser (templates/index.html + static/js)
        |  POST start, GET poll
        v
FastAPI  app/api/actions.py  +  app/api/status.py
        |
        v
app/services/gmail/*     app/services/auth.py
        |                        |
        v                        v
   Gmail API              token_*.json + accounts.json
                          (in-memory AppState sits beside this)
```

Long work does not stay inside the HTTP request. A POST handler registers a FastAPI `BackgroundTasks` job and returns immediately. The job writes progress into `AppState` (`app/core/state.py`). The page polls a GET status route until `done` is true. That pattern fits this app because the job must see the same in-memory state as the status routes. FastAPI documents `BackgroundTasks` for that kind of in-process work, and recommends a separate queue only when the job should leave the process.

Nothing about a scan, delete, or export is written to disk. Restarting the server clears `AppState`. OAuth tokens and `accounts.json` are the only persisted account data. The browser also keeps the last unsubscribe and delete scans in `localStorage` for one hour.

### Request flow

1. `main.py` starts uvicorn on `0.0.0.0:8766` and opens a browser unless `WEB_AUTH=true`.
2. `app/main.py` mounts `/static`, serves `templates/index.html`, and includes the two API routers.
3. `static/js/main.js` creates `window.GmailCleaner` and loads each feature module.
4. Navigation is a view swap inside one page: `unsubscribe`, `delete`, `markread`, `search`. There is no router.

### Frontend modules

| File | View / job |
| --- | --- |
| `auth.js` | Sign-in, sign-out, auth progress |
| `accounts.js` | Header account menu |
| `filters.js` | Shared scan / delete / mark-read filter bar |
| `scanner.js` | Unsubscribe scan and bulk unsubscribe |
| `delete.js` | Sender scan, delete, and the action toolbar |
| `preview.js` | Sender preview modal. Calls `POST /api/preview-emails` |
| `labels.js` | Apply label, archive, mark important |
| `markread.js` | Unread count and mark-as-read |
| `export.js` | Search, export, and the Unsubscribe label action |
| `ui.js` | View switching, toasts, sidebar |

Search & Export does not use the global filter bar. It builds its own Gmail query from the search form.

### API

All routes are under `/api`.

**Start work (POST)**

| Route | Work |
| --- | --- |
| `/sign-in` | OAuth for `gmail` or `unidays` client |
| `/sign-out` | Drop the active account token |
| `/accounts`, `/accounts/add`, `/accounts/switch`, `/accounts/remove` | Multi-account registry |
| `/scan` | Find unsubscribe links |
| `/unsubscribe` | Visit one unsubscribe link |
| `/process-unsubscribe-label` | Process messages labeled Unsubscribe |
| `/delete-scan` | Group mail by sender |
| `/delete-emails`, `/delete-emails-bulk` | Trash messages |
| `/preview-emails` | Recent messages from one sender |
| `/download-emails` | CSV of message metadata |
| `/archive` | Remove INBOX |
| `/mark-important` | Add or remove IMPORTANT |
| `/mark-read` | Remove UNREAD |
| `/labels`, `DELETE /labels/{id}` | Create or delete a label |
| `/apply-label`, `/remove-label` | Change labels on mail from selected senders |
| `/search-threads` | Thread list for export |
| `/export-threads`, `/export-selected` | Download txt, markdown, or pdf |

**Poll (GET)**

`/status`, `/results`, `/auth-status`, `/auth-progress`, `/unread-count`, `/mark-read-status`, `/delete-scan-status`, `/delete-scan-results`, `/delete-bulk-status`, `/download-status`, `/download-csv`, `/labels`, `/label-operation-status`, `/archive-status`, `/important-status`.

### Accounts and tokens

`app/services/auth.py` stores one token per mailbox: `token_{sanitized_email}.json`. `accounts.json` lists those files and the active email. `get_gmail_service()` loads the active token, refreshes it when it is expired, or starts `InstalledAppFlow.run_local_server` on port 8767.

Client JSON comes from `credentials.json` or the `GOOGLE_CREDENTIALS` environment variable (`.env` or `global.env`). The sign-in screen can also select a second client for a work account.

Scopes are `gmail.readonly` and `gmail.modify`.

### Gmail service layer

Each file in `app/services/gmail/` does one operation. Shared helpers in `helpers.py` build Gmail search queries and read `List-Unsubscribe` headers. List and modify calls are batched, up to 100 messages per HTTP request.

Deletes trash mail. Gmail keeps trash for 30 days. Archive removes the INBOX label and leaves the message in All Mail.

### Configuration

`app/core/config.py` loads settings with pydantic-settings. Priority is environment variables, then `.env`, then `global.env`, then defaults.

| Setting | Default | Meaning |
| --- | --- | --- |
| `PORT` | 8766 | Web UI |
| `OAUTH_PORT` | 8767 | Google callback |
| `WEB_AUTH` | false | Print the OAuth URL instead of opening a browser |
| `OAUTH_HOST` | localhost | Host in the redirect URI |

`Gmail Cleaner.bat` forces `WEB_AUTH=false` so a Docker setting in the shell does not turn the desktop app into headless mode.

### State object

`AppState` holds the active account plus a status dict for each long job: scan, delete scan, bulk delete, download, mark read, label apply, archive, and mark important. Each status has `progress`, `message`, `done`, and `error`. Reset methods clear one job without touching the others.

## Label Manager

Label Manager does not import the FastAPI app. `label_manager_auth.py` reads the same `accounts.json` and token files, then `label_manager.py` and `label_manager_ui.py` call the Gmail labels API directly.

Gmail stores nesting in the label name (`Parent/Child`). Rename and move rewrite the selected label and every name that starts with `OldName/`. Delete of a parent is blocked until the caller opts into cascade. Messages are not deleted.

See [docs/LABEL_MANAGER.md](docs/LABEL_MANAGER.md).

## What is not shared

- Cleaner UI cannot rename or move the label tree. Its label endpoints apply labels to messages.
- Label Manager cannot scan, unsubscribe, export, or delete mail.
- In-memory Cleaner progress is invisible to Label Manager.
- Streamlit is loaded only for Label Manager (`uv run --with streamlit`), not for the Cleaner runtime.
