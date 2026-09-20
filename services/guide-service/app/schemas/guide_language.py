"""
GuideLanguage Pydantic schemas.

Used nested inside GuideProfileResponse and for language updates.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

class GuideLanguageCreate(BaseModel):
    """A single language to add to a guide's spoken languages list."""

    language: str = Field(
        ...,
        min_length=2,
        max_length=80,
        description="Language name in English (e.g. 'Hindi', 'Japanese', 'French').",
        examples=["Hindi"],
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class GuideLanguageResponse(BaseModel):
    """Language record returned in profile responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    guide_id: UUID
    language: str
    created_at: datetime
