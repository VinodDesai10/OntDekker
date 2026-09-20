"""
GuideLocation Pydantic schemas.

Used nested inside GuideProfileResponse and for bulk location updates.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Create — used when adding a single location to a guide's profile
# ---------------------------------------------------------------------------

class GuideLocationCreate(BaseModel):
    """A single geographic coverage area to add to a guide's profile.

    country is required. region and city are optional refinements.
    """

    country: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Country name (e.g. 'India', 'Japan').",
        examples=["India"],
    )
    region: Optional[str] = Field(
        default=None,
        max_length=100,
        description="State / province / region (e.g. 'Himachal Pradesh').",
    )
    city: Optional[str] = Field(
        default=None,
        max_length=100,
        description="City or locality (e.g. 'Manali').",
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class GuideLocationResponse(BaseModel):
    """Location record returned in profile responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    guide_id: UUID
    country: str
    region: Optional[str]
    city: Optional[str]
    created_at: datetime
