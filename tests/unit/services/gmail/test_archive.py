"""
Tests for Gmail Archive Operations
-----------------------------------
Tests archiving by sender, by filter, and by both combined.
"""

from unittest.mock import MagicMock, patch

from app.core import state
from app.services.gmail.archive import archive_emails_background


def _mock_service(message_ids):
    service = MagicMock()
    service.users().messages().list().execute.return_value = {
        "messages": [{"id": mid} for mid in message_ids]
    }
    return service


class TestArchiveEmailsBackground:
    def test_requires_senders_or_filters(self):
        archive_emails_background(senders=None, filters=None)
        assert state.archive_status["done"] is True
        assert "No senders or filters" in state.archive_status["error"]

    @patch("app.services.gmail.archive.get_gmail_service")
    def test_archive_by_senders_only(self, mock_get_service):
        service = _mock_service(["m1", "m2"])
        mock_get_service.return_value = (service, None)

        archive_emails_background(senders=["news@example.com"])

        assert state.archive_status["done"] is True
        assert state.archive_status["archived_count"] == 2
        # query should not include filter terms
        list_call = service.users().messages().list
        _, kwargs = list_call.call_args_list[-1]
        assert kwargs["q"] == "from:news@example.com in:inbox"

    @patch("app.services.gmail.archive.get_gmail_service")
    def test_archive_by_filters_only(self, mock_get_service):
        service = _mock_service(["m1"])
        mock_get_service.return_value = (service, None)

        archive_emails_background(filters={"category": "promotions", "older_than": "90d"})

        assert state.archive_status["done"] is True
        assert state.archive_status["archived_count"] == 1
        list_call = service.users().messages().list
        _, kwargs = list_call.call_args_list[-1]
        assert kwargs["q"] == "in:inbox older_than:90d category:promotions"

    @patch("app.services.gmail.archive.get_gmail_service")
    def test_archive_by_senders_narrowed_by_filters(self, mock_get_service):
        service = _mock_service(["m1"])
        mock_get_service.return_value = (service, None)

        archive_emails_background(
            senders=["news@example.com"], filters={"older_than": "30d"}
        )

        list_call = service.users().messages().list
        _, kwargs = list_call.call_args_list[-1]
        assert kwargs["q"] == "from:news@example.com in:inbox older_than:30d"

    @patch("app.services.gmail.archive.get_gmail_service")
    def test_archive_by_thread_ids(self, mock_get_service):
        service = MagicMock()
        mock_get_service.return_value = (service, None)

        archive_emails_background(thread_ids=["thread_1", "thread_2"], add_label_id="Label_Archived")

        assert state.archive_status["done"] is True
        assert state.archive_status["archived_count"] == 2
        assert service.users().threads().modify.call_count == 2

    @patch("app.services.gmail.archive.get_gmail_service")
    def test_archive_by_search_query(self, mock_get_service):
        service = _mock_service(["m1", "m2", "m3"])
        mock_get_service.return_value = (service, None)

        archive_emails_background(query="subject:invoice larger:5M")

        assert state.archive_status["done"] is True
        assert state.archive_status["archived_count"] == 3
        list_call = service.users().messages().list
        _, kwargs = list_call.call_args_list[-1]
        assert "subject:invoice larger:5M" in kwargs["q"]
