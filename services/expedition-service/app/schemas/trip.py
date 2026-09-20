"""
Trip Pydantic schemas — /api/v1/trips endpoints.

These wrap the underlying Expedition model but expose trip-centric
field names (host_id instead of organizer_id, host_name populated from
participant data) and make community_id fully optional for personal trips.

Schema hierarchy:
  TripBase       — shared validators
  TripCreate     — POST /api/v1/trips
  TripUpdate     — PUT /api/v1/trips/{id}
  TripResponse   — full detail (single trip) — serialised as camelCase JSON
  TripSummary    — card view (paginated list) — serialised as camelCase JSON
  TripFilter     — query params for listing / search
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel
from typing_extensions import Self

from app.models.expedition import ExpeditionStatus, ExpeditionVisibility


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class TripBase(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    destination: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    cover_image_url: Optional[str] = Field(default=None, max_length=500)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    max_participants: Optional[int] = Field(default=None, ge=1, le=500)
    visibility: Optional[ExpeditionVisibility] = None
    community_id: Optional[UUID] = Field(
        default=None,
        description="UUID of the community. Omit for personal (non-community) trips.",
    )


# ---------------------------------------------------------------------------
# Create — POST /api/v1/trips
# ---------------------------------------------------------------------------

class TripCreate(TripBase):
    title: str = Field(..., min_length=3, max_length=200)        # type: ignore[assignment]
    destination: str = Field(..., min_length=2, max_length=200)  # type: ignore[assignment]
    max_participants: int = Field(default=1, ge=1, le=500)       # type: ignore[assignment]
    visibility: ExpeditionVisibility = Field(                    # type: ignore[assignment]
        default=ExpeditionVisibility.PUBLIC,
    )

    @field_validator("start_date")
    @classmethod
    def start_not_in_past(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v < date.today():
            raise ValueError("start_date must be today or in the future.")
        return v

    @model_validator(mode="after")
    def end_after_start(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


# ---------------------------------------------------------------------------
# Update — PUT /api/v1/trips/{id}
# ---------------------------------------------------------------------------

class TripUpdate(TripBase):
    @model_validator(mode="after")
    def end_after_start(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


# ---------------------------------------------------------------------------
# Response — full detail
# ---------------------------------------------------------------------------

class TripResponse(BaseModel):
    """Full trip detail. Serialised as camelCase JSON for the frontend."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    community_id: Optional[UUID]
    host_id: UUID          # → hostId in JSON
    title: str
    destination: str
    description: Optional[str]
    cover_image_url: Optional[str]   # → coverImageUrl in JSON
    start_date: Optional[date]       # → startDate in JSON
    end_date: Optional[date]         # → endDate in JSON
    budget: Optional[Decimal]
    max_participants: int             # → maxParticipants in JSON
    current_participants_count: int = 0  # → currentParticipantsCount in JSON
    visibility: ExpeditionVisibility
    status: ExpeditionStatus
    host_name: Optional[str] = None  # → hostName in JSON
    created_at: datetime             # → createdAt in JSON
    updated_at: datetime             # → updatedAt in JSON


# ---------------------------------------------------------------------------
# Summary — card / list view
# ---------------------------------------------------------------------------

class TripSummary(BaseModel):
    """Lightweight card summary. Serialised as camelCase JSON for the frontend."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    community_id: Optional[UUID]
    host_id: UUID
    title: str
    destination: str
    cover_image_url: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    budget: Optional[Decimal]
    max_participants: int
    current_participants_count: int = 0
    visibility: ExpeditionVisibility
    status: ExpeditionStatus
    host_name: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Filter — query params for GET /api/v1/trips
# ---------------------------------------------------------------------------

class TripFilter(BaseModel):
    search: Optional[str] = Field(default=None, description="Free-text search on title/destination.")
    community_id: Optional[UUID] = Field(default=None, description="Filter by community (omit for personal trips).")
    personal_only: bool = Field(default=False, description="If true, return only trips with no community.")
    status: Optional[ExpeditionStatus] = None
    visibility: Optional[ExpeditionVisibility] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
