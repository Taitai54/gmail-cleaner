"""
Smoke Tests - Cross-Feature Regression Guard
---------------------------------------------
Three-step check that catches the regressions that keep burning sessions:
  1. Auth status endpoint returns a valid shape
  2. Date picker filters pass validation and build correct Gmail queries
  3. Natural-language search accepts bare keywords and structured queries

Run after every change:  py.test tests/test_smoke.py -x -q
"""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.schemas import FiltersModel, ScanRequest, SearchThreadsRequest
from app.services.gmail.helpers import build_gmail_query


@pytest.fixture
def client():
    """Isolated FastAPI test client (does not share conftest fixture)."""
    app = create_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. AUTH STATUS - endpoint returns a well-formed response
# ---------------------------------------------------------------------------


class TestAuthSmoke:
    """Auth-status endpoint must always respond, signed-in or not."""

    def test_auth_status_returns_200(self, client):
        """GET /api/auth-status must return 200 with logged_in field."""
        resp = client.get("/api/auth-status")
        assert resp.status_code == 200
        data = resp.json()
        assert "logged_in" in data

    def test_auth_status_shape_when_signed_out(self, client):
        """When no token exists, logged_in should be False and email None."""
        resp = client.get("/api/auth-status")
        data = resp.json()
        assert data["logged_in"] is False
        assert data.get("email") is None


# ---------------------------------------------------------------------------
# 2. DATE PICKER - filter validation and query building
# ---------------------------------------------------------------------------


class TestDatePickerSmoke:
    """Date range filters must validate and build correct Gmail queries."""

    def test_after_date_format_valid(self):
        """YYYY/MM/DD format must pass validation."""
        f = FiltersModel(after_date="2025/01/15")
        assert f.after_date == "2025/01/15"

    def test_before_date_format_valid(self):
        """YYYY/MM/DD format must pass validation."""
        f = FiltersModel(before_date="2025/06/30")
        assert f.before_date == "2025/06/30"

    def test_date_range_both(self):
        """Both after and before dates produce the right query."""
        f = FiltersModel(after_date="2025/01/01", before_date="2025/03/01")
        q = build_gmail_query(f)
        assert "after:2025/01/01" in q
        assert "before:2025/03/01" in q

    def test_date_range_supersedes_older_than(self):
        """When dates are set, older_than should NOT appear in query."""
        f = FiltersModel(
            after_date="2025/01/01",
            before_date="2025/03/01",
            older_than="30d",
        )
        q = build_gmail_query(f)
        assert "older_than" not in q
        assert "after:2025/01/01" in q

    def test_invalid_date_rejected(self):
        """Bad date format must raise ValidationError."""
        with pytest.raises(Exception):
            FiltersModel(after_date="Jan 15 2025")

    def test_scan_with_date_filters_accepted(self, client):
        """POST /api/scan with date range must return 200."""
        resp = client.post(
            "/api/scan",
            json={
                "limit": 100,
                "filters": {
                    "after_date": "2025/01/01",
                    "before_date": "2025/06/01",
                },
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "started"


# ---------------------------------------------------------------------------
# 3. NATURAL-LANGUAGE SEARCH - bare keywords must pass through
# ---------------------------------------------------------------------------


class TestNLSearchSmoke:
    """Natural-language (bare keyword) searches must not be rejected.

    The dc3a2a7d regression: date-picker fix accidentally broke NL search
    by requiring structured filters. These tests ensure bare-keyword queries
    always reach the Gmail API.
    """

    def test_bare_keyword_query_validates(self):
        """A bare keyword like 'stripe' must pass SearchThreadsRequest validation."""
        req = SearchThreadsRequest(query="stripe")
        assert req.query == "stripe"

    def test_multi_word_query_validates(self):
        """Multi-word NL queries must validate."""
        req = SearchThreadsRequest(query="order confirmation amazon")
        assert req.query == "order confirmation amazon"

    def test_empty_query_with_no_filters_rejected(self):
        """Empty query AND no filters must be rejected (model_validator)."""
        with pytest.raises(Exception):
            SearchThreadsRequest(query="", filters=None)

    def test_empty_query_with_filters_accepted(self):
        """Empty query but with filters should pass validation."""
        req = SearchThreadsRequest(
            query="",
            filters=FiltersModel(category="promotions"),
        )
        assert req.filters.category == "promotions"

    @patch("app.services.gmail.export.search_thread_previews")
    def test_search_endpoint_accepts_bare_keywords(self, mock_search, client):
        """POST /api/search-threads with bare keywords must return 200."""
        mock_search.return_value = {
            "success": True,
            "threads": [
                {
                    "id": "t1",
                    "sender": "info@stripe.com",
                    "subject": "Your receipt",
                    "date": "Mon, 1 Jan 2025 10:00:00 +0000",
                    "snippet": "Payment received",
                    "message_count": 1,
                }
            ],
            "error": None,
        }
        resp = client.post("/api/search-threads", json={"query": "stripe"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["threads"]) >= 1

    @patch("app.services.gmail.export.search_thread_previews")
    def test_search_endpoint_with_date_filter(self, mock_search, client):
        """POST /api/search-threads with query + date filter must work."""
        mock_search.return_value = {
            "success": True,
            "threads": [],
            "error": None,
        }
        resp = client.post(
            "/api/search-threads",
            json={
                "query": "newsletter",
                "filters": {
                    "after_date": "2025/01/01",
                    "before_date": "2025/06/01",
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @patch("app.services.gmail.export.search_thread_previews")
    def test_search_with_only_filters_no_query(self, mock_search, client):
        """POST /api/search-threads with only filters (no query) must work."""
        mock_search.return_value = {
            "success": True,
            "threads": [],
            "error": None,
        }
        resp = client.post(
            "/api/search-threads",
            json={
                "query": "",
                "filters": {"category": "promotions"},
            },
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 4. QUERY BUILDER - build_gmail_query must combine filters correctly
# ---------------------------------------------------------------------------


class TestQueryBuilderSmoke:
    """build_gmail_query must produce valid Gmail search strings."""

    def test_empty_filters_returns_empty(self):
        assert build_gmail_query(None) == ""
        assert build_gmail_query({}) == ""

    def test_older_than(self):
        q = build_gmail_query({"older_than": "30d"})
        assert q == "older_than:30d"

    def test_category_promotions(self):
        q = build_gmail_query({"category": "promotions"})
        assert q == "category:promotions"

    def test_category_sent_uses_in_sent(self):
        q = build_gmail_query({"category": "sent"})
        assert q == "in:sent"

    def test_sender_filter(self):
        q = build_gmail_query({"sender": "news@example.com"})
        assert q == "from:news@example.com"

    def test_combined_filters(self):
        q = build_gmail_query({
            "after_date": "2025/01/01",
            "before_date": "2025/06/01",
            "category": "promotions",
            "sender": "news@co.com",
        })
        assert "after:2025/01/01" in q
        assert "before:2025/06/01" in q
        assert "category:promotions" in q
        assert "from:news@co.com" in q

    def test_pydantic_model_as_input(self):
        """build_gmail_query must accept a Pydantic model directly."""
        f = FiltersModel(older_than="7d", larger_than="5M")
        q = build_gmail_query(f)
        assert "older_than:7d" in q
        assert "larger:5M" in q
