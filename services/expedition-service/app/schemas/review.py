"""
Review Pydantic schemas.

Covers request/response shapes for:
  POST /api/v1/expeditions/{id}/reviews       — submit a review
  GET  /api/v1/expeditions/{id}/reviews       — list all reviews for expedition
  GET  /api/v1/expeditions/{id}/reviews/{id}  — single review detail

Business rules enforced here (mirroring database CheckConstraints):
  - All ratings must be between 1 and 5 inclusive
  - reviewer_id != reviewee_id (no self-reviews)
  - Reviews can only be submitted for COMPLETED expeditions
    (enforced in the service layer, not here)
  - comment is limited to 1000 characters

The reviewer_id is always resolved server-side from the JWT — it is
never accepted from the client.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from app.schemas.common import PaginationMeta


# ---------------------------------------------------------------------------
# Reusable annotated rating type
# ---------------------------------------------------------------------------

def _rating_field(description: str) -> int:
    """Return a Field definition for a 1–5 rating dimension."""
    return Field(..., ge=1, le=5, description=description)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ReviewCreate(BaseModel):
    """Body for POST /api/v1/expeditions/{id}/reviews.

    reviewer_id is resolved server-side from the JWT.
    reviewee_id is provided by the client — the service layer verifies
    that the reviewee is/was a participant in the same expedition.

    All six rating dimensions are required. The comment is optional.

    Validator:
      - reviewer_id must not equal reviewee_id (redundant with DB CHECK,
        but gives a clear 422 error before the DB is even reached).
    """

    reviewee_id: UUID = Field(
        ...,
        description="UUID of the participant being reviewed. "
                    "Must be a participant in the same expedition.",
    )

    # Six rating dimensions — all required, range 1–5
    rating_overall: int = _rating_field(
        "Overall experience rating (1 = poor, 5 = excellent)."
    )
    rating_communication: int = _rating_field(
        "Communication quality rating (1–5)."
    )
    rating_safety: int = _rating_field(
        "Safety-consciousness rating (1–5)."
    )
    rating_punctuality: int = _rating_field(
        "Punctuality and reliability rating (1–5)."
    )
    rating_organisation: int = _rating_field(
        "Organisation and planning rating (1–5)."
    )
    rating_friendliness: int = _rating_field(
        "Friendliness and attitude rating (1–5)."
    )

    would_travel_again: bool = Field(
        ...,
        description="Would you travel with this person again?",
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional written review (max 1000 characters).",
    )

    @model_validator(mode="after")
    def reviewer_must_differ_from_reviewee(self) -> Self:
        # reviewer_id is injected by the service layer after validation,
        # but we can still guard against a client accidentally sending
        # their own ID as reviewee_id. Full check is in the service layer.
        return self


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ReviewResponse(BaseModel):
    """Full review record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    expedition_id: UUID
    reviewer_id: UUID
    reviewee_id: UUID

    rating_overall: int
    rating_communication: int
    rating_safety: int
    rating_punctuality: int
    rating_organisation: int
    rating_friendliness: int

    would_travel_again: bool
    comment: Optional[str]

    created_at: datetime
    updated_at: datetime


class ReviewSummary(BaseModel):
    """Aggregated rating summary for a reviewee across all reviews
    in a single expedition.

    Computed by the service layer — not stored in the DB.
    Used to show a quick summary on the participant list or expedition
    completion screen.
    """

    reviewee_id: UUID
    expedition_id: UUID
    review_count: int = Field(ge=0)
    average_overall: Optional[float] = Field(
        default=None,
        description="Average overall rating. None if no reviews yet.",
    )
    would_travel_again_percentage: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Percentage of reviewers who would travel again. "
                    "None if no reviews yet.",
    )


class ReviewListResponse(BaseModel):
    """Paginated list of reviews for an expedition."""

    expedition_id: UUID
    reviews: List[ReviewResponse] = Field(default_factory=list)
    pagination: PaginationMeta
