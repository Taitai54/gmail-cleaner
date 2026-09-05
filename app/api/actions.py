"""
Actions API Routes
------------------
POST endpoints for triggering operations.
"""

import base64
import logging
from functools import partial
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, status

from app.models import (
    ScanRequest,
    MarkReadRequest,
    DeleteScanRequest,
    UnsubscribeRequest,
    DeleteEmailsRequest,
    DeleteBulkRequest,
    DownloadEmailsRequest,
    CreateLabelRequest,
    ApplyLabelRequest,
    ApplyLabelToThreadsRequest,
    RestorePreviewRequest,
    RestoreExecuteRequest,
    RemoveLabelRequest,
    RenameLabelRequest,
    MoveLabelRequest,
    ArchiveRequest,
    MarkImportantRequest,
    ExportRequest,
    ProcessUnsubscribeLabelRequest,
    SearchThreadsRequest,
    ExportByIdsRequest,
    SignInRequest,
    SwitchAccountRequest,
    RemoveAccountRequest,
)
from app.services import (
    scan_emails,
    get_gmail_service,
    sign_out,
    get_accounts,
    switch_account,
    remove_account,
    unsubscribe_single,
    mark_emails_as_read,
    scan_senders_for_delete,
    delete_emails_by_sender,
    delete_emails_bulk_background,
    download_emails_background,
    create_label,
    delete_label,
    rename_label,
    move_label,
    apply_label_to_senders_background,
    remove_label_from_senders_background,
    archive_emails_background,
    mark_important_background,
)
from app.services.gmail.archive import apply_label_to_threads_background
from app.services.gmail.restore import parse_archive_file, restore_messages_background

router = APIRouter(prefix="/api", tags=["Actions"])
logger = logging.getLogger(__name__)


@router.post("/scan")
async def api_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """Start email scan for unsubscribe links."""
    filters_dict = (
        request.filters.model_dump(exclude_none=True) if request.filters else None
    )
    background_tasks.add_task(scan_emails, request.limit, filters_dict)
    return {"status": "started"}


@router.post("/sign-in")
async def api_sign_in(
    background_tasks: BackgroundTasks,
    request: Optional[SignInRequest] = Body(default=None),
):
    """Trigger OAuth sign-in flow."""
    client_type = request.client_type if request else None
    force_oauth = client_type is not None
    background_tasks.add_task(get_gmail_service, force_oauth, "consent select_account", client_type)
    return {"status": "signing_in"}


@router.post("/sign-out")
async def api_sign_out():
    """Sign out and clear credentials."""
    try:
        return sign_out()
    except Exception as e:
        logger.exception("Error during sign-out")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sign out",
        ) from e


@router.post("/unsubscribe")
async def api_unsubscribe(request: UnsubscribeRequest):
    """Unsubscribe from a single sender."""
    try:
        return unsubscribe_single(request.domain, request.link)
    except Exception as e:
        logger.exception("Error during unsubscribe")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsubscribe",
        ) from e


@router.post("/mark-read")
async def api_mark_read(request: MarkReadRequest, background_tasks: BackgroundTasks):
    """Mark emails as read."""
    filters_dict = (
        request.filters.model_dump(exclude_none=True) if request.filters else None
    )
    background_tasks.add_task(mark_emails_as_read, request.count, filters_dict)
    return {"status": "started"}


@router.post("/delete-scan")
async def api_delete_scan(
    request: DeleteScanRequest, background_tasks: BackgroundTasks
):
    """Scan senders for bulk delete."""
    filters_dict = (
        request.filters.model_dump(exclude_none=True) if request.filters else None
    )
    background_tasks.add_task(scan_senders_for_delete, request.limit, filters_dict)
    return {"status": "started"}


@router.post("/delete-emails")
async def api_delete_emails(request: DeleteEmailsRequest):
    """Delete emails from a specific sender."""
    if not request.sender or not request.sender.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sender email is required",
        )
    try:
        return delete_emails_by_sender(request.sender)
    except Exception as e:
        logger.exception("Error deleting emails")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete emails",
        ) from e


@router.post("/delete-emails-bulk")
async def api_delete_emails_bulk(
    request: DeleteBulkRequest, background_tasks: BackgroundTasks
):
    """Delete emails from multiple senders (background task with progress)."""
    background_tasks.add_task(delete_emails_bulk_background, request.senders)
    return {"status": "started"}


@router.post("/download-emails")
async def api_download_emails(
    request: DownloadEmailsRequest, background_tasks: BackgroundTasks
):
    """Start downloading email metadata for selected senders."""
    # Note: Empty list is allowed - service function will handle it gracefully
    background_tasks.add_task(download_emails_background, request.senders)
    return {"status": "started"}


# ----- Label Management Endpoints -----


@router.post("/labels")
async def api_create_label(request: CreateLabelRequest):
    """Create a new Gmail label."""
    try:
        return create_label(request.name)
    except Exception as e:
        logger.exception("Error creating label")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create label",
        ) from e


@router.delete("/labels/{label_id}")
async def api_delete_label(label_id: str, cascade: bool = False):
    """Delete a Gmail label. If it has "/"-nested children, pass cascade=true to
    delete them too; otherwise the child names are returned so the caller can confirm."""
    if not label_id or not label_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Label ID is required",
        )
    try:
        return delete_label(label_id, cascade=cascade)
    except Exception as e:
        logger.exception("Error deleting label")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete label",
        ) from e


@router.post("/labels/rename")
async def api_rename_label(request: RenameLabelRequest):
    """Rename a Gmail label (cascades to "/"-nested children)."""
    try:
        return rename_label(request.label_id, request.new_name)
    except Exception as e:
        logger.exception("Error renaming label")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rename label",
        ) from e


@router.post("/labels/move")
async def api_move_label(request: MoveLabelRequest):
    """Move a Gmail label under a new parent (empty new_parent moves it to the root)."""
    try:
        return move_label(request.label_id, request.new_parent)
    except Exception as e:
        logger.exception("Error moving label")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to move label",
        ) from e


@router.post("/apply-label")
async def api_apply_label(
    request: ApplyLabelRequest, background_tasks: BackgroundTasks
):
    """Apply a label to emails from selected senders."""
    if not request.label_id or not request.label_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Label ID is required",
        )
    if not request.senders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one sender is required",
        )
    background_tasks.add_task(
        apply_label_to_senders_background, request.label_id, request.senders
    )
    return {"status": "started"}


@router.post("/remove-label")
async def api_remove_label(
    request: RemoveLabelRequest, background_tasks: BackgroundTasks
):
    """Remove a label from emails from selected senders."""
    if not request.label_id or not request.label_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Label ID is required",
        )
    if not request.senders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one sender is required",
        )
    background_tasks.add_task(
        remove_label_from_senders_background, request.label_id, request.senders
    )
    return {"status": "started"}


@router.post("/archive")
async def api_archive(request: ArchiveRequest, background_tasks: BackgroundTasks):
    """Archive emails from selected senders, specific thread IDs, search query, or matching filters."""
    filters_dict = (
        request.filters.model_dump(exclude_none=True) if request.filters else None
    )
    if request.thread_ids or request.query or request.add_label_id or request.add_label_name:
        background_tasks.add_task(
            archive_emails_background,
            senders=request.senders,
            filters=filters_dict,
            thread_ids=request.thread_ids,
            query=request.query,
            add_label_id=request.add_label_id,
            add_label_name=request.add_label_name,
        )
    else:
        background_tasks.add_task(
            archive_emails_background, request.senders, filters_dict
        )
    return {"status": "started"}


@router.post("/mark-important")
async def api_mark_important(
    request: MarkImportantRequest, background_tasks: BackgroundTasks
):
    """Mark/unmark emails from selected senders as important."""
    if not request.senders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one sender is required",
        )
    background_tasks.add_task(
        partial(mark_important_background, request.senders, important=request.important)
    )
    return {"status": "started"}


@router.post("/export-threads")
async def api_export_threads(request: ExportRequest):
    """Export email threads by search query."""
    from fastapi.responses import Response
    from app.services.gmail.export import export_threads_by_query

    try:
        # Call the export function
        content, media_type, ext = export_threads_by_query(
            query=request.query,
            max_threads=request.max_threads,
            format_type=request.format
        )

        # Return as downloadable file
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename=email_export.{ext}"
            }
        )
    except Exception as e:
        logger.exception("Error during thread export")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export threads: {str(e)}"
        ) from e


@router.post("/process-unsubscribe-label")
async def api_process_unsubscribe_label(request: ProcessUnsubscribeLabelRequest):
    """Process emails with 'Unsubscribe' label and visit unsubscribe links."""
    from app.services.gmail.unsubscribe import process_unsubscribe_label

    try:
        result = process_unsubscribe_label(label_name=request.label_name)
        return {"success": True, "message": result}
    except Exception as e:
        logger.exception("Error processing unsubscribe label")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process unsubscribe label: {str(e)}"
        ) from e


# ----- Search & Selective Export Endpoints -----


@router.post("/search-threads")
async def api_search_threads(request: SearchThreadsRequest):
    """Search for email threads and return previews (sender, subject, date, snippet)."""
    from app.services.gmail.export import search_thread_previews

    result = search_thread_previews(
        query=request.query,
        max_results=request.max_results,
        filters=request.filters,
    )
    if not result["success"]:
        error_msg = result.get("error", "Search failed")
        msg_lower = (error_msg or "").lower()
        is_auth_error = any(k in msg_lower for k in ("sign-in", "sign in", "auth", "credential", "token"))
        is_client_error = "cannot be empty" in msg_lower
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED if is_auth_error else
                        status.HTTP_422_UNPROCESSABLE_ENTITY if is_client_error else
                        status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )
    return result


@router.post("/export-selected")
async def api_export_selected(request: ExportByIdsRequest):
    """Export specific email threads by ID."""
    from fastapi.responses import Response
    from app.services.gmail.export import export_threads_by_ids

    try:
        content, media_type, ext = export_threads_by_ids(
            thread_ids=request.thread_ids,
            format_type=request.format
        )
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename=email_export.{ext}"},
        )
    except Exception as e:
        logger.exception("Error during selective export")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export: {str(e)}",
        ) from e


# ----- Multi-Account Endpoints -----


@router.get("/accounts")
async def api_get_accounts():
    """Get list of signed-in accounts."""
    return {"accounts": get_accounts()}


@router.post("/accounts/switch")
async def api_switch_account(request: SwitchAccountRequest):
    """Switch active account."""
    result = switch_account(request.email)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to switch account"),
        )
    return result


@router.post("/accounts/remove")
async def api_remove_account(request: RemoveAccountRequest):
    """Remove a signed-in account."""
    result = remove_account(request.email)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to remove account"),
        )
    return result


@router.post("/accounts/add")
async def api_add_account(
    background_tasks: BackgroundTasks,
    request: Optional[SignInRequest] = Body(default=None),
):
    """Trigger OAuth flow to add a new account."""
    client_type = request.client_type if request else None
    background_tasks.add_task(get_gmail_service, True, "consent select_account", client_type)
    return {"status": "signing_in"}


@router.post("/apply-label-threads")
async def api_apply_label_threads(
    request: ApplyLabelToThreadsRequest, background_tasks: BackgroundTasks
):
    """Apply a label to thread IDs or matching search query, optionally archiving (removing from Inbox)."""
    background_tasks.add_task(
        apply_label_to_threads_background,
        thread_ids=request.thread_ids,
        query=request.query,
        label_id=request.label_id,
        label_name=request.label_name,
        remove_inbox=request.remove_inbox,
    )
    return {"status": "started"}


@router.post("/restore/preview")
async def api_restore_preview(request: RestorePreviewRequest):
    """Parse and inspect an uploaded archive file (.json, .zip of .eml, or .eml) for preview."""
    try:
        content = base64.b64decode(request.content_base64)
        parsed = parse_archive_file(content, request.filename)
        if not parsed.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=parsed.get("error", "Failed to parse archive file"),
            )
        # Avoid sending massive raw_bytes back to preview
        if "messages" in parsed:
            for m in parsed["messages"]:
                m.pop("_raw_bytes", None)
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error parsing restore archive preview")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview archive: {str(e)}",
        ) from e


@router.post("/restore/execute")
async def api_restore_execute(
    request: RestoreExecuteRequest,
    background_tasks: BackgroundTasks,
):
    """Upload archive and start background restoration into Gmail."""
    try:
        content = base64.b64decode(request.content_base64)
        parsed = parse_archive_file(content, request.filename)
        if not parsed.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=parsed.get("error", "Failed to parse archive file"),
            )

        messages = parsed.get("messages", [])
        if not messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No messages found to restore",
            )

        background_tasks.add_task(
            restore_messages_background,
            messages_data=messages,
            target_label_id=request.target_label_id,
            target_label_name=request.target_label_name,
            add_to_inbox=request.add_to_inbox,
            mark_unread=request.mark_unread,
        )
        return {
            "status": "started",
            "total_messages": len(messages),
            "message": f"Restoring {len(messages)} messages...",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error starting archive restoration")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start restore: {str(e)}",
        ) from e
