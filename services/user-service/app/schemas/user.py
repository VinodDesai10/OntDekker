"""
User Service — Pydantic Schemas

Request validation and response serialization for all User Service endpoints.

Security rules:
  - auth_user_id is NEVER in request bodies for current-user operations (derived from JWT)
  - password_hash and auth credentials are never in any response
  - email is NOT stored in user_db; it comes from the JWT payload when needed
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
import re

# ---------------------------------------------------------------------------
# Username validation
# Source: 09-backend-mapping.md — "Username regex: ^[a-zA-Z0-9_]{3,30}$"
# ---------------------------------------------------------------------------
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,30}$")

ALLOWED_ENTITY_TYPES = {"STORY", "COMMUNITY", "EXPEDITION", "GUIDE"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


# ===========================================================================
# Request Schemas
# ===========================================================================

class UpdateProfileRequest(BaseModel):
    """PUT /users/me — update editable profile fields."""

    username: Optional[str] = Field(None, min_length=3, max_length=30)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not USERNAME_REGEX.match(v):
            raise ValueError(
                "Username must be 3–30 characters and contain only letters, digits, and underscores."
            )
        return v


class UpdateInterestsRequest(BaseModel):
    """Replace the full list of interests for the current user."""
    interests: List[str] = Field(..., max_length=30)

    @field_validator("interests", mode="before")
    @classmethod
    def validate_interests(cls, v: List[str]) -> List[str]:
        cleaned = [i.strip() for i in v if i.strip()]
        if len(cleaned) != len(set(i.lower() for i in cleaned)):
            raise ValueError("Duplicate interests are not allowed.")
        return cleaned


class UpdatePreferencesRequest(BaseModel):
    """PATCH /users/me/preferences"""

    travel_style: Optional[str] = Field(None, max_length=50)
    budget: Optional[str] = Field(None, max_length=50)
    adventure_level: Optional[str] = Field(None, max_length=50)
    languages: Optional[List[str]] = None
    preferred_destinations: Optional[List[str]] = None
    notifications_enabled: Optional[bool] = None
    profile_public: Optional[bool] = None


class SaveItemRequest(BaseModel):
    """POST /users/me/saved"""

    entity_type: str = Field(..., description="One of: STORY, COMMUNITY, EXPEDITION, GUIDE")
    entity_id: uuid.UUID

    @field_validator("entity_type", mode="before")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in ALLOWED_ENTITY_TYPES:
            raise ValueError(f"entity_type must be one of: {', '.join(sorted(ALLOWED_ENTITY_TYPES))}")
        return v


class BatchProfilesRequest(BaseModel):
    """POST /users/batch-profiles — resolve display data for a list of user IDs."""
    user_ids: List[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="List of user profile IDs to resolve (max 200)",
    )


class BatchProfilesByAuthRequest(BaseModel):
    """POST /users/batch-profiles-by-auth — resolve profiles by auth-service UUIDs.

    Feed, community, and other services store the JWT sub claim (auth-service UUID)
    as their author/user reference.  This endpoint resolves those auth UUIDs to
    the real display identity (username, display_name, avatar_url).
    """
    auth_user_ids: List[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="List of auth-service user IDs (JWT sub) to resolve (max 200)",
    )


# ===========================================================================
# Response Schemas
# ===========================================================================

class InterestResponse(BaseModel):
    interest: str
    created_at: datetime
    model_config = {"from_attributes": True}


class PreferenceResponse(BaseModel):
    travel_style: Optional[str] = None
    budget: Optional[str] = None
    adventure_level: Optional[str] = None
    languages: Optional[List[str]] = None
    preferred_destinations: Optional[List[str]] = None
    notifications_enabled: bool = True
    profile_public: bool = True
    model_config = {"from_attributes": True}


class BadgeResponse(BaseModel):
    id: uuid.UUID
    badge_name: str
    badge_icon: Optional[str] = None
    earned_at: datetime
    model_config = {"from_attributes": True}


class ReputationResponse(BaseModel):
    explorer_score: int = 0
    community_score: int = 0
    review_score: int = 0
    expeditions_joined: int = 0
    expeditions_organized: int = 0
    guide_interactions: int = 0
    reviews_received: int = 0
    model_config = {"from_attributes": True}


class SavedItemResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    created_at: datetime
    model_config = {"from_attributes": True}


class PublicProfileResponse(BaseModel):
    """Returned for GET /users/{username} — public fields only.

    Viewer-specific fields (is_following, is_own_profile) default to False
    for unauthenticated viewers. They are populated by the service layer when
    a valid Bearer token is present in the request.

    is_own_profile: True when the authenticated viewer IS the profile owner.
                    When True, the frontend must suppress the Follow/Unfollow button.
    is_following:   True when the authenticated viewer already follows this profile.
                    Only meaningful when is_own_profile=False.
    """

    id: uuid.UUID
    username: str
    display_name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    cover_url: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    follower_count: int = 0
    following_count: int = 0
    badges: List[BadgeResponse] = []
    reputation: Optional[ReputationResponse] = None
    created_at: datetime
    # Viewer-context fields — safe defaults for unauthenticated access
    is_following: bool = False
    is_own_profile: bool = False
    model_config = {"from_attributes": True}


class PrivateProfileResponse(BaseModel):
    """Returned for GET /users/me — full profile including private fields."""

    id: uuid.UUID
    auth_user_id: uuid.UUID
    username: str
    display_name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    cover_url: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    follower_count: int = 0
    following_count: int = 0
    interests: List[InterestResponse] = []
    preferences: Optional[PreferenceResponse] = None
    badges: List[BadgeResponse] = []
    reputation: Optional[ReputationResponse] = None
    saved_items: List[SavedItemResponse] = []
    created_at: datetime
    model_config = {"from_attributes": True}


class FollowerSummary(BaseModel):
    """Minimal profile info returned in followers/following lists."""

    id: uuid.UUID
    username: str
    display_name: str
    avatar_url: Optional[str] = None
    model_config = {"from_attributes": True}


class BatchProfileSummary(BaseModel):
    """Minimal profile info for a single user — returned by batch-profiles."""

    id: uuid.UUID
    username: str
    display_name: str
    avatar_url: Optional[str] = None
    model_config = {"from_attributes": True}


class BatchProfilesResponse(BaseModel):
    """Response for POST /users/batch-profiles."""
    profiles: List[BatchProfileSummary]


class PaginatedFollowersResponse(BaseModel):
    items: List[FollowerSummary]
    total: int
    page: int
    size: int


class MediaUploadResponse(BaseModel):
    """Returned after avatar or cover image upload."""

    object_name: str
    presigned_url: str
    message: str


class MessageResponse(BaseModel):
    message: str
