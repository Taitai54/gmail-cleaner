"""
Export every message on a single Gmail label.

Text, Markdown, and PDF reuse the existing thread formatter.
Including attachments writes a zip of .eml files (Gmail raw format),
which keeps the original message and its files together.
"""

import base64
import logging
import os
import re
import tempfile
import time
import zipfile
from datetime import datetime
from typing import Any

from app.core import state
from app.services.auth import get_gmail_service
from app.services.gmail.export import _extract_body, _extract_header
from app.services.gmail.formatters import format_export

logger = logging.getLogger(__name__)

_FULL_BATCH_SIZE = 25
_RAW_BATCH_SIZE = 5


def _label_search_query(name: str) -> str:
    """Build a Gmail query that matches this label name exactly."""
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'label:"{escaped}"'


def _download_name(label: str, ext: str) -> str:
    stamp = datetime.now().strftime("%Y-%m-%d")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", label).strip("._") or "label"
    return f"{safe[:60]}_{stamp}.{ext}"


def _fail(message: str) -> None:
    status = state.label_export_status
    status["progress"] = 100
    status["done"] = True
    status["running"] = False
    status["error"] = message
    status["message"] = message


def _find_label_name(service, label_name: str) -> str | None:
    """Return the canonical label name, or None if this account has no such label."""
    results = service.users().labels().list(userId="me").execute()
    for label in results.get("labels", []):
        if label.get("name") == label_name:
            return label["name"]
    return None


def _list_message_ids(service, query: str) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    page_token = None
    status = state.label_export_status

    while True:
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=500, pageToken=page_token)
            .execute()
        )
        for msg in results.get("messages", []):
            mid = msg.get("id")
            if mid and mid not in seen:
                seen.add(mid)
                ids.append(mid)
        status["message"] = f"Finding messages... {len(ids)} so far"
        page_token = results.get("nextPageToken")
        if not page_token:
            break
    return ids


def _fetch_batch(service, message_ids: list[str], fmt: str) -> tuple[list[dict], int]:
    """Fetch one page of messages. Failed items are counted and skipped."""
    batch = service.new_batch_http_request()
    found: list[dict] = []
    failed = 0

    def callback(_request_id, response, exception, bucket=found) -> None:
        nonlocal failed
        if exception is None and response:
            bucket.append(response)
        else:
            failed += 1

    for mid in message_ids:
        batch.add(
            service.users().messages().get(userId="me", id=mid, format=fmt),
            callback=callback,
            request_id=mid,
        )

    try:
        batch.execute()
    except Exception as exc:
        logger.error("Label export batch failed: %s", exc)
        return [], len(message_ids)

    return found, failed


def _decode_raw(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def _message_to_export(message: dict) -> dict[str, str]:
    headers = message.get("payload", {}).get("headers", [])
    return {
        "from": _extract_header(headers, "From"),
        "date": _extract_header(headers, "Date"),
        "subject": _extract_header(headers, "Subject"),
        "body": _extract_body(message.get("payload", {})),
    }


def _group_threads(messages: list[dict]) -> list[dict]:
    """Group labeled messages by thread, oldest first within each thread."""
    order: list[str] = []
    grouped: dict[str, list[dict]] = {}
    for message in messages:
        thread_id = message.get("threadId") or message.get("id") or ""
        if thread_id not in grouped:
            order.append(thread_id)
            grouped[thread_id] = []
        grouped[thread_id].append(message)

    threads = []
    for thread_id in order:
        msgs = sorted(grouped[thread_id], key=lambda m: int(m.get("internalDate") or 0))
        threads.append({"id": thread_id, "messages": [_message_to_export(m) for m in msgs]})
    return threads


def _update_fetch_progress(done: int, total: int) -> None:
    status = state.label_export_status
    status["fetched_count"] = done
    status["progress"] = 10 + int(85 * done / total) if total else 10
    status["message"] = f"Fetching {done}/{total} messages..."


def _write_bytes(path: str, content: Any) -> None:
    if isinstance(content, str):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    else:
        with open(path, "wb") as handle:
            handle.write(content)


def _finish(path: str, filename: str, media_type: str, message: str) -> None:
    status = state.label_export_status
    status["file_path"] = path
    status["filename"] = filename
    status["media_type"] = media_type
    status["progress"] = 100
    status["done"] = True
    status["running"] = False
    status["error"] = None
    status["message"] = message


def _export_formatted(service, message_ids: list[str], label_name: str, format_type: str) -> None:
    status = state.label_export_status
    fetched: list[dict] = []
    skipped = 0
    total = len(message_ids)

    for start in range(0, total, _FULL_BATCH_SIZE):
        chunk = message_ids[start : start + _FULL_BATCH_SIZE]
        messages, failed = _fetch_batch(service, chunk, "full")
        fetched.extend(messages)
        skipped += failed
        _update_fetch_progress(min(start + len(chunk), total), total)
        if (start // _FULL_BATCH_SIZE + 1) % 5 == 0:
            time.sleep(0.2)

    status["skipped_count"] = skipped
    status["fetched_count"] = len(fetched)
    if not fetched:
        _fail("Found messages with that label, but none of them could be fetched.")
        return

    status["message"] = "Writing export..."
    status["progress"] = 96
    threads = _group_threads(fetched)
    content, media_type, ext = format_export(threads, format_type)

    fd, path = tempfile.mkstemp(prefix="gmail-cleaner-label-", suffix=f".{ext}")
    os.close(fd)
    try:
        _write_bytes(path, content)
    except Exception:
        try:
            os.remove(path)
        except OSError:
            pass
        raise

    note = f'Exported {len(fetched)} message(s) from "{label_name}".'
    if skipped:
        note += f" Skipped {skipped} that could not be fetched."
    _finish(path, _download_name(label_name, ext), media_type, note)


def _export_eml_zip(service, message_ids: list[str], label_name: str) -> None:
    status = state.label_export_status
    total = len(message_ids)
    written = 0
    skipped = 0

    fd, path = tempfile.mkstemp(prefix="gmail-cleaner-label-", suffix=".zip")
    os.close(fd)
    try:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for start in range(0, total, _RAW_BATCH_SIZE):
                chunk = message_ids[start : start + _RAW_BATCH_SIZE]
                messages, failed = _fetch_batch(service, chunk, "raw")
                skipped += failed
                for message in messages:
                    raw = message.get("raw") or ""
                    try:
                        data = _decode_raw(raw) if raw else b""
                    except Exception as exc:
                        logger.warning("Could not decode raw message %s: %s", message.get("id"), exc)
                        skipped += 1
                        continue
                    if not data:
                        skipped += 1
                        continue
                    written += 1
                    mid = re.sub(r"[^A-Za-z0-9_-]+", "", str(message.get("id") or written))
                    archive.writestr(f"{written:04d}_{mid}.eml", data)
                _update_fetch_progress(min(start + len(chunk), total), total)
                if (start // _RAW_BATCH_SIZE + 1) % 5 == 0:
                    time.sleep(0.2)
    except Exception:
        try:
            os.remove(path)
        except OSError:
            pass
        raise

    status["skipped_count"] = skipped
    status["fetched_count"] = written
    if written == 0:
        try:
            os.remove(path)
        except OSError:
            pass
        _fail("Found messages with that label, but none of them could be fetched.")
        return

    note = f'Exported {written} message(s) from "{label_name}", with attachments.'
    if skipped:
        note += f" Skipped {skipped} that could not be fetched."
    _finish(path, _download_name(label_name, "zip"), "application/zip", note)


def export_label_background(
    label_name: str, format_type: str = "text", include_attachments: bool = False
) -> None:
    """Export every message on a label. Updates label_export_status as it runs."""
    status = state.label_export_status
    status["include_attachments"] = bool(include_attachments)
    status["error"] = None
    status["done"] = False

    try:
        service, error = get_gmail_service()
        if error:
            _fail(error)
            return

        label_name = (label_name or "").strip()
        if not label_name:
            _fail("Label is required")
            return

        resolved = _find_label_name(service, label_name)
        if not resolved:
            _fail(f"Label not found: {label_name}")
            return

        status["message"] = f'Finding messages labeled "{resolved}"...'
        status["progress"] = 5
        message_ids = _list_message_ids(service, _label_search_query(resolved))
        if not message_ids:
            _fail(f'No messages found with the label "{resolved}".')
            return

        status["total"] = len(message_ids)
        if include_attachments:
            _export_eml_zip(service, message_ids, resolved)
        else:
            chosen = format_type if format_type in ("text", "markdown", "pdf") else "text"
            _export_formatted(service, message_ids, resolved, chosen)
    except Exception as exc:
        logger.exception("Label export failed")
        _fail(f"Label export failed: {exc}")


def get_label_export_status() -> dict:
    """Status for the UI. The file path stays on the server."""
    status = state.label_export_status
    return {
        "progress": status["progress"],
        "message": status["message"],
        "done": status["done"],
        "error": status["error"],
        "running": status["running"],
        "total": status["total"],
        "fetched_count": status["fetched_count"],
        "skipped_count": status["skipped_count"],
        "include_attachments": status["include_attachments"],
        "filename": status["filename"],
    }


def get_label_export_file() -> tuple[str, str, str] | None:
    """Return (path, filename, media_type) when a finished export is ready."""
    status = state.label_export_status
    path = status.get("file_path")
    if not status.get("done") or status.get("error") or not path or not os.path.isfile(path):
        return None
    return path, status.get("filename") or "label_export", status.get("media_type") or "application/octet-stream"
