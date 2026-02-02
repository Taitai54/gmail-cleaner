"""
Gmail Unsubscribe Operations
----------------------------
Functions for unsubscribing from email senders.
"""

import logging
import re
import urllib.error
import urllib.request
from typing import Any

from app.services.auth import get_gmail_service
from app.services.gmail.helpers import validate_unsafe_url

logger = logging.getLogger(__name__)


def unsubscribe_single(domain: str, link: str) -> dict:
    """Attempt to unsubscribe from a single sender."""
    if not link:
        return {"success": False, "message": "No unsubscribe link provided"}

    # Handle mailto: links
    if link.startswith("mailto:"):
        return {
            "success": False,
            "message": "Email-based unsubscribe - open in email client",
            "type": "mailto",
        }

    try:
        # Validate URL for SSRF (Check scheme and block private/loopback IPs)
        try:
            link = validate_unsafe_url(link)
        except ValueError as e:
            return {"success": False, "message": f"Security Error: {str(e)}"}

        # Create Default SSL context (Verifies certs by default)
        # We removed the custom context that disabled verification.

        # Try POST first (one-click), then GET
        req = urllib.request.Request(
            link,
            data=b"List-Unsubscribe=One-Click",
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; GmailUnsubscribe/1.0)",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
                if response.status in [200, 201, 202, 204]:
                    return {
                        "success": True,
                        "message": "Unsubscribed successfully",
                        "domain": domain,
                    }
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            # POST failed - log and fall back to GET
            logger.debug(
                f"POST unsubscribe failed for {domain}, falling back to GET: {e}"
            )
        except Exception as e:
            # Unexpected error - log it
            logger.warning(
                f"Unexpected error during POST unsubscribe for {domain}: {e}"
            )

        # Fallback to GET
        req = urllib.request.Request(
            link,
            headers={"User-Agent": "Mozilla/5.0 (compatible; GmailUnsubscribe/1.0)"},
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
                if response.status in [200, 201, 202, 204, 301, 302]:
                    return {
                        "success": True,
                        "message": "Unsubscribed (confirmation may be needed)",
                        "domain": domain,
                    }
                return {
                    "success": False,
                    "message": f"Server returned status {response.status}",
                }
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            return {"success": False, "message": f"Failed to unsubscribe: {e}"}

    except Exception as e:
        return {"success": False, "message": str(e)[:100]}


def process_unsubscribe_label(label_name: str = "Unsubscribe") -> str:
    """Process all emails with a specific label and automatically unsubscribe.

    Finds all emails with the specified label, extracts List-Unsubscribe headers,
    visits the unsubscribe URLs, and removes the label after processing.

    Args:
        label_name: Name of the Gmail label to process (default: "Unsubscribe")

    Returns:
        Summary message with count of processed emails
    """
    # Get Gmail service
    service, error = get_gmail_service()
    if error:
        return f"Authentication error: {error}"

    try:
        # Find the label ID by name
        logger.info(f"Searching for label: {label_name}")
        labels_result = service.users().labels().list(userId="me").execute()
        labels = labels_result.get("labels", [])

        label_id = None
        for label in labels:
            if label.get("name", "").lower() == label_name.lower():
                label_id = label.get("id")
                break

        if not label_id:
            return f"Error: Label '{label_name}' not found. Please create the label first."

        logger.info(f"Found label '{label_name}' with ID: {label_id}")

        # List all messages with this label
        messages_result = service.users().messages().list(
            userId="me",
            labelIds=[label_id]
        ).execute()

        messages = messages_result.get("messages", [])

        if not messages:
            return f"No emails found with label '{label_name}'."

        logger.info(f"Found {len(messages)} message(s) with label '{label_name}'")

        processed_count = 0
        success_count = 0
        error_count = 0

        # Process each message
        for msg in messages:
            msg_id = msg["id"]

            try:
                # Fetch message headers
                message = service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=["List-Unsubscribe", "From"]
                ).execute()

                headers = message.get("payload", {}).get("headers", [])

                # Extract List-Unsubscribe header
                unsubscribe_header = None
                from_header = None

                for header in headers:
                    if header.get("name", "").lower() == "list-unsubscribe":
                        unsubscribe_header = header.get("value", "")
                    if header.get("name", "").lower() == "from":
                        from_header = header.get("value", "")

                if not unsubscribe_header:
                    logger.warning(f"No List-Unsubscribe header found in message {msg_id}")
                    error_count += 1
                    # Still remove the label even if no unsubscribe link
                    service.users().messages().modify(
                        userId="me",
                        id=msg_id,
                        body={"removeLabelIds": [label_id]}
                    ).execute()
                    continue

                # Parse unsubscribe URL from header
                # List-Unsubscribe format: <http://example.com/unsub>, <mailto:unsub@example.com>
                url_match = re.search(r"<(https?://[^>]+)>", unsubscribe_header)

                if not url_match:
                    logger.warning(
                        f"No HTTP unsubscribe URL found in message {msg_id} "
                        f"(header: {unsubscribe_header})"
                    )
                    error_count += 1
                    # Remove label
                    service.users().messages().modify(
                        userId="me",
                        id=msg_id,
                        body={"removeLabelIds": [label_id]}
                    ).execute()
                    continue

                unsubscribe_url = url_match.group(1)
                logger.info(f"Found unsubscribe URL for {from_header}: {unsubscribe_url}")

                # Visit the unsubscribe link
                try:
                    # Validate URL for security
                    validated_url = validate_unsafe_url(unsubscribe_url)

                    # Try GET request to unsubscribe URL
                    req = urllib.request.Request(
                        validated_url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (compatible; GmailUnsubscribe/1.0)"
                        },
                    )

                    with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
                        if response.status in [200, 201, 202, 204, 301, 302]:
                            logger.info(
                                f"Successfully visited unsubscribe URL for {from_header}: "
                                f"HTTP {response.status}"
                            )
                            success_count += 1
                        else:
                            logger.warning(
                                f"Unsubscribe URL returned HTTP {response.status} "
                                f"for {from_header}"
                            )
                            error_count += 1

                except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
                    logger.warning(
                        f"Failed to visit unsubscribe URL for {from_header}: {e}"
                    )
                    error_count += 1
                except Exception as e:
                    logger.error(
                        f"Unexpected error visiting unsubscribe URL for {from_header}: {e}",
                        exc_info=True
                    )
                    error_count += 1

                # Remove the label from the message after processing
                service.users().messages().modify(
                    userId="me",
                    id=msg_id,
                    body={"removeLabelIds": [label_id]}
                ).execute()

                processed_count += 1

            except Exception as e:
                logger.error(f"Error processing message {msg_id}: {e}", exc_info=True)
                error_count += 1

        summary = (
            f"Processed {processed_count} email(s) with the '{label_name}' label. "
            f"Successfully unsubscribed from {success_count}, "
            f"{error_count} errors/skipped."
        )
        logger.info(summary)
        return summary

    except Exception as e:
        logger.error(f"Error processing unsubscribe label: {e}", exc_info=True)
        return f"Error: {str(e)}"
