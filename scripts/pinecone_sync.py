"""
Gmail -> Pinecone Sync
----------------------
Pulls emails matching a Gmail search query, writes each as a markdown file
with frontmatter, then hands the folder to pinecone-management's
pinecone_bulk.py to chunk/embed/upload into the 'peace' index under the
'emails' namespace.

Re-running is safe: pinecone_bulk.py skips chunks whose ID already exists
(keyed off file path), and each email is exported to a deterministic
<message_id>.md filename, so unchanged emails are not re-embedded.

Usage:
    python scripts/pinecone_sync.py                       # last 30 days, 200 max
    python scripts/pinecone_sync.py --days 7 --max 50
    python scripts/pinecone_sync.py --query "from:*@stripe.com"
    python scripts/pinecone_sync.py --dry-run              # preview only, no upload
"""

import argparse
import logging
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.auth import get_gmail_service  # noqa: E402
from app.services.gmail.export import (  # noqa: E402
    _decode_base64url,
    _extract_body,
    _extract_header,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

EXPORT_DIR = Path(__file__).resolve().parent / ".email_export"
PINECONE_MANAGEMENT_DIR = Path("/Users/matthewatkinson/GitHub projects mac/pinecone-management")
PINECONE_PYTHON = PINECONE_MANAGEMENT_DIR / ".venv" / "bin" / "python3"
PINECONE_BULK = PINECONE_MANAGEMENT_DIR / "pinecone_bulk.py"


def _sanitize_filename(msg_id: str) -> str:
    return "".join(c for c in msg_id if c.isalnum() or c in ("-", "_")) + ".md"


def fetch_messages(service, query: str, max_results: int) -> list[dict]:
    """List message IDs matching query, paging as needed up to max_results."""
    message_ids = []
    page_token = None
    while len(message_ids) < max_results:
        remaining = max_results - len(message_ids)
        resp = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=min(remaining, 100),
            pageToken=page_token,
        ).execute()
        message_ids.extend(resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return message_ids[:max_results]


def export_message(service, msg_id: str, export_dir: Path) -> Path | None:
    """Fetch one message and write it to a frontmattered markdown file."""
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])

    subject = _extract_header(headers, "Subject") or "(no subject)"
    sender = _extract_header(headers, "From") or "(unknown sender)"
    to = _extract_header(headers, "To") or ""
    date_header = _extract_header(headers, "Date") or ""
    body = _extract_body(payload) or msg.get("snippet", "")

    # Prefer the Date header for createdAt; fall back to Gmail's internalDate (ms epoch).
    created_at = date_header
    if not created_at and msg.get("internalDate"):
        created_at = datetime.fromtimestamp(
            int(msg["internalDate"]) / 1000, tz=timezone.utc
        ).strftime("%a, %d %b %Y %H:%M:%S %z")

    escaped_subject = subject.replace('"', "'")
    escaped_from = sender.replace('"', "'")

    frontmatter = (
        "---\n"
        f'title: "{escaped_subject}"\n'
        f'createdAt: "{created_at}"\n'
        f'from: "{escaped_from}"\n'
        f'to: "{to}"\n'
        f"threadId: {msg.get('threadId', '')}\n"
        f"messageId: {msg_id}\n"
        "tags: emails\n"
        "---\n\n"
    )

    export_dir.mkdir(parents=True, exist_ok=True)
    out_path = export_dir / _sanitize_filename(msg_id)
    out_path.write_text(frontmatter + f"# {subject}\n\nFrom: {sender}\nTo: {to}\n\n{body}", encoding="utf-8")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Sync Gmail messages into Pinecone 'peace' index (emails namespace).")
    parser.add_argument("--query", default=None, help="Gmail search query. Default: newer_than:<days>d")
    parser.add_argument("--days", type=int, default=30, help="Look back this many days (ignored if --query given). Default: 30")
    parser.add_argument("--max", type=int, default=200, help="Max messages to sync. Default: 200")
    parser.add_argument("--dry-run", action="store_true", help="Export markdown only, don't upload to Pinecone")
    parser.add_argument("--keep-export", action="store_true", help="Don't delete the local .email_export folder after upload")
    args = parser.parse_args()

    if not PINECONE_PYTHON.exists() or not PINECONE_BULK.exists():
        logger.error(f"pinecone-management not found at {PINECONE_MANAGEMENT_DIR} — check the path is current.")
        sys.exit(1)

    service, error = get_gmail_service()
    if error:
        logger.error(f"Gmail auth error: {error}")
        sys.exit(1)

    query = args.query or f"newer_than:{args.days}d"
    logger.info(f"Searching Gmail: '{query}' (max {args.max})")
    message_refs = fetch_messages(service, query, args.max)
    logger.info(f"Found {len(message_refs)} message(s). Exporting...")

    exported = 0
    for ref in message_refs:
        try:
            export_message(service, ref["id"], EXPORT_DIR)
            exported += 1
        except Exception as e:
            logger.warning(f"Skipped message {ref.get('id')}: {e}")

    logger.info(f"Exported {exported} message(s) to {EXPORT_DIR}")

    if exported == 0:
        return

    cmd = [
        str(PINECONE_PYTHON), str(PINECONE_BULK),
        str(EXPORT_DIR),
        "--index-name", "peace",
        "--namespace", "emails",
        "--tags", "emails",
        "--collection", f"gmail-sync-{datetime.now().strftime('%Y-%m-%d')}",
    ]
    if args.dry_run:
        cmd.append("--dry-run")

    logger.info(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    if not args.keep_export and not args.dry_run:
        shutil.rmtree(EXPORT_DIR, ignore_errors=True)
        logger.info("Cleaned up local export folder.")


if __name__ == "__main__":
    main()
