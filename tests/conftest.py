"""
Pytest Configuration and Fixtures
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """FastAPI test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_email_headers():
    """Sample email headers for testing."""
    return [
        {"name": "From", "value": "Newsletter <newsletter@example.com>"},
        {"name": "Subject", "value": "Test Email Subject"},
        {"name": "List-Unsubscribe", "value": "<https://example.com/unsubscribe>"},
    ]


@pytest.fixture
def sample_email_headers_one_click():
    """Sample email headers with one-click unsubscribe."""
    return [
        {"name": "From", "value": "Marketing <marketing@company.com>"},
        {"name": "Subject", "value": "Special Offer"},
        {"name": "List-Unsubscribe", "value": "<https://company.com/unsub?id=123>"},
        {"name": "List-Unsubscribe-Post", "value": "List-Unsubscribe=One-Click"},
    ]


@pytest.fixture(autouse=True)
def mock_gmail_auth(monkeypatch, request, tmp_path):
    """Mock auth artifacts for API tests to avoid local OAuth side effects."""
    # Keep auth service/unit tests realistic (each test mocks what it needs
    # individually) rather than blanket-mocking os.path.exists like below.
    #
    # But that per-test mocking has proven fragile: a test that mocks
    # Credentials/InstalledAppFlow but not _save_accounts_registry can still
    # fall through real, unmocked code in app/services/auth.py that reads and
    # writes accounts.json / token_*.json via *relative* paths — which,
    # without this chdir, resolve against the repo root and can silently
    # deregister or delete the developer's real signed-in Gmail accounts.
    # (This happened: test_auth_state_after_token_expiry wiped the real
    # accounts.json during a routine test run.) Sandbox the CWD so any such
    # gap lands in a throwaway directory instead of real repo state.
    if "tests/unit/services/auth/" in request.node.nodeid.replace("\\", "/"):
        monkeypatch.chdir(tmp_path)
        return

    # Set environment variable to disable web auth mode (prevents browser opening)
    monkeypatch.setenv("WEB_AUTH", "false")

    # Mock file existence checks for auth artifacts to return False (no credentials)
    # This prevents OAuth/token refresh flow from touching local machine state.
    original_exists = os.path.exists

    def mock_exists(path):
        path_str = str(path)
        if (
            "credentials.json" in path_str
            or "token.json" in path_str
            or "token_" in path_str
            or "accounts.json" in path_str
        ):
            return False
        return original_exists(path)

    monkeypatch.setattr("os.path.exists", mock_exists)
