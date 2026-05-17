"""
Gmail Thread Export Operations
-------------------------------
Functions for searching and exporting email threads to text files.
"""

import base64
import logging
from typing import Any, Optional

from app.services.auth import get_gmail_service
from app.services.gmail.helpers import build_gmail_query
from app.services.gmail.formatters import format_export

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


def export_threads_by_query(
    query: str, max_threads: int = 50, format_type: str = "text"
) -> tuple[Any, str, str]:
    """Search for email threads by query and export full content to requested format.

    Args:
        query: Gmail search query (e.g., "from:example.com", "subject:newsletter")
        max_threads: Maximum number of threads to export (default: 50)
        format_type: Format to export to (text, markdown, pdf)

    Returns:
        (content, media_type, file_extension) or raises Exception
    """
    # Get Gmail service
    service, error = get_gmail_service()
    if error:
        raise Exception(f"Authentication error: {error}")

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
            raise Exception("No email threads found matching your query.")

        logger.info(f"Found {len(threads)} thread(s), fetching full content...")

        threads_data = []

        # Process each thread
        for thread_idx, thread in enumerate(threads, 1):
            thread_id = thread["id"]

            try:
                thread_data = service.users().threads().get(
                    userId="me",
                    id=thread_id,
                    format="full"
                ).execute()

                messages = thread_data.get("messages", [])
                
                msgs_data = []
                # Process each message in the thread
                for msg_idx, message in enumerate(messages, 1):
                    headers = message.get("payload", {}).get("headers", [])
                    from_header = _extract_header(headers, "From")
                    date_header = _extract_header(headers, "Date")
                    subject_header = _extract_header(headers, "Subject")
                    body = _extract_body(message.get("payload", {}))

                    msgs_data.append({
                        "from": from_header,
                        "date": date_header,
                        "subject": subject_header,
                        "body": body
                    })
                
                threads_data.append({
                    "id": thread_id,
                    "messages": msgs_data
                })

            except Exception as e:
                logger.error(f"Error fetching thread {thread_id}: {e}", exc_info=True)

        if not threads_data:
            raise Exception(
                "Found matching threads, but failed to fetch their content. Please try again."
            )

        return format_export(threads_data, format_type)

    except Exception as e:
        logger.error(f"Error during thread export: {e}", exc_info=True)
        raise


def search_thread_previews(
    query: str, max_results: int = 2000, filters: Optional[Any] = None
) -> dict:
    """Search for threads and return lightweight previews (no body fetch).

    Args:
        query: Gmail search query entered by the user
        max_results: Maximum number of thread previews to return (default: 2000, uses pagination)
        filters: Optional FiltersModel or dict with Gmail filter options

    Returns:
        {"success": bool, "threads": [...], "error": str | None}
        Each thread: {"id": str, "sender": str, "subject": str, "date": str, "snippet": str}
    """
    service, error = get_gmail_service()
    if error:
        return {"success": False, "threads": [], "error": error}

    base_query = (query or "").strip()

    # Build filter query from FiltersModel/dict, if provided
    filter_query = ""
    if filters:
        try:
            filter_query = build_gmail_query(filters)
        except Exception as e:
            logger.warning(f"Failed to build filter query for search_thread_previews: {e}")

    # Combine user query and filter query
    if base_query and filter_query:
        combined_query = f"({base_query}) {filter_query}"
    elif filter_query:
        combined_query = filter_query
    else:
        combined_query = base_query

    if not combined_query:
        return {
            "success": False,
            "threads": [],
            "error": "Search query cannot be empty (provide a query and/or filters)",
        }

    if max_results < 1:
        max_results = 2000
    elif max_results > 10000:
        max_results = 10000  # Reasonable upper limit for deep searches

    try:
        # Collect all thread IDs using pagination
        thread_list = []
        page_token = None

        while len(thread_list) < max_results:
            # Gmail API has a max of 100 per page, so we paginate
            page_size = min(100, max_results - len(thread_list))

            results = (
                service.users()
                .threads()
                .list(
                    userId="me",
                    q=combined_query,
                    maxResults=page_size,
                    pageToken=page_token,
                )
                .execute()
            )

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

        logger.info(
            f"Found {len(thread_list)} threads matching query: {combined_query}"
        )

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


def export_threads_by_ids(
    thread_ids: list[str], format_type: str = "text"
) -> tuple[Any, str, str]:
    """Export specific threads by their IDs.

    Args:
        thread_ids: List of Gmail thread IDs to export
        format_type: Format to export to (text, markdown, pdf)

    Returns:
        (content, media_type, file_extension) or raises Exception
    """
    service, error = get_gmail_service()
    if error:
        raise Exception(f"Authentication error: {error}")

    if not thread_ids:
        raise Exception("Error: No threads selected for export")

    try:
        threads_data = []

        for thread_idx, thread_id in enumerate(thread_ids, 1):
            try:
                thread_data = service.users().threads().get(
                    userId="me", id=thread_id, format="full"
                ).execute()

                messages = thread_data.get("messages", [])

                msgs_data = []
                for msg_idx, message in enumerate(messages, 1):
                    headers = message.get("payload", {}).get("headers", [])
                    from_header = _extract_header(headers, "From")
                    date_header = _extract_header(headers, "Date")
                    subject_header = _extract_header(headers, "Subject")
                    body = _extract_body(message.get("payload", {}))

                    msgs_data.append({
                        "from": from_header,
                        "date": date_header,
                        "subject": subject_header,
                        "body": body
                    })
                
                threads_data.append({
                    "id": thread_id,
                    "messages": msgs_data
                })

            except Exception as e:
                logger.error(f"Error fetching thread {thread_id}: {e}")

        if not threads_data:
            raise Exception(
                "No selected threads could be fetched. They may have been deleted or are inaccessible."
            )

        return format_export(threads_data, format_type)

    except Exception as e:
        logger.error(f"Error during thread export by IDs: {e}", exc_info=True)
        raise
