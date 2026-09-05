"""
Tests for Gmail Label Management Operations
--------------------------------------------
Tests for create/delete/rename/move label functions, including "/"-nested cascade behavior.
"""

from unittest.mock import MagicMock, patch

from app.services.gmail.labels import delete_label, rename_label, move_label


def _label(label_id, name):
    return {"id": label_id, "name": name, "type": "user"}


def _mock_service(user_labels):
    """Build a mock Gmail API service whose labels().list() returns the given labels."""
    service = MagicMock()
    service.users().labels().list().execute.return_value = {
        "labels": user_labels + [{"id": "INBOX", "name": "INBOX", "type": "system"}]
    }
    return service


class TestDeleteLabelCascade:
    """Tests for delete_label's cascade-to-children behavior."""

    @patch("app.services.gmail.labels.get_gmail_service")
    def test_delete_label_without_children(self, mock_get_service):
        """Deleting a label with no children should just delete it."""
        service = _mock_service([_label("L1", "Work")])
        mock_get_service.return_value = (service, None)

        result = delete_label("L1")

        assert result["success"] is True
        service.users().labels().delete.assert_called_with(userId="me", id="L1")

    @patch("app.services.gmail.labels.get_gmail_service")
    def test_delete_label_with_children_blocked_without_cascade(self, mock_get_service):
        """Deleting a label with children should be refused unless cascade=True."""
        service = _mock_service(
            [_label("L1", "Work"), _label("L2", "Work/Projects")]
        )
        mock_get_service.return_value = (service, None)

        result = delete_label("L1")

        assert result["success"] is False
        assert result["children"] == ["Work/Projects"]
        service.users().labels().delete.assert_not_called()

    @patch("app.services.gmail.labels.get_gmail_service")
    def test_delete_label_with_cascade_deletes_children_first(self, mock_get_service):
        """cascade=True should delete children, then the parent."""
        service = _mock_service(
            [_label("L1", "Work"), _label("L2", "Work/Projects")]
        )
        mock_get_service.return_value = (service, None)

        result = delete_label("L1", cascade=True)

        assert result["success"] is True
        calls = [c.kwargs["id"] for c in service.users().labels().delete.call_args_list]
        assert calls == ["L2", "L1"]


class TestRenameLabel:
    """Tests for rename_label, including cascade to "/"-nested children."""

    @patch("app.services.gmail.labels.get_gmail_service")
    def test_rename_simple_label(self, mock_get_service):
        service = _mock_service([_label("L1", "Newsletters")])
        service.users().labels().update().execute.return_value = {
            "id": "L1", "name": "Marketing", "type": "user"
        }
        mock_get_service.return_value = (service, None)

        result = rename_label("L1", "Marketing")

        assert result["success"] is True
        assert result["label"]["name"] == "Marketing"
        assert result["cascaded"] == []

    @patch("app.services.gmail.labels.get_gmail_service")
    def test_rename_cascades_to_children(self, mock_get_service):
        service = _mock_service(
            [_label("L1", "Work"), _label("L2", "Work/Projects"), _label("L3", "Work/Projects/Alpha")]
        )
        service.users().labels().update().execute.return_value = {
            "id": "L1", "name": "Career", "type": "user"
        }
        mock_get_service.return_value = (service, None)

        result = rename_label("L1", "Career")

        assert result["success"] is True
        cascaded_names = {c["name"] for c in result["cascaded"]}
        assert cascaded_names == {"Career/Projects", "Career/Projects/Alpha"}

    @patch("app.services.gmail.labels.get_gmail_service")
    def test_rename_missing_label(self, mock_get_service):
        service = _mock_service([])
        mock_get_service.return_value = (service, None)

        result = rename_label("missing", "New Name")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_rename_requires_new_name(self):
        result = rename_label("L1", "")
        assert result["success"] is False


class TestMoveLabel:
    """Tests for move_label (rename under a computed name)."""

    @patch("app.services.gmail.labels.get_gmail_service")
    def test_move_to_new_parent(self, mock_get_service):
        service = _mock_service([_label("L1", "Projects")])
        service.users().labels().update().execute.return_value = {
            "id": "L1", "name": "Work/Projects", "type": "user"
        }
        mock_get_service.return_value = (service, None)

        result = move_label("L1", "Work")

        assert result["success"] is True
        assert result["label"]["name"] == "Work/Projects"

    @patch("app.services.gmail.labels.get_gmail_service")
    def test_move_to_root_strips_parent(self, mock_get_service):
        service = _mock_service([_label("L1", "Work/Projects")])
        service.users().labels().update().execute.return_value = {
            "id": "L1", "name": "Projects", "type": "user"
        }
        mock_get_service.return_value = (service, None)

        result = move_label("L1", "")

        assert result["success"] is True
        assert result["label"]["name"] == "Projects"
