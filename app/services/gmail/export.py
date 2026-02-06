"""
Gmail Thread Export Operations
-------------------------------
Functions for searching and exporting email threads to text files.
"""

import base64
import logging
from typing import Any

from app.services.auth import get_gmail_service

logger = logging.getLogger(__name__)


def _decode_base64url(data: str) -> str:
    """Decode base64url encoded string.

    Args:
        data: Base64url encoded string

    Returns:
        Decoded string
    """
    if not data:
        return ""
    try:
        # Add padding if needed
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        decoded_bytes = base64.urlsafe_b64decode(data)
        return decoded_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"Failed to decode base64url data: {e}")
        return ""


def _extract_header(headers: list[dict[str, str]], name: str) -> str:
    """Extract a specific header value from headers list.

    Args:
        headers: List of header dictionaries with 'name' and 'value' keys
        name: Header name to find (case-insensitive)

    Returns:
        Header value or empty string if not found
    """
    name_lower = name.lower()
    for header in headers:
        if header.get("name", "").lower() == name_lower:
            return header.get("value", "")
    return ""


def _extract_body(payload: dict[str, Any]) -> str:
    """Extract email body from message payload.

    Handles both simple and multipart messages. Prefers text/plain over text/html.

    Args:
        payload: Message payload dictionary

    Returns:
        Decoded email body text
    """
    # Check if body data is directly in payload
    if "body" in payload and "data" in payload["body"]:
        return _decode_base64url(payload["body"]["data"])

    # Check for parts (multipart message)
    if "parts" in payload:
        text_plain = None
        text_html = None

        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")

            # Handle nested multipart
            if mime_type.startswith("multipart/"):
                nested_body = _extract_body(part)
                if nested_body:
                    return nested_body

            # Extract text/plain
            if mime_type == "text/plain" and "body" in part and "data" in part["body"]:
                text_plain = _decode_base64url(part["body"]["data"])

            # Extract text/html as fallback
            elif mime_type == "text/html" and "body" in part and "data" in part["body"]:
                text_html = _decode_base64url(part["body"]["data"])

        # Prefer text/plain over text/html
        return text_plain or text_html or ""

    return ""


def export_threads_by_query(query: str, max_threads: int = 50) -> str:
    """Search for email threads by query and export full content to text.

    Args:
        query: Gmail search query (e.g., "from:example.com", "subject:newsletter")
        max_threads: Maximum number of threads to export (default: 50)

    Returns:
        Formatted text content of all matching threads, or error message
    """
    # Get Gmail service
    service, error = get_gmail_service()
    if error:
        return f"Authentication error: {error}"

    if not query or not query.strip():
        return "Error: Search query cannot be empty"

    # Validate max_threads
    if not isinstance(max_threads, int) or max_threads < 1:
        max_threads = 50
    elif max_threads > 500:
        max_threads = 500  # Cap at 500 to prevent excessive API calls

    try:
        # Search for threads matching the query
        logger.info(f"Searching for threads with query: {query} (max: {max_threads})")
        results = service.users().threads().list(
            userId="me",
            q=query,
            maxResults=max_threads
        ).execute()

        threads = results.get("threads", [])

        if not threads:
            return "No email threads found matching your query."

        logger.info(f"Found {len(threads)} thread(s), fetching full content...")

        # Build the export content
        export_lines = []
        export_lines.append(f"Gmail Thread Export")
        export_lines.append(f"Search Query: {query}")
        export_lines.append(f"Total Threads: {len(threads)}")
        export_lines.append(f"{'=' * 80}\n")

        # Process each thread
        for thread_idx, thread in enumerate(threads, 1):
            thread_id = thread["id"]

            try:
                # Fetch full thread content
                thread_data = service.users().threads().get(
                    userId="me",
                    id=thread_id,
                    format="full"
                ).execute()

                messages = thread_data.get("messages", [])

                export_lines.append(f"\n{'=' * 80}")
                export_lines.append(f"THREAD {thread_idx} of {len(threads)} (ID: {thread_id})")
                export_lines.append(f"Messages in thread: {len(messages)}")
                export_lines.append(f"{'=' * 80}\n")

                # Process each message in the thread
                for msg_idx, message in enumerate(messages, 1):
                    headers = message.get("payload", {}).get("headers", [])

                    # Extract key headers
                    from_header = _extract_header(headers, "From")
                    date_header = _extract_header(headers, "Date")
                    subject_header = _extract_header(headers, "Subject")

                    # Extract body
                    body = _extract_body(message.get("payload", {}))

                    # Format message
                    export_lines.append(f"--- Message {msg_idx} of {len(messages)} ---")
                    export_lines.append(f"From: {from_header}")
                    export_lines.append(f"Date: {date_header}")
                    export_lines.append(f"Subject: {subject_header}")
                    export_lines.append(f"\n{body}\n")
                    export_lines.append("---\n")

            except Exception as e:
                logger.error(f"Error fetching thread {thread_id}: {e}", exc_info=True)
                export_lines.append(f"\nError fetching thread {thread_id}: {str(e)}\n")

        export_lines.append(f"\n{'=' * 80}")
        export_lines.append(f"End of Export - {len(threads)} thread(s)")
        export_lines.append(f"{'=' * 80}")

        full_export_content = "\n".join(export_lines)

        logger.info(f"Export completed successfully: {len(threads)} threads, "
                   f"{len(full_export_content)} characters")

        return full_export_content

    except Exception as e:
        logger.error(f"Error during thread export: {e}", exc_info=True)
        return f"Error during export: {str(e)}"


def search_thread_previews(query: str, max_results: int = 500) -> dict:
    """Search for threads and return lightweight previews (no body fetch).

    Args:
        query: Gmail search query
        max_results: Maximum number of thread previews to return (default: 500, uses pagination)

    Returns:
        {"success": bool, "threads": [...], "error": str | None}
        Each thread: {"id": str, "sender": str, "subject": str, "date": str, "snippet": str}
    """
    service, error = get_gmail_service()
    if error:
        return {"success": False, "threads": [], "error": error}

    if not query or not query.strip():
        return {"success": False, "threads": [], "error": "Search query cannot be empty"}

    if max_results < 1:
        max_results = 500
    elif max_results > 2000:
        max_results = 2000  # Reasonable upper limit

    try:
        # Collect all thread IDs using pagination
        thread_list = []
        page_token = None

        while len(thread_list) < max_results:
            # Gmail API has a max of 100 per page, so we paginate
            page_size = min(100, max_results - len(thread_list))

            results = service.users().threads().list(
                userId="me",
                q=query,
                maxResults=page_size,
                pageToken=page_token
            ).execute()

            threads_in_page = results.get("threads", [])
            if not threads_in_page:
                break

            thread_list.extend(threads_in_page)

            # Check if there are more pages
            page_token = results.get("nextPageToken")
            if not page_token:
                break

        if not thread_list:
            return {"success": True, "threads": [], "error": None}

        logger.info(f"Found {len(thread_list)} threads matching query: {query}")

        previews = []
        for thread in thread_list:
            thread_id = thread["id"]
            try:
                # Fetch with metadata only — much faster than format=full
                thread_data = service.users().threads().get(
                    userId="me", id=thread_id, format="metadata"
                ).execute()

                messages = thread_data.get("messages", [])
                # Use the last message in the thread for preview (most recent)
                if messages:
                    latest = messages[-1]
                    headers = latest.get("payload", {}).get("headers", [])
                    sender = _extract_header(headers, "From")
                    subject = _extract_header(headers, "Subject")
                    date = _extract_header(headers, "Date")
                    snippet = latest.get("snippet", "")
                else:
                    sender = subject = date = snippet = ""

                previews.append({
                    "id": thread_id,
                    "sender": sender,
                    "subject": subject,
                    "date": date,
                    "snippet": snippet,
                    "message_count": len(messages),
                })
            except Exception as e:
                logger.warning(f"Error fetching thread preview {thread_id}: {e}")
                previews.append({
                    "id": thread_id,
                    "sender": "",
                    "subject": "(error loading preview)",
                    "date": "",
                    "snippet": "",
                    "message_count": 0,
                })

        return {"success": True, "threads": previews, "error": None}

    except Exception as e:
        logger.error(f"Error searching threads: {e}", exc_info=True)
        return {"success": False, "threads": [], "error": str(e)}


def export_threads_by_ids(thread_ids: list[str]) -> str:
    """Export specific threads by their IDs (full content).

    Args:
        thread_ids: List of Gmail thread IDs to export

    Returns:
        Formatted text content of the selected threads
    """
    service, error = get_gmail_service()
    if error:
        return f"Authentication error: {error}"

    if not thread_ids:
        return "Error: No threads selected for export"

    try:
        export_lines = []
        export_lines.append("Gmail Thread Export (Selected)")
        export_lines.append(f"Total Threads: {len(thread_ids)}")
        export_lines.append(f"{'=' * 80}\n")

        for thread_idx, thread_id in enumerate(thread_ids, 1):
            try:
                thread_data = service.users().threads().get(
                    userId="me", id=thread_id, format="full"
                ).execute()

                messages = thread_data.get("messages", [])

                export_lines.append(f"\n{'=' * 80}")
                export_lines.append(f"THREAD {thread_idx} of {len(thread_ids)} (ID: {thread_id})")
                export_lines.append(f"Messages in thread: {len(messages)}")
                export_lines.append(f"{'=' * 80}\n")

                for msg_idx, message in enumerate(messages, 1):
                    headers = message.get("payload", {}).get("headers", [])
                    from_header = _extract_header(headers, "From")
                    date_header = _extract_header(headers, "Date")
                    subject_header = _extract_header(headers, "Subject")
                    body = _extract_body(message.get("payload", {}))

                    export_lines.append(f"--- Message {msg_idx} of {len(messages)} ---")
                    export_lines.append(f"From: {from_header}")
                    export_lines.append(f"Date: {date_header}")
                    export_lines.append(f"Subject: {subject_header}")
                    export_lines.append(f"\n{body}\n")
                    export_lines.append("---\n")

            except Exception as e:
                logger.error(f"Error fetching thread {thread_id}: {e}")
                export_lines.append(f"\nError fetching thread {thread_id}: {str(e)}\n")

        export_lines.append(f"\n{'=' * 80}")
        export_lines.append(f"End of Export - {len(thread_ids)} thread(s)")
        export_lines.append(f"{'=' * 80}")

        return "\n".join(export_lines)

    except Exception as e:
        logger.error(f"Error during thread export by IDs: {e}", exc_info=True)
        return f"Error during export: {str(e)}"
