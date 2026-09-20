"""
Expedition Pydantic schemas.

Covers all request/response shapes for:
  POST   /api/v1/expeditions
  GET    /api/v1/expeditions
  GET    /api/v1/expeditions/{id}
  PATCH  /api/v1/expeditions/{id}
  DELETE /api/v1/expeditions/{id}

Schema hierarchy:
  ExpeditionBase       — shared fields (no validators, no defaults)
  ExpeditionCreate     — POST body  (required fields + validators)
  ExpeditionUpdate     — PATCH body (all optional fields + validators)
  ExpeditionResponse   — full detail response (single expedition)
  ExpeditionSummary    — lightweight card response (used in list)
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from typing_extensions import Self

from app.models.expedition import ExpeditionStatus, ExpeditionVisibility


# ---------------------------------------------------------------------------
# Base (shared field definitions — no defaults, no validators)
# ---------------------------------------------------------------------------

class ExpeditionBase(BaseModel):
    """Fields shared between Create and Update.

    Not used as a request body directly — only inherited.
    """

    title: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=200,
        description="Expedition title (3–200 characters).",
        examples=["Everest Base Camp Trek 2026"],
    )
    destination: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=200,
        description="Primary destination name.",
        examples=["Khumbu Valley, Nepal"],
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Detailed expedition description (max 5000 chars).",
    )
    meeting_point: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Physical meeting location or instructions.",
        examples=["Lukla Airport, Gate 2"],
    )
    start_date: Optional[date] = Field(
        default=None,
        description="Planned departure date (YYYY-MM-DD).",
    )
    end_date: Optional[date] = Field(
        default=None,
        description="Planned return date (YYYY-MM-DD).",
    )
    max_participants: Optional[int] = Field(
        default=None,
        ge=2,
        le=500,
        description="Maximum number of participants including the organiser (2–500).",
    )
    budget: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0"),
        description="Estimated per-person budget. Must be non-negative.",
        examples=[Decimal("1200.00")],
    )
    visibility: Optional[ExpeditionVisibility] = Field(
        default=None,
        description="PUBLIC allows direct join; PRIVATE requires approval.",
    )
    cover_image_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="MinIO/CDN object URL for the expedition cover image.",
    )


# ---------------------------------------------------------------------------
# Create — POST /api/v1/expeditions
# ---------------------------------------------------------------------------

class ExpeditionCreate(ExpeditionBase):
    """Request body for creating a new expedition.

    Required fields: title, destination, community_id.
    The organizer_id is NOT accepted from the client — it is always set
    server-side from the authenticated user's JWT (sub claim).

    Validators:
      - end_date must be >= start_date when both are provided
      - start_date must be today or in the future
    """

    # Required on creation
    title: str = Field(                               # type: ignore[assignment]
        ...,
        min_length=3,
        max_length=200,
        description="Expedition title (3–200 characters).",
        examples=["Everest Base Camp Trek 2026"],
    )
    destination: str = Field(                         # type: ignore[assignment]
        ...,
        min_length=2,
        max_length=200,
        description="Primary destination name.",
    )
    community_id: Optional[UUID] = Field(
        default=None,
        description="UUID of the community this expedition belongs to. "
                    "Omit for personal (non-community) trips.",
    )

    # Provide sensible defaults for optional numeric fields at creation time
    max_participants: int = Field(                    # type: ignore[assignment]
        default=10,
        ge=2,
        le=500,
        description="Maximum participants including the organiser (2–500). Defaults to 10.",
    )
    visibility: ExpeditionVisibility = Field(         # type: ignore[assignment]
        default=ExpeditionVisibility.PUBLIC,
        description="PUBLIC allows direct join; PRIVATE requires approval.",
    )

    @field_validator("start_date")
    @classmethod
    def start_date_not_in_past(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v < date.today():
            raise ValueError("start_date must be today or in the future.")
        return v

    @model_validator(mode="after")
    def end_date_after_start(self) -> Self:
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be on or after start_date.")
        return self


# ---------------------------------------------------------------------------
# Update — PATCH /api/v1/expeditions/{id}
# ---------------------------------------------------------------------------

class ExpeditionUpdate(ExpeditionBase):
    """Request body for partial update of an expedition.

    All fields are optional — only provided fields are updated.
    The status field is intentionally excluded: status transitions
    are handled by dedicated lifecycle endpoints (publish, cancel, etc.)
    to enforce valid state machine transitions in the service layer.
    community_id and organizer_id cannot be changed after creation.

    Validator:
      - end_date must be >= start_date when both are provided
    """

    @model_validator(mode="after")
    def end_date_after_start(self) -> Self:
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be on or after start_date.")
        return self


# ---------------------------------------------------------------------------
# Response — GET /api/v1/expeditions/{id}
# ---------------------------------------------------------------------------

class ExpeditionResponse(BaseModel):
    """Full expedition detail returned from GET /api/v1/expeditions/{id}.

    Contains every persisted field. The router serialises an Expedition
    ORM object directly via from_attributes=True.

    Note: nested participant/itinerary/gallery/gear/review lists are
    intentionally excluded here — the frontend fetches them via
    dedicated sub-resource endpoints to keep the main payload lean.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    community_id: Optional[UUID]
    organizer_id: UUID

    title: str
    destination: str
    description: Optional[str]
    meeting_point: Optional[str]

    start_date: Optional[date]
    end_date: Optional[date]
    max_participants: int
    budget: Optional[Decimal]

    status: ExpeditionStatus
    visibility: ExpeditionVisibility
    cover_image_url: Optional[str]

    # Audit fields (from AuditMixin)
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]
    updated_by: Optional[UUID]

    # Soft-delete fields (from SoftDeleteMixin)
    is_deleted: bool
    deleted_at: Optional[datetime]


# ---------------------------------------------------------------------------
# Summary — used in paginated list responses
# ---------------------------------------------------------------------------

class ExpeditionSummary(BaseModel):
    """Lightweight expedition representation for list/card views.

    Used in GET /api/v1/expeditions (list). Excludes verbose fields
    like description and audit columns to keep list payloads small.
    The frontend renders this as a TripCard component.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    community_id: Optional[UUID]
    organizer_id: UUID

    title: str
    destination: str
    start_date: Optional[date]
    end_date: Optional[date]
    max_participants: int
    budget: Optional[Decimal]
    status: ExpeditionStatus
    visibility: ExpeditionVisibility
    cover_image_url: Optional[str]

    created_at: datetime
