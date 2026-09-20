"""
GuideProfile Pydantic schemas.

Covers request/response shapes for:
  GET  /api/v1/guides             — list (uses GuideProfileSummary)
  GET  /api/v1/guides/{id}        — detail (uses GuideProfileResponse)
  PUT  /api/v1/guides/{id}        — update (uses GuideProfileUpdate)

Schema hierarchy:
  GuideProfileUpdate    — PUT body (all optional, server-controlled fields excluded)
  GuideProfileResponse  — full detail response
  GuideProfileSummary   — lightweight card response for list/directory

The user_id is never in a request body — always resolved server-side from JWT.
verification_status is never in an update body — it is controlled by the
  admin verification workflow, not direct client edits.
rating and review_count are computed/denormalised server-side — not updatable.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.guide_profile import VerificationStatus
from app.schemas.guide_location import GuideLocationResponse
from app.schemas.guide_language import GuideLanguageResponse
from app.schemas.guide_availability import GuideAvailabilityResponse
from app.schemas.guide_specialization import GuideSpecializationResponse


# ---------------------------------------------------------------------------
# Update — PUT /api/v1/guides/{id}
# ---------------------------------------------------------------------------

class GuideProfileUpdate(BaseModel):
    """Request body for updating a guide's own profile.

    All fields are optional.
    Excluded (server-controlled): user_id, verification_status, rating, review_count.
    Image URLs are accepted directly (MinIO upload handled separately).
    """

    bio: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Guide biography (max 2000 characters).",
    )
    profile_image_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="MinIO object URL for profile photo.",
    )
    cover_image_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="MinIO object URL for cover image.",
    )
    years_experience: Optional[int] = Field(
        default=None,
        ge=0,
        le=80,
        description="Self-reported years of guiding experience (0–80).",
    )
    price_per_day: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Guide's daily rate in USD.",
    )


# ---------------------------------------------------------------------------
# Response — GET /api/v1/guides/{id}
# ---------------------------------------------------------------------------

class GuideProfileResponse(BaseModel):
    """Full guide profile detail.

    Includes nested locations, languages, and availability for the
    detail view (Guide Portfolio / Guide Profile page).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID

    bio: Optional[str]
    profile_image_url: Optional[str]
    cover_image_url: Optional[str]
    years_experience: Optional[int]
    price_per_day: Optional[Decimal]

    rating: Optional[Decimal]
    review_count: int

    verification_status: VerificationStatus

    # Nested children — loaded for the detail view
    locations: List[GuideLocationResponse] = Field(default_factory=list)
    languages: List[GuideLanguageResponse] = Field(default_factory=list)
    availability: Optional[GuideAvailabilityResponse] = None
    specializations: List[GuideSpecializationResponse] = Field(default_factory=list)

    # Audit fields (from AuditMixin)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Summary — used in paginated directory listing
# ---------------------------------------------------------------------------

class GuideProfileSummary(BaseModel):
    """Lightweight guide card for the directory listing.

    Used in GET /api/v1/guides. Includes locations, languages, and
    availability so the frontend GuideCard can render location/language
    chips and the availability indicator without a second round-trip.

    display_name: a human-readable label for the card title.  When a
    user-service integration is in place this will be populated from the
    user record.  Until then it is None and the frontend falls back to a
    placeholder.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID

    display_name: Optional[str] = None

    bio: Optional[str]
    profile_image_url: Optional[str]
    years_experience: Optional[int]
    price_per_day: Optional[Decimal]

    rating: Optional[Decimal]
    review_count: int

    verification_status: VerificationStatus

    # Nested children — needed for card rendering and client-side search
    locations: List[GuideLocationResponse] = Field(default_factory=list)
    languages: List[GuideLanguageResponse] = Field(default_factory=list)
    availability: Optional[GuideAvailabilityResponse] = None
    specializations: List[GuideSpecializationResponse] = Field(default_factory=list)
