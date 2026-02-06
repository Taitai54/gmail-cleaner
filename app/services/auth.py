"""
Authentication Service
----------------------
Handles OAuth2 authentication with Gmail API.
Supports multiple signed-in accounts with active account switching.
"""

import json
import logging
import os
import platform
import re
import shutil
import threading
import time
from http.server import HTTPServer

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.core import settings, state
from app.services.auth_handlers import OAuthCallbackHandler

logger = logging.getLogger(__name__)

# Track auth in progress
_auth_in_progress = {"active": False}


# ---------------------------------------------------------------------------
# Token file helpers for multi-account
# ---------------------------------------------------------------------------


def _sanitize_email(email: str) -> str:
    """Convert email to a safe filename component."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", email)


def _token_file_for(email: str) -> str:
    """Return the token file path for a given email."""
    return f"token_{_sanitize_email(email)}.json"


def _is_file_empty(file_path: str) -> bool:
    """Check if a file exists and is empty."""
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "r") as f:
            return not f.read().strip()
    except OSError:
        return False


def _load_accounts_registry() -> tuple[list[dict], str | None]:
    """Load accounts and active email from accounts.json.

    Returns:
        (accounts_list, active_email)  where accounts_list is [{"email": str, "token_file": str}, ...]
    """
    registry_path = "accounts.json"
    if not os.path.exists(registry_path) or _is_file_empty(registry_path):
        return [], None
    try:
        with open(registry_path, "r") as f:
            data = json.load(f)
        accounts = [
            a for a in data.get("accounts", [])
            if a.get("token_file") and os.path.exists(a["token_file"]) and not _is_file_empty(a["token_file"])
        ]
        return accounts, data.get("active")
    except (json.JSONDecodeError, OSError):
        return [], None


def _save_accounts_registry(accounts: list[dict], active_email: str | None) -> None:
    """Save accounts registry to accounts.json."""
    with open("accounts.json", "w") as f:
        json.dump({"accounts": accounts, "active": active_email}, f, indent=2)


def _sync_state() -> None:
    """Sync state.accounts / state.active_account from registry, update current_user."""
    accounts, active = _load_accounts_registry()
    state.accounts = accounts
    emails = [a["email"] for a in accounts]

    if active and active in emails:
        state.active_account = active
    elif emails:
        state.active_account = emails[0]
    else:
        state.active_account = None

    state.current_user = {
        "email": state.active_account,
        "logged_in": state.active_account is not None,
    }


# ---------------------------------------------------------------------------
# Public multi-account API
# ---------------------------------------------------------------------------


def get_accounts() -> list[dict]:
    """Get list of signed-in accounts with active flag."""
    _sync_state()
    return [
        {"email": a["email"], "active": a["email"] == state.active_account}
        for a in state.accounts
    ]


def switch_account(email: str) -> dict:
    """Switch active account to the given email."""
    _sync_state()
    if not any(a["email"] == email for a in state.accounts):
        return {"success": False, "error": f"Account {email} not found"}
    _save_accounts_registry(state.accounts, email)
    _sync_state()
    return {"success": True, "active": email}


def remove_account(email: str) -> dict:
    """Remove a signed-in account (deletes its token file)."""
    _sync_state()
    acct = next((a for a in state.accounts if a["email"] == email), None)
    if not acct:
        return {"success": False, "error": f"Account {email} not found"}

    # Delete token file
    tf = acct["token_file"]
    if os.path.exists(tf):
        try:
            os.remove(tf)
        except OSError:
            pass

    remaining = [a for a in state.accounts if a["email"] != email]
    new_active = remaining[0]["email"] if remaining else None
    _save_accounts_registry(remaining, new_active)
    _sync_state()

    return {"success": True, "active": state.active_account}


# ---------------------------------------------------------------------------
# Credentials & refresh helpers
# ---------------------------------------------------------------------------


def is_web_auth_mode() -> bool:
    """Check if we should use web-based auth (Docker/headless)."""
    return settings.web_auth


def needs_auth_setup() -> bool:
    """Check if at least one account is signed in."""
    _sync_state()
    return len(state.accounts) == 0


def get_web_auth_status() -> dict:
    """Get current web auth status."""
    return {
        "needs_setup": needs_auth_setup(),
        "web_auth_mode": is_web_auth_mode(),
        "has_credentials": os.path.exists(settings.credentials_file),
        "pending_auth_url": state.pending_auth_url.get("url"),
    }


def _try_refresh_creds(creds: Credentials, token_file: str) -> Credentials | None:
    """Attempt to refresh expired credentials and save to token_file."""
    try:
        creds.refresh(Request())
        try:
            with open(token_file, "w") as token:
                token.write(creds.to_json())
        except OSError:
            logger.exception("Failed to save refreshed token")
        return creds
    except RefreshError as e:
        logger.warning(f"Token refresh failed: {e}")
        try:
            os.remove(token_file)
        except OSError:
            pass
        return None


def _get_credentials_path() -> str | None:
    """Get valid credentials file path (from file or env var)."""
    if os.path.exists(settings.credentials_file):
        if _is_file_empty(settings.credentials_file):
            logger.error("Credentials file is empty.")
            return None
        try:
            with open(settings.credentials_file, "r") as f:
                json.loads(f.read().strip())
            return settings.credentials_file
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            logger.error(f"Credentials file issue: {e}")
            return None

    env_creds = os.environ.get("GOOGLE_CREDENTIALS")
    if env_creds:
        try:
            json.loads(env_creds)
            with open(settings.credentials_file, "w") as f:
                f.write(env_creds)
            return settings.credentials_file
        except (json.JSONDecodeError, TypeError, OSError) as e:
            logger.error(f"GOOGLE_CREDENTIALS env var issue: {e}")
            return None

    return None


# ---------------------------------------------------------------------------
# Core: get_gmail_service
# ---------------------------------------------------------------------------


def get_gmail_service():
    """Get authenticated Gmail API service for the active account.

    Returns:
        tuple: (service, error_message)
    """
    _sync_state()

    # Find active account's token file
    creds = None
    token_file = settings.token_file  # fallback

    if state.active_account:
        acct = next((a for a in state.accounts if a["email"] == state.active_account), None)
        if acct:
            token_file = acct["token_file"]

    if os.path.exists(token_file) and not _is_file_empty(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, settings.scopes)
        except (ValueError, OSError) as e:
            logger.warning(f"Failed to load credentials from {token_file}: {e}")
            try:
                os.remove(token_file)
            except OSError:
                pass
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds = _try_refresh_creds(creds, token_file)

        if not creds or not creds.valid:
            # Trigger OAuth for a new account
            if _auth_in_progress.get("active", False):
                return (None, "Sign-in already in progress. Please complete authorization in your browser.")

            creds_path = _get_credentials_path()
            if not creds_path:
                if os.path.exists(settings.credentials_file) and _is_file_empty(settings.credentials_file):
                    return (None, "credentials.json file is empty!")
                return (None, "credentials.json not found or contains invalid JSON!")

            _auth_in_progress["active"] = True

            def run_oauth() -> None:
                try:
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(creds_path, settings.scopes)
                    except (ValueError, json.JSONDecodeError, OSError, FileNotFoundError) as e:
                        logger.error(f"Failed to load credentials: {e}")
                        print(f"ERROR: credentials.json issue: {e}")
                        return

                    bind_address = "0.0.0.0" if is_web_auth_mode() else "localhost"  # nosec B104
                    redirect_port = (
                        settings.oauth_external_port
                        if isinstance(settings.oauth_external_port, int)
                        else settings.oauth_port
                    )

                    if is_web_auth_mode():
                        open_browser = False
                    elif platform.system() in ("Windows", "Darwin"):
                        open_browser = True
                    else:
                        open_browser = bool(shutil.which("xdg-open") or os.environ.get("DISPLAY"))

                    new_creds = None

                    if redirect_port != settings.oauth_port:
                        if not settings.oauth_host or not settings.oauth_host.strip():
                            raise ValueError("oauth_host cannot be empty with custom external port.")

                        redirect_uri = f"http://{settings.oauth_host}:{redirect_port}/"
                        flow.redirect_uri = redirect_uri

                        authorization_url, oauth_state_val = flow.authorization_url(
                            access_type="offline", prompt="consent"
                        )
                        if not authorization_url:
                            raise ValueError("Failed to generate OAuth authorization URL.")

                        with state.oauth_state_lock:
                            state.oauth_state["state"] = oauth_state_val
                        if is_web_auth_mode():
                            state.pending_auth_url["url"] = authorization_url

                        callback_event = threading.Event()
                        callback_lock = threading.Lock()
                        callback_data: dict = {"code": None, "error": None}

                        def handler_factory(*args, **kwargs):
                            return OAuthCallbackHandler(
                                callback_event, callback_lock, callback_data, *args, **kwargs
                            )

                        server = None
                        try:
                            try:
                                server = HTTPServer((bind_address, settings.oauth_port), handler_factory)
                            except OSError as e:
                                if "address already in use" in str(e).lower() or (hasattr(e, "errno") and e.errno in (98, 10048)):
                                    raise OSError(f"Port {settings.oauth_port} is already in use.") from e
                                raise

                            print(f"Please visit this URL to authorize: {authorization_url}")
                            if open_browser:
                                try:
                                    import webbrowser
                                    webbrowser.open(authorization_url)
                                except Exception as e:
                                    logger.warning(f"Failed to open browser: {e}")

                            server.timeout = 1.0
                            start_time = time.time()
                            while not callback_event.is_set():
                                if time.time() - start_time > 300:
                                    raise TimeoutError("OAuth authorization timed out after 5 minutes.")
                                try:
                                    server.handle_request()
                                except Exception as e:
                                    if "address already in use" in str(e).lower():
                                        raise
                                callback_event.wait(timeout=0.1)

                            with callback_lock:
                                auth_code = callback_data["code"]
                                error_message = callback_data["error"]

                            if error_message:
                                raise ValueError(f"OAuth error: {error_message}")
                            if not auth_code:
                                raise ValueError("No authorization code received")

                            flow.fetch_token(code=auth_code)
                            new_creds = flow.credentials
                        finally:
                            if server is not None:
                                try:
                                    server.server_close()
                                except Exception:
                                    pass
                    else:
                        new_creds = flow.run_local_server(
                            port=settings.oauth_port,
                            bind_addr=bind_address,
                            host=settings.oauth_host,
                            open_browser=open_browser,
                            prompt="consent",
                        )

                    if new_creds is None:
                        raise ValueError("OAuth flow completed but no credentials were obtained")

                    # Get email from profile
                    try:
                        tmp_service = build("gmail", "v1", credentials=new_creds)
                        profile = tmp_service.users().getProfile(userId="me").execute()
                        new_email = profile.get("emailAddress", "unknown")
                    except Exception as e:
                        logger.error(f"Failed to get profile: {e}")
                        new_email = "unknown"

                    # Save to per-account token file
                    new_token_file = _token_file_for(new_email)
                    try:
                        with open(new_token_file, "w") as token:
                            token.write(new_creds.to_json())
                        print(f"OAuth complete! Signed in as {new_email}")
                    except OSError as e:
                        logger.error(f"Failed to save token: {e}")
                        raise

                    # Update registry — new account becomes active
                    accounts, _ = _load_accounts_registry()
                    if not any(a["email"] == new_email for a in accounts):
                        accounts.append({"email": new_email, "token_file": new_token_file})
                    else:
                        for a in accounts:
                            if a["email"] == new_email:
                                a["token_file"] = new_token_file
                    _save_accounts_registry(accounts, new_email)
                    _sync_state()

                except Exception as e:
                    logger.error(f"OAuth error: {e}", exc_info=True)
                    print(f"OAuth error: {e}")
                finally:
                    _auth_in_progress["active"] = False
                    state.pending_auth_url["url"] = None
                    with state.oauth_state_lock:
                        state.oauth_state["state"] = None

            oauth_thread = threading.Thread(target=run_oauth, daemon=True)
            oauth_thread.start()
            return (None, "Sign-in started. Please complete authorization in your browser.")

    # Build Gmail service
    try:
        service = build("gmail", "v1", credentials=creds)
    except Exception as e:
        logger.error(f"Failed to build Gmail service: {e}")
        return (None, f"Failed to connect to Gmail API: {str(e)}.")

    # Ensure current_user is set
    if state.active_account:
        state.current_user = {"email": state.active_account, "logged_in": True}
    else:
        try:
            profile = service.users().getProfile(userId="me").execute()
            state.current_user["email"] = profile.get("emailAddress", "Unknown")
            state.current_user["logged_in"] = True
        except Exception:
            state.current_user["email"] = "Unknown"
            state.current_user["logged_in"] = True

    return service, None


# ---------------------------------------------------------------------------
# Sign out / check login
# ---------------------------------------------------------------------------


def sign_out() -> dict:
    """Sign out the active account. If no accounts remain, fully signed out."""
    _sync_state()
    if state.active_account:
        result = remove_account(state.active_account)
        if not state.accounts:
            state.reset_scan()
            state.reset_delete_scan()
            state.reset_mark_read()
        return result

    # Legacy: remove old token.json
    if os.path.exists(settings.token_file):
        os.remove(settings.token_file)
    state.current_user = {"email": None, "logged_in": False}
    state.reset_scan()
    state.reset_delete_scan()
    state.reset_mark_read()
    return {"success": True, "message": "Signed out successfully", "results_cleared": True}


def check_login_status() -> dict:
    """Check if user is logged in and get their email."""
    _sync_state()

    if state.active_account:
        acct = next((a for a in state.accounts if a["email"] == state.active_account), None)
        if acct:
            tf = acct["token_file"]
            if os.path.exists(tf) and not _is_file_empty(tf):
                try:
                    creds = Credentials.from_authorized_user_file(tf, settings.scopes)
                    if creds and creds.valid:
                        return {"email": state.active_account, "logged_in": True}
                    elif creds and creds.expired and creds.refresh_token:
                        if _try_refresh_creds(creds, tf):
                            return {"email": state.active_account, "logged_in": True}
                except (ValueError, OSError) as e:
                    logger.warning(f"Credentials issue for {state.active_account}: {e}")
                    try:
                        os.remove(tf)
                    except OSError:
                        pass

        # Active account token is bad — remove and try next
        remaining = [a for a in state.accounts if a["email"] != state.active_account]
        new_active = remaining[0]["email"] if remaining else None
        _save_accounts_registry(remaining, new_active)
        _sync_state()
        if state.active_account:
            return check_login_status()

    # Legacy migration: check old token.json
    if os.path.exists(settings.token_file) and not _is_file_empty(settings.token_file):
        try:
            creds = Credentials.from_authorized_user_file(settings.token_file, settings.scopes)
            if creds and (creds.valid or (creds.expired and creds.refresh_token)):
                if creds.expired:
                    creds = _try_refresh_creds(creds, settings.token_file)
                if creds and creds.valid:
                    svc = build("gmail", "v1", credentials=creds)
                    profile = svc.users().getProfile(userId="me").execute()
                    email = profile.get("emailAddress", "Unknown")
                    # Migrate to multi-account
                    new_tf = _token_file_for(email)
                    os.rename(settings.token_file, new_tf)
                    _save_accounts_registry([{"email": email, "token_file": new_tf}], email)
                    _sync_state()
                    return {"email": email, "logged_in": True}
        except Exception as e:
            logger.error(f"Legacy token migration error: {e}")

    state.current_user = {"email": None, "logged_in": False}
    return state.current_user.copy()
