"""
GuideAvailability Pydantic schemas.

Covers request/response shapes for:
  GET /api/v1/guides/{id}/availability  — GuideAvailabilityResponse
  PUT /api/v1/guides/{id}/availability  — GuideAvailabilityUpdate
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.guide_availability import AvailabilityStatus


# ---------------------------------------------------------------------------
# Update — PUT /api/v1/guides/{id}/availability
# ---------------------------------------------------------------------------

class GuideAvailabilityUpdate(BaseModel):
    """Request body for updating a guide's availability.

    Both fields are optional so a guide can update just the status,
    just the note, or both in one request.
    """

    status: Optional[AvailabilityStatus] = Field(
        default=None,
        description="New availability status.",
    )
    note: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Optional message for travelers (e.g. 'Back in October').",
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class GuideAvailabilityResponse(BaseModel):
    """Availability record returned for a guide."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    guide_id: UUID
    status: AvailabilityStatus
    note: Optional[str]
    created_at: datetime
    updated_at: datetime
