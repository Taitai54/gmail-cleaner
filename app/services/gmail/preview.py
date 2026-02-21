"""
Gmail Preview Operations
------------------------
Functions for previewing emails before deletion.
"""

import logging
from typing import Optional

from app.services.auth import get_gmail_service
from app.services.gmail.helpers import get_subject

logger = logging.getLogger(__name__)


def preview_emails_from_sender(sender: str, limit: int = 10) -> dict:
    """Preview emails from a specific sender.
    
    Args:
        sender: Email address or domain to preview
        limit: Maximum number of emails to fetch (1-50)
        
    Returns:
        dict with success status and email list
    """
    if not sender or not sender.strip():
        return {
            "success": False,
            "error": "No sender specified",
            "emails": []
        }
    
    # Validate limit
    limit = max(1, min(limit, 50))
    
    service, error = get_gmail_service()
    if error:
        return {
            "success": False,
            "error": error,
            "emails": []
        }
    
    try:
        # Find emails from sender
        query = f"from:{sender}"
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=limit
        ).execute()
        
        messages = results.get("messages", [])
        
        if not messages:
            return {
                "success": True,
                "emails": [],
                "message": "No emails found from this sender"
            }
        
        # Fetch email details in batch
        emails = []
        batch_size = 100
        
        def process_message(request_id, response, exception) -> None:
            if exception:
                logger.warning(f"Failed to fetch email {request_id}: {exception}")
                return
            
            headers = response.get("payload", {}).get("headers", [])
            subject = get_subject(headers)
            
            # Extract date
            email_date = None
            for header in headers:
                if header["name"].lower() == "date":
                    email_date = header["value"]
                    break
            
            # Get snippet
            snippet = response.get("snippet", "")
            
            emails.append({
                "id": response.get("id"),
                "subject": subject,
                "date": email_date,
                "snippet": snippet
            })
        
        # Execute batch request
        for i in range(0, len(messages), batch_size):
            batch_ids = messages[i:i + batch_size]
            batch = service.new_batch_http_request(callback=process_message)
            
            for msg_data in batch_ids:
                batch.add(
                    service.users().messages().get(
                        userId="me",
                        id=msg_data["id"],
                        format="metadata",
                        metadataHeaders=["Subject", "Date"]
                    )
                )
            
            batch.execute()
        
        return {
            "success": True,
            "emails": emails,
            "count": len(emails)
        }
        
    except Exception as e:
        logger.error(f"Error previewing emails: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "emails": []
        }
