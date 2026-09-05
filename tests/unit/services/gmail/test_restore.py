"""
Unit tests for archive restore service and parsers.
"""

import io
import json
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from app.core import state
from app.services.gmail.restore import (
    build_rfc822_bytes,
    parse_archive_file,
    restore_messages_background,
)


def test_parse_json_archive_threads():
    payload = {
        "metadata": {"total_threads": 1, "total_messages": 2},
        "threads": [
            {
                "id": "t1",
                "messages": [
                    {
                        "id": "m1",
                        "from": "alice@example.com",
                        "to": "bob@example.com",
                        "subject": "Invoice #101",
                        "body": "Please find invoice attached.",
                        "date": "Wed, 15 Jan 2026 10:00:00 +0000",
                    },
                    {
                        "id": "m2",
                        "from": "bob@example.com",
                        "to": "alice@example.com",
                        "subject": "Re: Invoice #101",
                        "body": "Thank you, payment sent.",
                        "date": "Wed, 15 Jan 2026 11:00:00 +0000",
                    },
                ],
            }
        ],
    }
    raw = json.dumps(payload).encode("utf-8")
    result = parse_archive_file(raw, "archive.json")

    assert result["success"] is True
    assert result["format"] == "json"
    assert result["total_messages"] == 2
    assert result["total_threads"] == 1
    assert result["messages"][0]["subject"] == "Invoice #101"
    assert result["messages"][1]["subject"] == "Re: Invoice #101"


def test_parse_zip_archive_eml():
    eml_content = (
        b"From: sender@domain.com\r\n"
        b"To: me@example.com\r\n"
        b"Subject: Test Newsletter\r\n"
        b"Date: Thu, 16 Jan 2026 12:00:00 +0000\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"Here is your newsletter body."
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("thread_1/msg_1.eml", eml_content)

    result = parse_archive_file(buf.getvalue(), "archive.zip")

    assert result["success"] is True
    assert result["format"] == "zip"
    assert result["total_messages"] == 1
    assert result["messages"][0]["subject"] == "Test Newsletter"
    assert result["messages"][0]["from"] == "sender@domain.com"
    assert "newsletter body" in result["messages"][0]["body"]


def test_parse_single_eml():
    eml_content = (
        b"From: support@service.com\r\n"
        b"To: me@example.com\r\n"
        b"Subject: Password Reset\r\n"
        b"Date: Fri, 17 Jan 2026 09:00:00 +0000\r\n\r\n"
        b"Click here to reset."
    )
    result = parse_archive_file(eml_content, "message.eml")

    assert result["success"] is True
    assert result["format"] == "eml"
    assert result["total_messages"] == 1
    assert result["messages"][0]["subject"] == "Password Reset"


def test_build_rfc822_bytes():
    msg_dict = {
        "from": "user@example.com",
        "to": "recipient@example.com",
        "subject": "Meeting Tomorrow",
        "body": "Let's meet at 2pm.",
        "date": "Mon, 20 Jan 2026 14:00:00 +0000",
    }
    raw = build_rfc822_bytes(msg_dict)
    assert b"Subject: Meeting Tomorrow" in raw
    assert b"From: user@example.com" in raw
    assert b"Let's meet at 2pm." in raw


def test_restore_messages_background():
    mock_service = MagicMock()
    mock_insert = MagicMock()
    mock_insert.execute.return_value = {"id": "new_msg_id"}
    mock_service.users().messages().insert.return_value = mock_insert

    messages = [
        {
            "from": "a@example.com",
            "to": "b@example.com",
            "subject": "Test 1",
            "body": "Body 1",
            "date": "Mon, 20 Jan 2026 10:00:00 +0000",
        },
        {
            "from": "c@example.com",
            "to": "b@example.com",
            "subject": "Test 2",
            "body": "Body 2",
            "date": "Mon, 20 Jan 2026 11:00:00 +0000",
        },
    ]

    with patch("app.services.gmail.restore.get_gmail_service", return_value=(mock_service, None)):
        restore_messages_background(
            messages_data=messages,
            target_label_id="Label_123",
            add_to_inbox=True,
            mark_unread=False,
        )

    assert state.restore_status["done"] is True
    assert state.restore_status["restored_count"] == 2
    assert mock_service.users().messages().insert.call_count == 2
