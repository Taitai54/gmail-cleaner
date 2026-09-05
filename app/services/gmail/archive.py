"""
Gmail Archive Operations
------------------------
Functions for archiving emails (removing from inbox).
"""

import logging
import time
from typing import Optional

from app.core import state
from app.services.auth import get_gmail_service
from app.services.gmail.helpers import build_gmail_query

logger = logging.getLogger(__name__)


def _fetch_and_archive(service, query: str, add_label_id: Optional[str] = None) -> int:
    """Find all messages matching a query and remove INBOX from them. Returns count archived."""
    message_ids = []
    page_token = None
    add_labels = [add_label_id] if add_label_id else []

    while True:
        result = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=500, pageToken=page_token)
            .execute()
        )

        messages = result.get("messages", [])
        message_ids.extend([m["id"] for m in messages])

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    archived = 0
    modify_body = {"removeLabelIds": ["INBOX"]}
    if add_labels:
        modify_body["addLabelIds"] = add_labels

    for j in range(0, len(message_ids), 100):
        batch_ids = message_ids[j : j + 100]
        service.users().messages().batchModify(
            userId="me", body={"ids": batch_ids, **modify_body}
        ).execute()
        archived += len(batch_ids)

        # Throttle every 500 emails (check at 100, 600, 1100, etc.)
        if (j + 100) % 500 == 0:
            time.sleep(0.5)

    return archived


def _archive_threads_by_ids(
    service, thread_ids: list[str], add_label_id: Optional[str] = None
) -> int:
    """Archive specific threads by ID. Returns count of threads archived."""
    add_labels = [add_label_id] if add_label_id else []
    modify_body = {"removeLabelIds": ["INBOX"]}
    if add_labels:
        modify_body["addLabelIds"] = add_labels

    archived = 0
    total = len(thread_ids)

    for i, thread_id in enumerate(thread_ids):
        try:
            service.users().threads().modify(
                userId="me", id=thread_id, body=modify_body
            ).execute()
            archived += 1
        except Exception as e:
            logger.warning(f"Error archiving thread {thread_id}: {e}")

        progress = int(((i + 1) / total) * 100)
        state.archive_status["progress"] = progress
        state.archive_status["message"] = f"Archived {archived}/{total} threads..."

        if (i + 1) % 50 == 0:
            time.sleep(0.3)

    return archived


def archive_emails_background(
    senders: Optional[list[str]] = None,
    filters: Optional[dict] = None,
    thread_ids: Optional[list[str]] = None,
    query: Optional[str] = None,
    add_label_id: Optional[str] = None,
    add_label_name: Optional[str] = None,
):
    """Archive emails, either by specific thread IDs, search query, selected senders, or filter set.

    Removes INBOX label and optionally adds add_label_id / add_label_name.
    """
    state.reset_archive()

    senders = senders or []
    thread_ids = thread_ids or []
    filter_query = build_gmail_query(filters) if filters else ""
    custom_query = (query or "").strip()

    if not senders and not filter_query and not thread_ids and not custom_query:
        state.archive_status["done"] = True
        state.archive_status["error"] = "No senders or filters specified"
        return

    state.archive_status["message"] = "Starting archive..."

    try:
        service, error = get_gmail_service()
        if error:
            state.archive_status["error"] = error
            state.archive_status["done"] = True
            return

        final_label_id = add_label_id
        if add_label_name and not final_label_id:
            from app.services.gmail.labels import create_label, _get_user_labels
            clean_name = add_label_name.strip()
            if clean_name:
                existing = _get_user_labels(service)
                matched = next((l["id"] for l in existing if l["name"].lower() == clean_name.lower()), None)
                if matched:
                    final_label_id = matched
                else:
                    created = create_label(service, clean_name)
                    if created.get("success"):
                        final_label_id = created["label"]["id"]

        total_archived = 0

        # Case 1: Specific Thread IDs
        if thread_ids:
            state.archive_status["total_threads"] = len(thread_ids)
            state.archive_status["message"] = f"Archiving {len(thread_ids)} threads..."
            total_archived = _archive_threads_by_ids(service, thread_ids, final_label_id)
            message = f"Archived {total_archived} thread(s)"

        # Case 2: Custom Search Query
        elif custom_query:
            state.archive_status["message"] = "Archiving matching search results..."
            final_query = f"in:inbox ({custom_query})"
            total_archived = _fetch_and_archive(service, final_query, final_label_id)
            message = f"Archived {total_archived} email(s) matching search query"

        # Case 3: Senders (with optional filter)
        elif senders:
            state.archive_status["total_senders"] = len(senders)
            for i, sender in enumerate(senders):
                state.archive_status["current_sender"] = i + 1
                state.archive_status["message"] = f"Archiving emails from {sender}..."
                state.archive_status["progress"] = int((i / len(senders)) * 100)

                q = f"from:{sender} in:inbox"
                if filter_query:
                    q = f"{q} {filter_query}"
                total_archived += _fetch_and_archive(service, q, final_label_id)

            message = f"Archived {total_archived} emails from {len(senders)} senders"

        # Case 4: Filter set only
        else:
            state.archive_status["message"] = "Archiving matching emails..."
            q = f"in:inbox {filter_query}"
            total_archived = _fetch_and_archive(service, q, final_label_id)
            message = f"Archived {total_archived} emails matching filters"

        state.archive_status["progress"] = 100
        state.archive_status["done"] = True
        state.archive_status["archived_count"] = total_archived
        state.archive_status["message"] = message

    except Exception as e:
        logger.exception("Error in archive_emails_background")
        state.archive_status["error"] = f"{e!s}"
        state.archive_status["done"] = True
        state.archive_status["message"] = f"Error: {e!s}"


def apply_label_to_threads_background(
    thread_ids: list[str],
    query: Optional[str] = None,
    label_id: Optional[str] = None,
    label_name: Optional[str] = None,
    remove_inbox: bool = False,
):
    """Apply a label to thread IDs or matching search query, optionally removing INBOX (archive to label)."""
    state.reset_label_operation()
    state.label_operation_status["message"] = "Applying label..."

    try:
        service, error = get_gmail_service()
        if error:
            state.label_operation_status["error"] = error
            state.label_operation_status["done"] = True
            return

        final_label_id = label_id
        if label_name and not final_label_id:
            from app.services.gmail.labels import create_label, _get_user_labels
            clean_name = label_name.strip()
            if clean_name:
                existing = _get_user_labels(service)
                matched = next((l["id"] for l in existing if l["name"].lower() == clean_name.lower()), None)
                if matched:
                    final_label_id = matched
                else:
                    created = create_label(service, clean_name)
                    if created.get("success"):
                        final_label_id = created["label"]["id"]

        if not final_label_id:
            state.label_operation_status["error"] = "No valid label specified"
            state.label_operation_status["done"] = True
            return

        modify_body = {"addLabelIds": [final_label_id]}
        if remove_inbox:
            modify_body["removeLabelIds"] = ["INBOX"]

        affected = 0
        if thread_ids:
            total = len(thread_ids)
            for i, tid in enumerate(thread_ids):
                try:
                    service.users().threads().modify(userId="me", id=tid, body=modify_body).execute()
                    affected += 1
                except Exception as e:
                    logger.warning(f"Error labeling thread {tid}: {e}")
                state.label_operation_status["progress"] = int(((i + 1) / total) * 100)
                state.label_operation_status["message"] = f"Labeled {affected}/{total} thread(s)..."
                if (i + 1) % 50 == 0:
                    time.sleep(0.3)
        elif query:
            # Query-based message batch modification
            page_token = None
            msg_ids = []
            while True:
                res = service.users().messages().list(userId="me", q=query, maxResults=500, pageToken=page_token).execute()
                msgs = res.get("messages", [])
                msg_ids.extend([m["id"] for m in msgs])
                page_token = res.get("nextPageToken")
                if not page_token:
                    break
            for j in range(0, len(msg_ids), 100):
                batch = msg_ids[j : j + 100]
                service.users().messages().batchModify(userId="me", body={"ids": batch, **modify_body}).execute()
                affected += len(batch)
                if (j + 100) % 500 == 0:
                    time.sleep(0.5)

        state.label_operation_status["progress"] = 100
        state.label_operation_status["done"] = True
        state.label_operation_status["affected_count"] = affected
        state.label_operation_status["message"] = f"Successfully updated {affected} email(s) with label!"

    except Exception as e:
        logger.exception("Error in apply_label_to_threads_background")
        state.label_operation_status["error"] = str(e)
        state.label_operation_status["done"] = True


def get_archive_status() -> dict:
    """Get archive operation status."""
    return state.archive_status.copy()

