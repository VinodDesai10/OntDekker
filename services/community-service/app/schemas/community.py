"""
Community Service — Pydantic Schemas

Request and response schemas for all Community Service API endpoints.
Handles validation, serialization, and documentation.
"""

import re
import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

from shared.constants.status import (
    CommunityStatus,
    CommunityVisibility,
    MemberRole,
    MembershipStatus,
    JoinRequestStatus,
)


# ---------------------------------------------------------------------------
# Viewer membership status — single enum that powers all UI states
# ---------------------------------------------------------------------------

class MembershipViewStatus(str, Enum):
    """
    Represents the current authenticated user's relationship with a community.
    Returned as `membership_status` on CommunitySchema so the frontend can
    derive all join-button and permission UI from a single authoritative field
    without relying on ephemeral local state.
    """
    NOT_MEMBER = "NOT_MEMBER"
    PENDING    = "PENDING"     # has a pending join request
    MEMBER     = "MEMBER"      # active member (MEMBER role)
    CO_HEAD    = "CO_HEAD"     # MODERATOR role
    HEAD       = "HEAD"        # OWNER role


# ---------------------------------------------------------------------------
# Base Schemas
# ---------------------------------------------------------------------------

class TimestampSchema(BaseModel):
    created_at: datetime
    updated_at: datetime


class AuditSchema(TimestampSchema):
    created_by: Optional[uuid.UUID] = None
    updated_by: Optional[uuid.UUID] = None


# ---------------------------------------------------------------------------
# Community Schemas
# ---------------------------------------------------------------------------

class CommunityCreateRequest(BaseModel):
    """Request schema for creating a community"""
    name: str = Field(..., min_length=3, max_length=100, description="Community display name")
    description: Optional[str] = Field(None, max_length=2000)
    location: Optional[str] = Field(None, max_length=255)
    visibility: CommunityVisibility = Field(default=CommunityVisibility.PUBLIC)
    requires_approval: bool = Field(
        default=False,
        description="If True, new members must be approved before joining",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Community name must be at least 3 characters")
        return v


class CommunityUpdateRequest(BaseModel):
    """Request schema for updating a community"""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    location: Optional[str] = Field(None, max_length=255)
    visibility: Optional[CommunityVisibility] = None
    requires_approval: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) < 3:
                raise ValueError("Community name must be at least 3 characters")
        return v


class CommunitySchema(AuditSchema):
    """Full community schema with all details"""
    id: uuid.UUID
    creator_id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    location: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    status: CommunityStatus
    visibility: CommunityVisibility
    requires_approval: bool
    member_count: int = 0
    is_deleted: bool = False

    # Rules included in full community view
    rules: List["CommunityRuleSchema"] = Field(default_factory=list)

    # Viewer context (filled by service layer)
    current_user_role: Optional[MemberRole] = Field(
        None, description="Current user's role in this community (None if not a member)"
    )
    is_member: bool = Field(default=False)
    membership_status: MembershipViewStatus = Field(
        default=MembershipViewStatus.NOT_MEMBER,
        description="Current user's relationship with this community",
    )

    model_config = ConfigDict(from_attributes=True)


class CommunitySummarySchema(TimestampSchema):
    """Lightweight community schema for listing"""
    id: uuid.UUID
    creator_id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    location: Optional[str] = None
    logo_url: Optional[str] = None
    status: CommunityStatus
    visibility: CommunityVisibility
    requires_approval: bool
    member_count: int = 0
    is_member: bool = False

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Media Upload Schemas
# ---------------------------------------------------------------------------

class MediaUploadRequest(BaseModel):
    """Request schema for generating a presigned upload URL"""
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., description="MIME type (e.g., image/jpeg)")

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        allowed = ["image/jpeg", "image/png", "image/webp", "image/heic"]
        if v not in allowed:
            raise ValueError(f"Content type must be one of: {allowed}")
        return v


class MediaUploadResponse(BaseModel):
    """Response schema for presigned URL generation"""
    upload_url: str
    object_key: str
    expires_in: int = 3600


class CommunityMediaSetRequest(BaseModel):
    """Request to associate an uploaded object with community logo/banner"""
    object_key: str = Field(..., description="MinIO object key from upload response")


# ---------------------------------------------------------------------------
# Membership Schemas
# ---------------------------------------------------------------------------

class MemberSchema(TimestampSchema):
    """Schema for community member information"""
    id: uuid.UUID
    community_id: uuid.UUID
    user_id: uuid.UUID
    role: MemberRole
    status: MembershipStatus

    model_config = ConfigDict(from_attributes=True)


class MemberRoleUpdateRequest(BaseModel):
    """Request to update a member's role"""
    role: MemberRole = Field(..., description="New role for the member (MODERATOR or MEMBER)")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: MemberRole) -> MemberRole:
        # OWNER role cannot be assigned via this endpoint — use transfer ownership
        if v == MemberRole.OWNER:
            raise ValueError("Cannot assign OWNER role via this endpoint")
        return v


class MemberListResponse(BaseModel):
    """Response for member listing"""
    members: List[MemberSchema]
    total: int
    limit: int
    offset: int
    has_more: bool


# ---------------------------------------------------------------------------
# Join Request Schemas
# ---------------------------------------------------------------------------

class JoinCommunityRequest(BaseModel):
    """Request body when joining a community (public or requesting to join private)"""
    message: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional message explaining why the user wants to join",
    )


class JoinRequestSchema(AuditSchema):
    """Schema for a join request record"""
    id: uuid.UUID
    community_id: uuid.UUID
    requester_id: uuid.UUID
    message: Optional[str] = None
    status: JoinRequestStatus
    reviewed_by: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


class JoinRequestActionRequest(BaseModel):
    """Request to approve or reject a join request"""
    action: str = Field(..., description="'approve' or 'reject'")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v.lower() not in ("approve", "reject"):
            raise ValueError("action must be 'approve' or 'reject'")
        return v.lower()


class JoinRequestListResponse(BaseModel):
    """Response for pending join requests listing"""
    requests: List[JoinRequestSchema]
    total: int
    limit: int
    offset: int
    has_more: bool


# ---------------------------------------------------------------------------
# Community Rule Schemas
# ---------------------------------------------------------------------------

class CommunityRuleCreateRequest(BaseModel):
    """Request schema for adding a community rule"""
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    order_index: int = Field(default=1, ge=1, description="Display order (1-based, ascending)")


class CommunityRuleUpdateRequest(BaseModel):
    """Request schema for updating a community rule"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    order_index: Optional[int] = Field(None, ge=1)


class CommunityRuleSchema(AuditSchema):
    """Schema for a community rule"""
    id: uuid.UUID
    community_id: uuid.UUID
    title: str
    description: Optional[str] = None
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class CommunityRuleListResponse(BaseModel):
    """Response for community rules listing"""
    rules: List[CommunityRuleSchema]
    total: int


# ---------------------------------------------------------------------------
# Discussion Schemas
# ---------------------------------------------------------------------------

class DiscussionCreateRequest(BaseModel):
    """Request schema for creating a discussion"""
    title: str = Field(..., min_length=3, max_length=255)
    content: Optional[str] = Field(None, max_length=10000)


class DiscussionUpdateRequest(BaseModel):
    """Request schema for updating a discussion"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    content: Optional[str] = Field(None, max_length=10000)


class DiscussionSchema(AuditSchema):
    """Full discussion schema with comment count"""
    id: uuid.UUID
    community_id: uuid.UUID
    author_id: uuid.UUID
    title: str
    content: Optional[str] = None
    comment_count: int = 0
    is_deleted: bool = False

    model_config = ConfigDict(from_attributes=True)


class DiscussionSummarySchema(TimestampSchema):
    """Lightweight discussion for listing"""
    id: uuid.UUID
    community_id: uuid.UUID
    author_id: uuid.UUID
    title: str
    comment_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DiscussionListResponse(BaseModel):
    """Response for discussion listing"""
    discussions: List[DiscussionSummarySchema]
    total: int
    limit: int
    offset: int
    has_more: bool


# ---------------------------------------------------------------------------
# Discussion Comment Schemas
# ---------------------------------------------------------------------------

class DiscussionCommentCreateRequest(BaseModel):
    """Request schema for adding a comment to a discussion"""
    content: str = Field(..., min_length=1, max_length=2000)


class DiscussionCommentUpdateRequest(BaseModel):
    """Request schema for updating a discussion comment"""
    content: str = Field(..., min_length=1, max_length=2000)


class DiscussionCommentSchema(TimestampSchema):
    """Schema for a discussion comment"""
    id: uuid.UUID
    discussion_id: uuid.UUID
    author_id: uuid.UUID
    content: str
    is_deleted: bool = False

    model_config = ConfigDict(from_attributes=True)


class DiscussionCommentListResponse(BaseModel):
    """Response for discussion comment listing"""
    comments: List[DiscussionCommentSchema]
    total: int
    limit: int
    offset: int
    has_more: bool


# ---------------------------------------------------------------------------
# Query Parameter Schemas
# ---------------------------------------------------------------------------

class CommunityQueryParams(BaseModel):
    """Query parameters for community listing"""
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    location: Optional[str] = Field(None, description="Filter by location (partial match)")
    visibility: Optional[CommunityVisibility] = Field(None, description="Filter by visibility")
    search: Optional[str] = Field(None, max_length=100, description="Search by name")


class DiscussionQueryParams(BaseModel):
    """Query parameters for discussion listing"""
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class CommentQueryParams(BaseModel):
    """Query parameters for comment listing"""
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class MemberQueryParams(BaseModel):
    """Query parameters for member listing"""
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    role: Optional[MemberRole] = Field(None, description="Filter by role")


# ---------------------------------------------------------------------------
# Community List Response
# ---------------------------------------------------------------------------

class CommunityListResponse(BaseModel):
    """Response for community listing"""
    communities: List[CommunitySummarySchema]
    total: int
    limit: int
    offset: int
    has_more: bool


# Enable forward references
CommunitySchema.model_rebuild()
