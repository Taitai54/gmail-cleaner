"""
Gmail Archive Restoration Operations
-------------------------------------
Functions for parsing exported archives (JSON, EML/Zip) and restoring emails into Gmail via Gmail API.
"""

import email
import io
import json
import logging
import time
import zipfile
from email.message import EmailMessage
from email.utils import formatdate
from typing import Optional

from googleapiclient.http import MediaInMemoryUpload

from app.core import state
from app.services.auth import get_gmail_service
from app.services.gmail.labels import create_label, _get_user_labels

logger = logging.getLogger(__name__)


def parse_archive_file(content: bytes, filename: str) -> dict:
    """
    Parse an uploaded archive file (.json, .zip of .eml, or .eml) and return
    a normalized preview structure of all contained messages.
    """
    if not content:
        return {"success": False, "error": "Uploaded file is empty"}

    fn_lower = (filename or "").lower()

    if fn_lower.endswith(".json"):
        return _parse_json_archive(content, filename)
    elif fn_lower.endswith(".zip"):
        return _parse_zip_archive(content, filename)
    elif fn_lower.endswith(".eml"):
        return _parse_eml_file(content, filename)
    else:
        # Try JSON first, then ZIP, then EML
        try:
            return _parse_json_archive(content, filename)
        except Exception:
            try:
                return _parse_zip_archive(content, filename)
            except Exception:
                try:
                    return _parse_eml_file(content, filename)
                except Exception:
                    return {
                        "success": False,
                        "error": "Unsupported file format. Please upload a .json export or .zip containing .eml files.",
                    }


def _parse_json_archive(content: bytes, filename: str) -> dict:
    try:
        data = json.loads(content.decode("utf-8", errors="replace"))
    except Exception as e:
        return {"success": False, "error": f"Invalid JSON format: {str(e)}"}

    messages = []
    threads_count = 0

    if isinstance(data, dict):
        if "threads" in data and isinstance(data["threads"], list):
            threads_count = len(data["threads"])
            for t in data["threads"]:
                for m in t.get("messages", []):
                    messages.append(_normalize_message_dict(m))
        elif "messages" in data and isinstance(data["messages"], list):
            for m in data["messages"]:
                messages.append(_normalize_message_dict(m))
            threads_count = len({m.get("thread_id", idx) for idx, m in enumerate(messages)})
        elif "id" in data and "subject" in data:
            messages.append(_normalize_message_dict(data))
            threads_count = 1
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                if "messages" in item and isinstance(item["messages"], list):
                    threads_count += 1
                    for m in item["messages"]:
                        messages.append(_normalize_message_dict(m))
                else:
                    messages.append(_normalize_message_dict(item))
        if not threads_count:
            threads_count = len(messages)

    if not messages:
        return {"success": False, "error": "No valid messages found in the JSON archive."}

    return {
        "success": True,
        "filename": filename,
        "format": "json",
        "total_messages": len(messages),
        "total_threads": max(1, threads_count),
        "messages": messages,
    }


def _parse_zip_archive(content: bytes, filename: str) -> dict:
    try:
        zf = zipfile.ZipFile(io.BytesIO(content), "r")
    except Exception as e:
        return {"success": False, "error": f"Could not read ZIP archive: {str(e)}"}

    messages = []
    for info in zf.infolist():
        if info.is_dir() or not info.filename.lower().endswith(".eml"):
            continue
        try:
            eml_bytes = zf.read(info.filename)
            msg = email.message_from_bytes(eml_bytes)
            messages.append(_normalize_eml_message(msg, eml_bytes))
        except Exception as e:
            logger.warning(f"Failed to parse eml file {info.filename}: {e}")

    if not messages:
        return {
            "success": False,
            "error": "No .eml files found inside the ZIP archive.",
        }

    return {
        "success": True,
        "filename": filename,
        "format": "zip",
        "total_messages": len(messages),
        "total_threads": len(messages),
        "messages": messages,
    }


def _parse_eml_file(content: bytes, filename: str) -> dict:
    try:
        msg = email.message_from_bytes(content)
        parsed = _normalize_eml_message(msg, content)
        return {
            "success": True,
            "filename": filename,
            "format": "eml",
            "total_messages": 1,
            "total_threads": 1,
            "messages": [parsed],
        }
    except Exception as e:
        return {"success": False, "error": f"Invalid EML format: {str(e)}"}


def _normalize_message_dict(m: dict) -> dict:
    body = m.get("body") or ""
    snippet = m.get("snippet") or (body[:120] + "..." if len(body) > 120 else body)
    return {
        "from": str(m.get("from") or "Unknown"),
        "to": str(m.get("to") or ""),
        "cc": str(m.get("cc") or ""),
        "date": str(m.get("date") or ""),
        "subject": str(m.get("subject") or "(No Subject)"),
        "snippet": snippet.strip().replace("\n", " "),
        "body": body,
        "labels": m.get("labels") or [],
    }


def _normalize_eml_message(msg: email.message.Message, raw_bytes: bytes) -> dict:
    subject = msg.get("Subject", "(No Subject)")
    sender = msg.get("From", "Unknown")
    recipient = msg.get("To", "")
    cc = msg.get("Cc", "")
    date = msg.get("Date", "")

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get("Content-Disposition"))
            if ctype in ("text/plain", "text/html") and "attachment" not in cdisp:
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")

    snippet = body[:120].strip().replace("\n", " ") + ("..." if len(body) > 120 else "")

    return {
        "from": str(sender),
        "to": str(recipient),
        "cc": str(cc),
        "date": str(date),
        "subject": str(subject),
        "snippet": snippet,
        "body": body,
        "labels": [],
        "_raw_bytes": raw_bytes,
    }


def build_rfc822_bytes(message_dict: dict) -> bytes:
    """Build RFC 822 email bytes from message dictionary."""
    if "_raw_bytes" in message_dict and isinstance(message_dict["_raw_bytes"], (bytes, bytearray)):
        return bytes(message_dict["_raw_bytes"])

    msg = EmailMessage()
    msg["From"] = message_dict.get("from") or "Unknown"
    msg["To"] = message_dict.get("to") or ""
    if message_dict.get("cc"):
        msg["Cc"] = message_dict["cc"]
    msg["Subject"] = message_dict.get("subject") or "(No Subject)"

    date_str = message_dict.get("date")
    if date_str:
        msg["Date"] = date_str
    else:
        msg["Date"] = formatdate(time.time(), localtime=True)

    body_text = message_dict.get("body") or ""
    msg.set_content(body_text)
    return msg.as_bytes()


def restore_messages_background(
    messages_data: list[dict],
    target_label_id: Optional[str] = None,
    target_label_name: Optional[str] = None,
    add_to_inbox: bool = False,
    mark_unread: bool = False,
):
    """
    Background worker that imports messages into the user's Gmail mailbox using
    the Gmail API users.messages.insert endpoint.
    """
    state.reset_restore()

    if not messages_data:
        state.restore_status["done"] = True
        state.restore_status["error"] = "No messages provided for restoration."
        return

    service, err = get_gmail_service()
    if not service:
        state.restore_status["done"] = True
        state.restore_status["error"] = err or "Not signed in to Gmail."
        return

    total = len(messages_data)
    state.restore_status["total_messages"] = total
    state.restore_status["message"] = f"Preparing to restore {total} message(s)..."

    # Resolve target label ID if a name was supplied
    final_label_id = target_label_id
    if target_label_name and not final_label_id:
        target_name_clean = target_label_name.strip()
        if target_name_clean:
            # Check existing labels first
            existing = _get_user_labels(service)
            matched = next(
                (l["id"] for l in existing if l["name"].lower() == target_name_clean.lower()),
                None,
            )
            if matched:
                final_label_id = matched
            else:
                created = create_label(service, target_name_clean)
                if created.get("success"):
                    final_label_id = created["label"]["id"]

    label_ids = []
    if add_to_inbox:
        label_ids.append("INBOX")
    if mark_unread:
        label_ids.append("UNREAD")
    if final_label_id:
        label_ids.append(final_label_id)

    restored_count = 0

    for i, m in enumerate(messages_data):
        try:
            raw_bytes = build_rfc822_bytes(m)
            media = MediaInMemoryUpload(raw_bytes, mimetype="message/rfc822", resumable=False)

            body_dict = {
                "labelIds": label_ids,
                "internalDateSource": "dateHeader",
            }

            service.users().messages().insert(
                userId="me",
                body=body_dict,
                media_body=media,
            ).execute()

            restored_count += 1
        except Exception as e:
            logger.exception(f"Error inserting message {i}: {e}")

        progress = int(((i + 1) / total) * 100)
        state.restore_status["progress"] = progress
        state.restore_status["restored_count"] = restored_count
        state.restore_status["message"] = f"Restored {restored_count}/{total} messages..."

        if (i + 1) % 25 == 0:
            time.sleep(0.2)

    state.restore_status["progress"] = 100
    state.restore_status["done"] = True
    state.restore_status["message"] = f"Restoration complete! Successfully restored {restored_count} message(s)."
