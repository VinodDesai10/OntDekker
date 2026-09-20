"""
GuideReview Pydantic schemas.

Covers request/response shapes for:
  POST /api/v1/guides/{id}/reviews  — submit a review (GuideReviewCreate)
  GET  /api/v1/guides/{id}/reviews  — list reviews (GuideReviewResponse)

Business rules enforced here:
  - All six ratings must be between 1 and 5 inclusive
  - reviewer_id is always resolved server-side from JWT, never from the body
  - expedition_id is optional (a traveler may review a guide they met
    outside a formal expedition)
  - comment is limited to 1000 characters

The guide's rolling average rating and review_count are updated by the
service layer after a review is submitted — not computed here.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


# ---------------------------------------------------------------------------
# Rating field helper
# ---------------------------------------------------------------------------

def _rating_field(description: str) -> int:
    """Return a Field definition for a 1–5 rating dimension."""
    return Field(..., ge=1, le=5, description=description)


# ---------------------------------------------------------------------------
# Create — POST /api/v1/guides/{id}/reviews
# ---------------------------------------------------------------------------

class GuideReviewCreate(BaseModel):
    """Request body for submitting a guide review.

    reviewer_id is resolved server-side from the JWT.
    guide_id is taken from the URL path parameter.

    expedition_id is optional — a traveler can review a guide they
    connected with outside a formal expedition.
    """

    expedition_id: Optional[UUID] = Field(
        default=None,
        description="UUID of the expedition during which this review was earned. "
                    "Optional — omit for guides met outside formal expeditions.",
    )

    # Six rating dimensions — all required
    rating_overall: int = _rating_field(
        "Overall experience rating (1 = poor, 5 = excellent)."
    )
    rating_knowledge: int = _rating_field(
        "Local knowledge and expertise rating (1–5)."
    )
    rating_friendliness: int = _rating_field(
        "Friendliness and approachability rating (1–5)."
    )
    rating_communication: int = _rating_field(
        "Communication quality rating (1–5)."
    )
    rating_safety: int = _rating_field(
        "Safety-consciousness rating (1–5)."
    )
    rating_professionalism: int = _rating_field(
        "Professionalism and reliability rating (1–5)."
    )

    would_recommend: bool = Field(
        ...,
        description="Would you recommend this guide to other travelers?",
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional written review (max 1000 characters).",
    )


# ---------------------------------------------------------------------------
# Response — single review
# ---------------------------------------------------------------------------

class GuideReviewResponse(BaseModel):
    """Full guide review record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    guide_id: UUID
    reviewer_id: UUID
    expedition_id: Optional[UUID]

    rating_overall: int
    rating_knowledge: int
    rating_friendliness: int
    rating_communication: int
    rating_safety: int
    rating_professionalism: int

    would_recommend: bool
    comment: Optional[str]

    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Rating summary — aggregate view for a guide's public profile
# ---------------------------------------------------------------------------

class GuideRatingSummary(BaseModel):
    """Aggregated rating summary for a guide's public profile.

    Computed by the service layer — not stored directly in the database.
    The individual averages are derived from guide_reviews rows;
    the overall rating and review_count are the denormalised values
    on guide_profiles (kept in sync after each review).
    """

    guide_id: UUID
    review_count: int = Field(ge=0)
    average_overall: Optional[Decimal] = Field(
        default=None,
        description="Rounded average overall rating. None if no reviews yet.",
    )
    average_knowledge: Optional[Decimal] = None
    average_friendliness: Optional[Decimal] = None
    average_communication: Optional[Decimal] = None
    average_safety: Optional[Decimal] = None
    average_professionalism: Optional[Decimal] = None
    would_recommend_percentage: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Percentage of reviewers who would recommend this guide.",
    )


# ---------------------------------------------------------------------------
# List response
# ---------------------------------------------------------------------------

class GuideReviewListResponse(BaseModel):
    """Paginated list of reviews for a guide.

    Uses `items` (matching PaginatedResponse convention) so the frontend
    can consume this with the same `data?.items ?? []` pattern.
    `guide_id` is included for cache-key convenience on the client.
    """

    guide_id: UUID
    items: List[GuideReviewResponse] = Field(default_factory=list)
    pagination: PaginationMeta
