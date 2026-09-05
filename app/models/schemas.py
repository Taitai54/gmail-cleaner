"""
Pydantic Models - Request/Response Schemas
------------------------------------------
Data validation and serialization.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
import re


# ----- Filter Model -----


class FiltersModel(BaseModel):
    """Gmail filter options with validation."""

    older_than: Optional[str] = Field(
        default=None,
        description="Filter emails older than (e.g., 7d, 30d, 90d, 180d, 365d)",
    )
    after_date: Optional[str] = Field(
        default=None, description="Filter emails after this date (format: YYYY/MM/DD)"
    )
    before_date: Optional[str] = Field(
        default=None, description="Filter emails before this date (format: YYYY/MM/DD)"
    )
    larger_than: Optional[str] = Field(
        default=None, description="Filter emails larger than (e.g., 1M, 5M, 10M)"
    )
    category: Optional[str] = Field(default=None, description="Gmail category filter")
    sender: Optional[str] = Field(
        default=None,
        description="Filter emails from specific sender (email address or domain)",
    )
    label: Optional[str] = Field(default=None, description="Gmail label filter")

    @field_validator("older_than")
    @classmethod
    def validate_older_than(cls, v) -> Optional[str]:
        if v is None or v == "":
            return None
        if not re.match(r"^\d+d$", v):
            raise ValueError('older_than must be in format like "7d", "30d", "365d"')
        return v

    @field_validator("after_date")
    @classmethod
    def validate_after_date(cls, v) -> Optional[str]:
        if v is None or v == "":
            return None
        if not re.match(r"^\d{4}/\d{2}/\d{2}$", v):
            raise ValueError('after_date must be in format like "2025/01/15"')
        return v

    @field_validator("before_date")
    @classmethod
    def validate_before_date(cls, v) -> Optional[str]:
        if v is None or v == "":
            return None
        if not re.match(r"^\d{4}/\d{2}/\d{2}$", v):
            raise ValueError('before_date must be in format like "2025/01/15"')
        return v

    @field_validator("larger_than")
    @classmethod
    def validate_larger_than(cls, v) -> Optional[str]:
        if v is None or v == "":
            return None
        if not re.match(r"^\d+[KMG]$", v, re.IGNORECASE):
            raise ValueError('larger_than must be in format like "1M", "5M", "10M"')
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v) -> Optional[str]:
        if v is None or v == "":
            return None
        allowed = ["primary", "social", "promotions", "updates", "forums", "sent"]
        if v.lower() not in allowed:
            raise ValueError(f"category must be one of: {allowed}")
        return v.lower()

    @field_validator("sender")
    @classmethod
    def validate_sender(cls, v) -> Optional[str]:
        if v is None or v == "":
            return None
        # Allow email addresses or domain names
        sender = v.strip()
        if not sender:
            return None
        # Also allow plain sender keywords (e.g. "beta", "stripe") for fuzzy matching
        if "@" not in sender and "." not in sender:
            if len(sender) < 2:
                raise ValueError("sender keyword must be at least 2 characters")
        return sender


# ----- Request Models -----


class ScanRequest(BaseModel):
    """Request to start email scan."""

    limit: int = Field(default=500, ge=1, le=5000, description="Max emails to scan")
    filters: Optional[FiltersModel] = Field(
        default=None, description="Gmail filter options"
    )


class MarkReadRequest(BaseModel):
    """Request to mark emails as read."""

    count: int = Field(
        default=100,
        ge=0,
        le=100000,
        description="Number of emails to mark. Use 0 to mark all.",
    )
    filters: Optional[FiltersModel] = Field(
        default=None, description="Gmail filter options"
    )


class DeleteScanRequest(BaseModel):
    """Request to scan senders for deletion."""

    limit: int = Field(default=1000, ge=1, le=10000, description="Max emails to scan")
    filters: Optional[FiltersModel] = Field(
        default=None, description="Gmail filter options"
    )


class UnsubscribeRequest(BaseModel):
    """Request to unsubscribe from a sender."""

    domain: str = Field(default="", description="Sender domain")
    link: str = Field(default="", description="Unsubscribe link URL")


class DeleteEmailsRequest(BaseModel):
    """Request to delete emails from a sender."""

    sender: str = Field(default="", description="Sender email address")


class DeleteBulkRequest(BaseModel):
    """Request to delete emails from multiple senders."""

    senders: list[str] = Field(default=[], description="List of sender addresses")


class DownloadEmailsRequest(BaseModel):
    """Request to download emails from selected senders."""

    senders: list[str] = Field(default=[], description="List of sender addresses")


class CreateLabelRequest(BaseModel):
    """Request to create a new Gmail label."""

    name: str = Field(..., min_length=1, max_length=100, description="Label name")


class ApplyLabelRequest(BaseModel):
    """Request to apply a label to emails from selected senders."""

    label_id: str = Field(..., description="Gmail label ID to apply")
    senders: list[str] = Field(default=[], description="List of sender addresses")


class RemoveLabelRequest(BaseModel):
    """Request to remove a label from selected senders."""

    label_id: str = Field(..., description="Gmail label ID to remove")
    senders: list[str] = Field(default=[], description="List of sender addresses")


class ArchiveRequest(BaseModel):
    """Request to archive emails, from selected senders, specific thread IDs, search query, or matching filters."""

    senders: list[str] = Field(default=[], description="List of sender addresses")
    thread_ids: list[str] = Field(default=[], description="List of thread IDs to archive")
    query: Optional[str] = Field(
        default=None, description="Search query to archive all matching emails from inbox"
    )
    filters: Optional[FiltersModel] = Field(
        default=None, description="Gmail filter options to narrow or replace sender selection"
    )
    add_label_id: Optional[str] = Field(
        default=None, description="Optional Gmail label ID to tag archived emails"
    )
    add_label_name: Optional[str] = Field(
        default=None, description="Optional Gmail label name to create/tag archived emails"
    )

    @model_validator(mode="after")
    def validate_archive_targets(self):
        has_senders = bool(self.senders)
        has_threads = bool(self.thread_ids)
        has_query = bool((self.query or "").strip())
        has_filters = bool(
            self.filters
            and any(value not in (None, "", []) for value in self.filters.model_dump().values())
        )
        if not has_senders and not has_threads and not has_query and not has_filters:
            raise ValueError("Provide at least one of: senders, thread_ids, query, or filters")
        return self


class ApplyLabelToThreadsRequest(BaseModel):
    """Request to apply a label to specific thread IDs or matching search query."""

    thread_ids: list[str] = Field(default=[], description="List of thread IDs")
    query: Optional[str] = Field(default=None, description="Search query")
    label_id: Optional[str] = Field(default=None, description="Label ID to apply")
    label_name: Optional[str] = Field(default=None, description="Label name to create/apply")
    remove_inbox: bool = Field(default=False, description="Whether to remove from inbox (archive to label)")

    @model_validator(mode="after")
    def validate_targets(self):
        if not self.thread_ids and not (self.query or "").strip():
            raise ValueError("Provide thread_ids or query")
        if not (self.label_id or "").strip() and not (self.label_name or "").strip():
            raise ValueError("Provide label_id or label_name")
        return self


class RestorePreviewRequest(BaseModel):
    """Request to inspect an archive file."""

    filename: str = Field(..., min_length=1, description="Name of the archive file")
    content_base64: str = Field(..., min_length=1, description="Base64 encoded file content")


class RestoreExecuteRequest(BaseModel):
    """Request to execute restore of an archive file into Gmail."""

    filename: str = Field(..., min_length=1, description="Name of the archive file")
    content_base64: str = Field(..., min_length=1, description="Base64 encoded file content")
    target_label_id: Optional[str] = Field(default=None, description="Target label ID")
    target_label_name: Optional[str] = Field(default=None, description="Target label name to create")
    add_to_inbox: bool = Field(default=False, description="Add INBOX label to restored messages")
    mark_unread: bool = Field(default=False, description="Mark restored messages as unread")


class RenameLabelRequest(BaseModel):
    """Request to rename a Gmail label (cascades to "/"-nested children)."""

    label_id: str = Field(..., min_length=1, description="Gmail label ID to rename")
    new_name: str = Field(..., min_length=1, max_length=100, description="New label name")


class MoveLabelRequest(BaseModel):
    """Request to move a Gmail label under a new parent."""

    label_id: str = Field(..., min_length=1, description="Gmail label ID to move")
    new_parent: str = Field(
        default="", description="New parent label name, or empty to move to root"
    )


class MarkImportantRequest(BaseModel):
    """Request to mark/unmark emails as important."""

    senders: list[str] = Field(default=[], description="List of sender addresses")
    important: bool = Field(
        default=True, description="True to mark important, False to unmark"
    )


class ExportRequest(BaseModel):
    """Request to export email threads by search query."""

    query: str = Field(..., min_length=1, description="Gmail search query")
    max_threads: int = Field(
        default=50, ge=1, le=500, description="Maximum threads to export"
    )
    format: Literal["text", "markdown", "pdf", "json", "html", "eml", "zip"] = Field(
        default="text", description="Export format: text, markdown, pdf, json, html, or eml"
    )


class ProcessUnsubscribeLabelRequest(BaseModel):
    """Request to process emails with 'Unsubscribe' label."""

    label_name: str = Field(
        default="Unsubscribe", description="Name of the label to process"
    )


class SearchThreadsRequest(BaseModel):
    """Request to search for thread previews."""

    query: str = Field(default="", description="Gmail search query")
    max_results: int = Field(
        default=2000, ge=1, le=10000, description="Maximum threads to return (uses pagination)"
    )
    filters: Optional[FiltersModel] = Field(
        default=None, description="Optional Gmail filter options to refine the search"
    )

    @model_validator(mode="after")
    def validate_query_or_filters(self):
        has_query = bool((self.query or "").strip())
        has_filters = bool(
            self.filters
            and any(value not in (None, "", []) for value in self.filters.model_dump().values())
        )
        if not has_query and not has_filters:
            raise ValueError("Provide a query and/or at least one filter")
        return self


class ExportByIdsRequest(BaseModel):
    """Request to export specific threads by their IDs."""

    thread_ids: list[str] = Field(..., min_length=1, description="List of thread IDs to export")
    format: Literal["text", "markdown", "pdf", "json", "html", "eml", "zip"] = Field(
        default="text", description="Export format: text, markdown, pdf, json, html, or eml"
    )


class SignInRequest(BaseModel):
    """Request to start an OAuth sign-in or add-account flow."""

    client_type: Optional[Literal["gmail", "unidays"]] = Field(
        default=None,
        description="OAuth client to use: 'gmail' for personal, 'unidays' for work",
    )


class SwitchAccountRequest(BaseModel):
    """Request to switch active account."""

    email: str = Field(..., min_length=1, description="Email of account to switch to")


class RemoveAccountRequest(BaseModel):
    """Request to remove a signed-in account."""

    email: str = Field(..., min_length=1, description="Email of account to remove")


# ----- Response Models -----


class StatusResponse(BaseModel):
    """Generic status response."""

    status: str


class AuthStatusResponse(BaseModel):
    """Authentication status response."""

    email: Optional[str] = None
    logged_in: bool = False


class ScanStatusResponse(BaseModel):
    """Scan progress status response."""

    progress: int = 0
    message: str = "Ready"
    done: bool = False
    error: Optional[str] = None


class UnreadCountResponse(BaseModel):
    """Unread email count response."""

    count: int = 0
    error: Optional[str] = None


class UnsubscribeResponse(BaseModel):
    """Unsubscribe action response."""

    success: bool
    message: str
    domain: Optional[str] = None


class DeleteResponse(BaseModel):
    """Delete action response."""

    success: bool
    deleted: int = 0
    message: Optional[str] = None
