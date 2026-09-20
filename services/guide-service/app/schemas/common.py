"""
Common / shared Pydantic schemas for the Guide Service.

Contains:
  - PaginationMeta      — page metadata included in every list response
  - PaginatedResponse   — generic paginated wrapper (typed via TypeVar)
  - ApiResponse         — standard single-item success envelope
  - GuideFilter         — query parameters for GET /api/v1/guides
"""

from __future__ import annotations

from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.guide_profile import VerificationStatus
from app.models.guide_availability import AvailabilityStatus

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    """Metadata returned alongside every paginated list response."""

    page: int = Field(..., ge=1, description="Current page number (1-indexed).")
    page_size: int = Field(..., ge=1, le=100, description="Items per page (max 100).")
    total_items: int = Field(..., ge=0, description="Total items matching the filter.")
    total_pages: int = Field(..., ge=0, description="Total pages given current page_size.")
    has_next: bool = Field(..., description="True if a next page exists.")
    has_previous: bool = Field(..., description="True if a previous page exists.")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list envelope.

    Usage:
        PaginatedResponse[GuideProfileSummary](items=[...], pagination=...)
    """

    items: List[T] = Field(default_factory=list, description="Page of results.")
    pagination: PaginationMeta = Field(..., description="Pagination metadata.")


# ---------------------------------------------------------------------------
# Standard API envelope
# ---------------------------------------------------------------------------

class ApiResponse(BaseModel, Generic[T]):
    """Standard success envelope for single-resource responses."""

    success: bool = Field(default=True)
    message: str = Field(...)
    data: Optional[T] = Field(default=None)


# ---------------------------------------------------------------------------
# Guide directory filter / query parameters
# ---------------------------------------------------------------------------

class GuideFilter(BaseModel):
    """Query parameters for GET /api/v1/guides.

    All fields are optional — omitting a field means no filter on that
    dimension. Multiple fields are combined with AND.

    Used by the router as a Depends():
        def list_guides(filters: GuideFilter = Depends()):
    """

    country: Optional[str] = Field(
        default=None,
        description="Filter guides who cover this country.",
    )
    language: Optional[str] = Field(
        default=None,
        description="Filter guides who speak this language.",
    )
    specialization: Optional[str] = Field(
        default=None,
        description="Filter guides who have this specialization category.",
    )
    availability: Optional[AvailabilityStatus] = Field(
        default=None,
        description="Filter guides by current availability status.",
    )
    verification_status: Optional[VerificationStatus] = Field(
        default=None,
        description="Filter by verification state (default: VERIFIED only in production).",
    )
    page: int = Field(default=1, ge=1, description="Page number (1-indexed).")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page.")
