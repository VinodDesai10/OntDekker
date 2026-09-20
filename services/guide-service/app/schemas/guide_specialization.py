"""
GuideSpecialization Pydantic schemas.

Covers request/response shapes for:
  POST   /api/v1/guides/{id}/specializations         — add specialization
  GET    /api/v1/guides/{id}/specializations         — list specializations
  DELETE /api/v1/guides/{id}/specializations/{spec_id} — remove specialization
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Create — POST /api/v1/guides/{id}/specializations
# ---------------------------------------------------------------------------

class GuideSpecializationCreate(BaseModel):
    """Request body for adding a specialization category to a guide profile."""

    category: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Specialization category tag (e.g. 'alpine', 'sea kayaking').",
    )


# ---------------------------------------------------------------------------
# Response — included in GuideProfileResponse and GuideProfileSummary
# ---------------------------------------------------------------------------

class GuideSpecializationResponse(BaseModel):
    """A single specialization entry in a guide profile response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    guide_id: UUID
    category: str
    created_at: datetime
    updated_at: datetime
