"""
Feed Service — Pydantic Schemas

Request and response schemas for all Feed Service API endpoints.
Handles validation, serialization, and documentation.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum

from shared.constants.status import PostStatus, PostVisibility, MediaType


# -------------------------------------------------------------------------
# Base Schemas
# -------------------------------------------------------------------------

class TimestampSchema(BaseModel):
    """Base schema with timestamp fields"""
    created_at: datetime
    updated_at: datetime


class AuditSchema(TimestampSchema):
    """Base schema with audit fields"""
    created_by: Optional[uuid.UUID] = None
    updated_by: Optional[uuid.UUID] = None


# -------------------------------------------------------------------------
# Media Schemas
# -------------------------------------------------------------------------

class MediaUploadRequest(BaseModel):
    """Request schema for generating media upload URL"""
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    content_type: str = Field(..., description="MIME type (e.g., image/jpeg)")
    
    @field_validator('content_type')
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/heic']
        if v not in allowed_types:
            raise ValueError(f'Content type must be one of: {allowed_types}')
        return v


class MediaUploadResponse(BaseModel):
    """Response schema for media upload URL generation"""
    upload_url: str = Field(..., description="Presigned URL for direct upload")
    object_key: str = Field(..., description="MinIO object key for later reference")
    expires_in: int = Field(default=3600, description="URL expiration time in seconds")


class PostMediaSchema(AuditSchema):
    """Schema for post media metadata"""
    id: uuid.UUID
    post_id: uuid.UUID
    media_url: str
    object_key: str
    media_type: str = MediaType.IMAGE
    display_order: int = Field(ge=0, description="Display order (0 = cover image)")
    alt_text: Optional[str] = Field(None, max_length=255)

    model_config = ConfigDict(from_attributes=True)


class PostMediaCreateRequest(BaseModel):
    """Request schema for associating uploaded media with a post"""
    object_key: str = Field(..., description="MinIO object key from upload response")
    display_order: int = Field(ge=0, description="Display order within post")
    alt_text: Optional[str] = Field(None, max_length=255)


# -------------------------------------------------------------------------
# Tag Schemas  
# -------------------------------------------------------------------------

class PostTagSchema(BaseModel):
    """Schema for post tags"""
    id: uuid.UUID
    post_id: uuid.UUID
    tag: str = Field(..., min_length=1, max_length=50)

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------------------
# Post Schemas
# -------------------------------------------------------------------------

class PostCreateRequest(BaseModel):
    """Request schema for creating a new post"""
    title: str = Field(..., min_length=1, max_length=255)
    content: Optional[str] = Field(None, max_length=10000)
    location: Optional[str] = Field(None, max_length=255)
    community_id: Optional[uuid.UUID] = None
    expedition_id: Optional[uuid.UUID] = None
    tags: List[str] = Field(default_factory=list, max_length=10, description="Max 10 tags")
    visibility: PostVisibility = Field(default=PostVisibility.PUBLIC)
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        # Clean and validate tags
        clean_tags = []
        for tag in v:
            clean_tag = tag.strip().lower()
            if len(clean_tag) < 1 or len(clean_tag) > 50:
                raise ValueError(f'Tag "{tag}" must be 1-50 characters')
            if clean_tag not in clean_tags:  # Remove duplicates
                clean_tags.append(clean_tag)
        return clean_tags


class PostUpdateRequest(BaseModel):
    """Request schema for updating a post"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, max_length=10000)
    location: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = Field(None, max_length=10)
    visibility: Optional[PostVisibility] = None
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        clean_tags = []
        for tag in v:
            clean_tag = tag.strip().lower()
            if len(clean_tag) < 1 or len(clean_tag) > 50:
                raise ValueError(f'Tag "{tag}" must be 1-50 characters')
            if clean_tag not in clean_tags:
                clean_tags.append(clean_tag)
        return clean_tags


class PostSchema(AuditSchema):
    """Complete post schema with relationships"""
    id: uuid.UUID
    author_id: uuid.UUID
    community_id: Optional[uuid.UUID] = None
    expedition_id: Optional[uuid.UUID] = None
    title: str
    content: Optional[str] = None
    location: Optional[str] = None
    status: PostStatus
    visibility: PostVisibility
    is_deleted: bool = False
    
    # Relationships
    media: List[PostMediaSchema] = Field(default_factory=list)
    tags: List[PostTagSchema] = Field(default_factory=list)
    
    # Computed fields (filled by service layer)
    like_count: int = Field(default=0, description="Total number of likes")
    comment_count: int = Field(default=0, description="Total number of comments")
    share_count: int = Field(default=0, description="Total number of shares")
    is_liked: bool = Field(default=False, description="True if current user liked this post")
    is_bookmarked: bool = Field(default=False, description="True if current user bookmarked this post")

    model_config = ConfigDict(from_attributes=True)


class PostSummarySchema(TimestampSchema):
    """Lightweight post schema for lists and feeds"""
    id: uuid.UUID
    author_id: uuid.UUID
    community_id: Optional[uuid.UUID] = None
    title: str
    location: Optional[str] = None
    status: PostStatus
    visibility: PostVisibility
    
    # First media item (cover image)
    cover_image_url: Optional[str] = None
    
    # Tag strings only
    tag_list: List[str] = Field(default_factory=list)
    
    # Interaction counts
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    is_liked: bool = False
    is_bookmarked: bool = False

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------------------
# Comment Schemas
# -------------------------------------------------------------------------

class CommentCreateRequest(BaseModel):
    """Request schema for creating a comment"""
    content: str = Field(..., min_length=1, max_length=1000)
    parent_comment_id: Optional[uuid.UUID] = None


class CommentUpdateRequest(BaseModel):
    """Request schema for updating a comment"""
    content: str = Field(..., min_length=1, max_length=1000)


class CommentSchema(TimestampSchema):
    """Schema for comments with basic info"""
    id: uuid.UUID
    post_id: uuid.UUID
    author_id: uuid.UUID
    parent_comment_id: Optional[uuid.UUID] = None
    content: str
    is_deleted: bool = False
    
    # Nested replies (one level only)
    replies: List['CommentSchema'] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------------------
# Interaction Schemas
# -------------------------------------------------------------------------

class LikeSchema(TimestampSchema):
    """Schema for likes"""
    id: uuid.UUID
    post_id: uuid.UUID
    user_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class BookmarkSchema(TimestampSchema):
    """Schema for bookmarks"""
    id: uuid.UUID
    post_id: uuid.UUID
    user_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class ShareRequest(BaseModel):
    """Request schema for sharing a post"""
    share_channel: Optional[str] = Field(None, max_length=50, description="Platform where shared (optional)")


class ShareSchema(TimestampSchema):
    """Schema for shares"""
    id: uuid.UUID
    post_id: uuid.UUID
    user_id: uuid.UUID
    share_channel: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------------------
# Query Parameter Schemas
# -------------------------------------------------------------------------

class PostQueryParams(BaseModel):
    """Query parameters for post listing endpoints"""
    limit: int = Field(default=20, ge=1, le=100, description="Number of posts to return")
    offset: int = Field(default=0, ge=0, description="Number of posts to skip")
    author_id: Optional[uuid.UUID] = Field(None, description="Filter by author")
    exclude_author_id: Optional[uuid.UUID] = Field(None, description="Exclude posts by this author (used for own-post exclusion in main feed)")
    community_id: Optional[uuid.UUID] = Field(None, description="Filter by community")
    expedition_id: Optional[uuid.UUID] = Field(None, description="Filter by expedition")
    tags: Optional[str] = Field(None, description="Comma-separated list of tags to filter by")
    location: Optional[str] = Field(None, description="Filter by location (partial match)")
    status: Optional[PostStatus] = Field(None, description="Filter by status")
    visibility: Optional[PostVisibility] = Field(None, description="Filter by visibility")
    since: Optional[datetime] = Field(None, description="Return posts created after this date")
    until: Optional[datetime] = Field(None, description="Return posts created before this date")
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Validate that it's a reasonable tag filter
        tags = [tag.strip() for tag in v.split(',') if tag.strip()]
        if len(tags) > 10:
            raise ValueError('Cannot filter by more than 10 tags')
        return ','.join(tags)


class CommentQueryParams(BaseModel):
    """Query parameters for comment listing"""
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    include_replies: bool = Field(default=True, description="Whether to include nested replies")


# -------------------------------------------------------------------------
# Response Wrappers
# -------------------------------------------------------------------------

class PostListResponse(BaseModel):
    """Response schema for post listing endpoints"""
    posts: List[PostSummarySchema]
    total: int = Field(..., description="Total number of posts matching criteria")
    limit: int
    offset: int
    has_more: bool = Field(..., description="True if there are more posts beyond this page")


class CommentListResponse(BaseModel):
    """Response schema for comment listing"""
    comments: List[CommentSchema]
    total: int
    limit: int
    offset: int
    has_more: bool


class BookmarkListResponse(BaseModel):
    """Response schema for user's bookmarked posts"""
    bookmarks: List[PostSummarySchema]  # Posts that are bookmarked
    total: int
    limit: int
    offset: int
    has_more: bool


# -------------------------------------------------------------------------
# Action Response Schemas
# -------------------------------------------------------------------------

class LikeActionResponse(BaseModel):
    """Response for like/unlike actions"""
    post_id: uuid.UUID
    is_liked: bool = Field(..., description="True if post is now liked, False if unliked")
    like_count: int = Field(..., description="Updated total like count")


class BookmarkActionResponse(BaseModel):
    """Response for bookmark/unbookmark actions"""
    post_id: uuid.UUID
    is_bookmarked: bool = Field(..., description="True if post is now bookmarked, False if removed")


class ShareActionResponse(BaseModel):
    """Response for share action"""
    post_id: uuid.UUID
    share_count: int = Field(..., description="Updated total share count")
    share_id: uuid.UUID = Field(..., description="ID of the created share record")


# Enable forward references for recursive CommentSchema
CommentSchema.model_rebuild()