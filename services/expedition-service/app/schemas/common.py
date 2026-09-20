"""
Common / shared Pydantic schemas for the Expedition Service.

Contains:
  - PaginationMeta        — page metadata included in every list response
  - PaginatedResponse     — generic paginated wrapper (typed via TypeVar)
  - ApiResponse           — standard single-item success envelope
  - ExpeditionFilter      — query parameters for GET /api/v1/expeditions
  - ExpeditionSearchQuery — free-text search parameters

These schemas have no dependency on any other schema in this package,
so they are safe to import from any other schema module.
"""

from __future__ import annotations

from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.models.expedition import ExpeditionStatus, ExpeditionVisibility

# Generic type variable for the paginated item type
T = TypeVar("T")


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    """Metadata returned alongside every paginated list response.

    Field names are serialised as camelCase in JSON so the frontend
    TypeScript interface (pageSize, totalItems, totalPages, hasNext,
    hasPrevious) matches directly.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    page: int = Field(
        ...,
        ge=1,
        description="Current page number (1-indexed).",
    )
    page_size: int = Field(       # → pageSize in JSON
        ...,
        ge=1,
        le=100,
        description="Number of items per page (max 100).",
    )
    total_items: int = Field(     # → totalItems in JSON
        ...,
        ge=0,
        description="Total number of items matching the current filter.",
    )
    total_pages: int = Field(     # → totalPages in JSON
        ...,
        ge=0,
        description="Total number of pages given current page_size.",
    )
    has_next: bool = Field(       # → hasNext in JSON
        ...,
        description="True if there is at least one more page after this one.",
    )
    has_previous: bool = Field(   # → hasPrevious in JSON
        ...,
        description="True if there is at least one page before this one.",
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list envelope.

    Usage:
        PaginatedResponse[ExpeditionSummary](
            items=[...],
            pagination=PaginationMeta(...)
        )

    The router declares its response_model as
        PaginatedResponse[ExpeditionSummary]
    and FastAPI generates the correct OpenAPI schema automatically.
    """

    items: List[T] = Field(
        default_factory=list,
        description="Page of results.",
    )
    pagination: PaginationMeta = Field(
        ...,
        description="Pagination metadata.",
    )


# ---------------------------------------------------------------------------
# Standard API envelope
# ---------------------------------------------------------------------------

class ApiResponse(BaseModel, Generic[T]):
    """Standard success envelope for single-resource responses.

    Wraps every non-list response so the frontend always receives a
    consistent shape: { success, message, data }.

    Usage:
        ApiResponse[ExpeditionResponse](
            success=True,
            message="Expedition created.",
            data=expedition_response
        )
    """

    success: bool = Field(
        default=True,
        description="Always True for non-error responses.",
    )
    message: str = Field(
        ...,
        description="Human-readable status message.",
    )
    data: Optional[T] = Field(
        default=None,
        description="The response payload. None for 204-style success responses.",
    )


# ---------------------------------------------------------------------------
# Expedition filter / search query parameters
# ---------------------------------------------------------------------------

class ExpeditionFilter(BaseModel):
    """Query parameters for GET /api/v1/expeditions.

    All fields are optional — omitting a field means "no filter on that
    dimension". Multiple fields are combined with AND.

    Used by the router as a dependency:
        def list_expeditions(filters: ExpeditionFilter = Depends()):

    This matches the documented listing behaviour:
      - community feed (community_id filter)
      - My Trips (organizer_id filter)
      - status-based filtering
      - visibility filtering
    """

    community_id: Optional[UUID] = Field(
        default=None,
        description="Filter expeditions belonging to this community.",
    )
    organizer_id: Optional[UUID] = Field(
        default=None,
        description="Filter expeditions organised by this user (My Trips).",
    )
    status: Optional[ExpeditionStatus] = Field(
        default=None,
        description="Filter by expedition lifecycle status.",
    )
    visibility: Optional[ExpeditionVisibility] = Field(
        default=None,
        description="Filter by visibility (PUBLIC or PRIVATE).",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed).",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100).",
    )
