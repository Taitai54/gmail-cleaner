"""Shared Gmail auth for the label manager CLI and Streamlit UI.

Uses the same local OAuth files as Gmail Cleaner when they exist, so the two
products can share an account without a hardcoded token path.
"""

import json
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]
ROOT = Path(__file__).parent
REDIRECT_URI = "http://127.0.0.1:8767/"


def resolve_credentials_file() -> Path:
    """Return the OAuth client file, preferring the label-manager client."""
    for name in ("credentials_gmail.json", "credentials.json"):
        path = ROOT / name
        if path.exists() and path.stat().st_size > 0:
            return path
    raise FileNotFoundError(
        "No OAuth client file found. Place credentials_gmail.json or "
        "credentials.json in the project folder, then launch again."
    )


def resolve_token_file() -> Path | None:
    """Pick the active Cleaner token, or the only token file on disk.

    Returns None when a new sign-in is required. Raises if several tokens
    exist and none is marked active in accounts.json.
    """
    accounts_path = ROOT / "accounts.json"
    if accounts_path.exists() and accounts_path.stat().st_size > 0:
        try:
            data = json.loads(accounts_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            data = {}
        accounts = data.get("accounts") or []
        active = data.get("active")
        ordered = sorted(
            accounts,
            key=lambda account: account.get("email") != active,
        )
        for account in ordered:
            token_name = account.get("token_file")
            if not token_name:
                continue
            token_path = Path(token_name)
            if not token_path.is_absolute():
                token_path = ROOT / token_path
            if token_path.exists() and token_path.stat().st_size > 0:
                return token_path

    tokens = sorted(
        path
        for path in ROOT.glob("token_*.json")
        if path.is_file() and path.stat().st_size > 0
    )
    legacy = ROOT / "token.json"
    if legacy.exists() and legacy.stat().st_size > 0:
        tokens.append(legacy)
    if len(tokens) == 1:
        return tokens[0]
    if len(tokens) > 1:
        names = ", ".join(path.name for path in tokens)
        raise RuntimeError(
            "More than one Gmail token is saved and no active account is set. "
            f"Sign in with Gmail Cleaner first, or remove the extra files ({names})."
        )
    return None


def _sanitize_email(email: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", email)


def _load_client_config(creds_file: Path) -> dict:
    raw = json.loads(creds_file.read_text(encoding="utf-8-sig"))
    section = dict(raw.get("web") or raw.get("installed") or {})
    if not section:
        raise ValueError(f"{creds_file.name} is not a Google OAuth client JSON file.")
    wrapper_key = "web" if "web" in raw else "installed"
    uris = list(section.get("redirect_uris") or [])
    if REDIRECT_URI not in uris:
        uris.append(REDIRECT_URI)
    section["redirect_uris"] = uris
    return {wrapper_key: section}


def _run_oauth(creds_file: Path) -> Credentials:
    flow = InstalledAppFlow.from_client_config(_load_client_config(creds_file), SCOPES)
    flow.redirect_uri = REDIRECT_URI
    return flow.run_local_server(port=8767)


def _register_account(email: str, token_file: Path) -> None:
    path = ROOT / "accounts.json"
    data: dict = {"accounts": [], "active": email}
    if path.exists() and path.stat().st_size > 0:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            data = {"accounts": [], "active": email}
    accounts = list(data.get("accounts") or [])
    updated = False
    for account in accounts:
        if account.get("email") == email:
            account["token_file"] = token_file.name
            updated = True
    if not updated:
        accounts.append({"email": email, "token_file": token_file.name})
    data["accounts"] = accounts
    if not data.get("active"):
        data["active"] = email
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _save_new_token(creds: Credentials) -> Path:
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    email = profile.get("emailAddress") or "account"
    token_file = ROOT / f"token_{_sanitize_email(email)}.json"
    token_file.write_text(creds.to_json(), encoding="utf-8")
    if email != "account":
        _register_account(email, token_file)
    return token_file


def get_service():
    """Return an authenticated Gmail API client."""
    creds_file = resolve_credentials_file()
    token_file = resolve_token_file()
    creds = None
    if token_file is not None:
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token and token_file is not None:
            creds.refresh(Request())
            token_file.write_text(creds.to_json(), encoding="utf-8")
        else:
            creds = _run_oauth(creds_file)
            _save_new_token(creds)
    return build("gmail", "v1", credentials=creds)
