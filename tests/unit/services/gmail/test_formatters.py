"""
Tests for Gmail Thread Export Formatters (formatters.py)
--------------------------------------------------------
Tests formatting of threads into Text, Markdown, PDF, JSON, HTML, and EML Zip.
"""

import json
import zipfile
import io
import pytest

from app.services.gmail.formatters import format_export


@pytest.fixture
def sample_threads_data():
    return [
        {
            "id": "thread_123",
            "messages": [
                {
                    "id": "msg_001",
                    "from": "alice@example.com",
                    "to": "bob@example.com",
                    "date": "Wed, 15 Jan 2026 10:00:00 +0000",
                    "subject": "Project Kickoff",
                    "body": "Hi Bob, looking forward to working on this project!",
                    "snippet": "Hi Bob, looking forward...",
                    "labels": ["INBOX", "IMPORTANT"],
                },
                {
                    "id": "msg_002",
                    "from": "bob@example.com",
                    "to": "alice@example.com",
                    "date": "Wed, 15 Jan 2026 10:30:00 +0000",
                    "subject": "Re: Project Kickoff",
                    "body": "Sounds great Alice! Let's schedule a call.",
                    "snippet": "Sounds great Alice!...",
                    "labels": ["INBOX"],
                },
            ],
        },
        {
            "id": "thread_456",
            "messages": [
                {
                    "id": "msg_003",
                    "from": "billing@saas.com",
                    "to": "me@example.com",
                    "date": "Thu, 16 Jan 2026 09:00:00 +0000",
                    "subject": "Your Monthly Invoice #1024",
                    "body": "Your invoice for $49 is now ready to view.",
                    "snippet": "Your invoice for $49...",
                    "labels": ["CATEGORY_UPDATES"],
                }
            ],
        },
    ]


class TestExportFormatters:
    def test_format_text(self, sample_threads_data):
        content, media_type, ext = format_export(sample_threads_data, "text")
        assert media_type == "text/plain"
        assert ext == "txt"
        assert "Total Threads: 2" in content
        assert "THREAD 1 of 2 (ID: thread_123)" in content
        assert "Project Kickoff" in content
        assert "alice@example.com" in content

    def test_format_markdown(self, sample_threads_data):
        content, media_type, ext = format_export(sample_threads_data, "markdown")
        assert media_type == "text/markdown"
        assert ext == "md"
        assert "# Gmail Thread Export" in content
        assert "## THREAD 1 of 2" in content
        assert "```text" in content

    def test_format_json(self, sample_threads_data):
        content, media_type, ext = format_export(sample_threads_data, "json")
        assert media_type == "application/json"
        assert ext == "json"
        parsed = json.loads(content)
        assert parsed["metadata"]["total_threads"] == 2
        assert parsed["metadata"]["total_messages"] == 3
        assert len(parsed["threads"]) == 2
        assert parsed["threads"][0]["id"] == "thread_123"

    def test_format_html(self, sample_threads_data):
        content, media_type, ext = format_export(sample_threads_data, "html")
        assert media_type == "text/html"
        assert ext == "html"
        assert "<!DOCTYPE html>" in content
        assert "Gmail Archive" in content
        assert "threadsData = " in content
        assert "Project Kickoff" in content

    def test_format_eml_zip(self, sample_threads_data):
        content, media_type, ext = format_export(sample_threads_data, "eml")
        assert media_type == "application/zip"
        assert ext == "zip"
        assert isinstance(content, bytes)

        # Verify ZIP contains .eml files
        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            namelist = zf.namelist()
            assert len(namelist) == 3
            assert any("msg_01_Project Kickoff.eml" in name for name in namelist)

    def test_format_pdf(self, sample_threads_data):
        content, media_type, ext = format_export(sample_threads_data, "pdf")
        assert media_type == "application/pdf"
        assert ext == "pdf"
        assert isinstance(content, bytes)
        assert content.startswith(b"%PDF")
