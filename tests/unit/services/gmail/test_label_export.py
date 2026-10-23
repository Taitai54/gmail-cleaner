"""Tests for whole-label export."""

import base64
import zipfile
from unittest.mock import patch

import pytest

from app.core.state import state
from app.services.gmail.label_export import (
    export_label_background,
    get_label_export_file,
    get_label_export_status,
)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _full_message(message_id, thread_id, subject, body, internal_date):
    return {
        "id": message_id,
        "threadId": thread_id,
        "internalDate": str(internal_date),
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Ada <ada@example.com>"},
                {"name": "Date", "value": "Mon, 1 Jan 2024 00:00:00 +0000"},
                {"name": "Subject", "value": subject},
            ],
            "body": {"data": _b64(body.encode())},
        },
    }


class _Call:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error

    def execute(self):
        if self.error:
            raise self.error
        return self.payload


class _Batch:
    def __init__(self):
        self._ops = []

    def add(self, request, callback=None, request_id=None):
        self._ops.append((request, callback))

    def execute(self):
        for request, callback in self._ops:
            try:
                callback(None, request.execute(), None)
            except Exception as exc:
                callback(None, None, exc)


class _Labels:
    def __init__(self, service):
        self.service = service

    def list(self, **kwargs):
        return _Call({"labels": self.service.labels})


class _Messages:
    def __init__(self, service):
        self.service = service

    def list(self, **kwargs):
        self.service.queries.append(kwargs.get("q"))
        page_index = int(kwargs.get("pageToken") or 0)
        ids = self.service.pages[page_index]
        payload = {"messages": []}
        for mid in ids:
            record = self.service.messages[mid]
            thread_id = record.get("threadId")
            if not thread_id and record.get("full"):
                thread_id = record["full"].get("threadId")
            payload["messages"].append({"id": mid, "threadId": thread_id or "t"})
        if page_index + 1 < len(self.service.pages):
            payload["nextPageToken"] = str(page_index + 1)
        return _Call(payload)

    def get(self, **kwargs):
        message_id = kwargs["id"]
        fmt = kwargs.get("format")
        self.service.formats.append(fmt)
        record = self.service.messages[message_id]
        if record.get("error"):
            return _Call(error=record["error"])
        return _Call(record[fmt])


class _Users:
    def __init__(self, service):
        self.service = service

    def labels(self):
        return _Labels(self.service)

    def messages(self):
        return _Messages(self.service)


class FakeGmail:
    def __init__(self, labels, pages, messages):
        self.labels = labels
        self.pages = pages
        self.messages = messages
        self.queries = []
        self.formats = []

    def users(self):
        return _Users(self)

    def new_batch_http_request(self):
        return _Batch()


@pytest.fixture(autouse=True)
def _clean_export_state():
    state.reset_label_export()
    yield
    state.reset_label_export()


def _run(service, **kwargs):
    with patch(
        "app.services.gmail.label_export.get_gmail_service",
        return_value=(service, None),
    ):
        export_label_background(**kwargs)


def test_text_export_groups_a_thread_oldest_first_and_pages_the_label():
    service = FakeGmail(
        labels=[{"id": "Label_1", "name": "Receipts", "type": "user"}],
        pages=[["later"], ["earlier"]],
        messages={
            "later": {
                "full": _full_message("later", "t1", "Later note", "second", 2000),
            },
            "earlier": {
                "full": _full_message("earlier", "t1", "Earlier note", "first", 1000),
            },
        },
    )

    _run(service, label_name="Receipts", format_type="text", include_attachments=False)

    status = get_label_export_status()
    assert status["done"] is True
    assert status["error"] is None
    assert status["fetched_count"] == 2
    assert "file_path" not in status
    assert service.queries == ['label:"Receipts"', 'label:"Receipts"']

    path, filename, media_type = get_label_export_file()
    assert filename.startswith("Receipts_")
    assert filename.endswith(".txt")
    assert media_type == "text/plain"
    text = open(path, encoding="utf-8").read()
    assert text.index("Earlier note") < text.index("Later note")
    assert "first" in text and "second" in text


def test_attachment_export_writes_eml_files_for_the_exact_label():
    raw = b"From: Ada <ada@example.com>\r\nSubject: Invoice\r\n\r\nHello\r\n"
    service = FakeGmail(
        labels=[
            {"id": "Label_1", "name": "Parent", "type": "user"},
            {"id": "Label_2", "name": "Parent/Child", "type": "user"},
        ],
        pages=[["m1"]],
        messages={
            "m1": {
                "full": _full_message("m1", "t1", "Invoice", "Hello", 1000),
                "raw": {"id": "m1", "threadId": "t1", "raw": _b64(raw)},
            },
        },
    )

    _run(service, label_name="Parent", include_attachments=True)

    status = get_label_export_status()
    assert status["error"] is None
    assert status["include_attachments"] is True
    assert service.queries == ['label:"Parent"']
    assert service.formats == ["raw"]

    path, filename, media_type = get_label_export_file()
    assert filename.endswith(".zip")
    assert media_type == "application/zip"
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert len(names) == 1
        assert names[0].endswith(".eml")
        assert archive.read(names[0]) == raw


def test_quoted_label_name_is_escaped_in_the_gmail_query():
    service = FakeGmail(
        labels=[{"id": "Label_9", "name": 'Say "hi"', "type": "user"}],
        pages=[["m1"]],
        messages={"m1": {"full": _full_message("m1", "t9", "Hi", "Body", 1)}},
    )

    _run(service, label_name='Say "hi"', format_type="markdown")

    assert service.queries == ['label:"Say \\"hi\\""']
    path, filename, media_type = get_label_export_file()
    assert filename.endswith(".md")
    assert media_type == "text/markdown"
    assert "Body" in open(path, encoding="utf-8").read()


def test_missing_label_does_not_search_mail():
    service = FakeGmail(labels=[{"id": "Label_1", "name": "Other"}], pages=[], messages={})

    _run(service, label_name="Receipts")

    status = get_label_export_status()
    assert status["done"] is True
    assert "Label not found" in status["error"]
    assert service.queries == []
    assert get_label_export_file() is None


def test_failed_message_is_skipped_and_the_rest_export():
    service = FakeGmail(
        labels=[{"id": "Label_1", "name": "Receipts"}],
        pages=[["good", "bad"]],
        messages={
            "good": {"full": _full_message("good", "t1", "Kept", "kept body", 1)},
            "bad": {"threadId": "t2", "error": RuntimeError("gone")},
        },
    )

    _run(service, label_name="Receipts")

    status = get_label_export_status()
    assert status["error"] is None
    assert status["fetched_count"] == 1
    assert status["skipped_count"] == 1
    path, _, _ = get_label_export_file()
    assert "kept body" in open(path, encoding="utf-8").read()


def test_pdf_export_writes_a_pdf():
    service = FakeGmail(
        labels=[{"id": "Label_1", "name": "Receipts"}],
        pages=[["m1"]],
        messages={"m1": {"full": _full_message("m1", "t1", "Invoice", "Hello", 1)}},
    )

    _run(service, label_name="Receipts", format_type="pdf")

    path, filename, media_type = get_label_export_file()
    assert filename.endswith(".pdf")
    assert media_type == "application/pdf"
    assert open(path, "rb").read().startswith(b"%PDF")
