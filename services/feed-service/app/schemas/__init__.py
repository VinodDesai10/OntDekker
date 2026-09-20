"""
Feed Service Schemas

Exports all Pydantic schemas for request/response validation and documentation.
"""

from .feed import (
    # Media schemas
    MediaUploadRequest,
    MediaUploadResponse,
    PostMediaSchema,
    PostMediaCreateRequest,
    
    # Tag schemas
    PostTagSchema,
    
    # Post schemas
    PostCreateRequest,
    PostUpdateRequest,
    PostSchema,
    PostSummarySchema,
    
    # Comment schemas
    CommentCreateRequest,
    CommentUpdateRequest,
    CommentSchema,
    
    # Interaction schemas
    LikeSchema,
    BookmarkSchema,
    ShareRequest,
    ShareSchema,
    
    # Query parameter schemas
    PostQueryParams,
    CommentQueryParams,
    
    # Response wrappers
    PostListResponse,
    CommentListResponse,
    BookmarkListResponse,
    
    # Action responses
    LikeActionResponse,
    BookmarkActionResponse,
    ShareActionResponse,
)

__all__ = [
    # Media
    "MediaUploadRequest",
    "MediaUploadResponse", 
    "PostMediaSchema",
    "PostMediaCreateRequest",
    
    # Tags
    "PostTagSchema",
    
    # Posts
    "PostCreateRequest",
    "PostUpdateRequest",
    "PostSchema",
    "PostSummarySchema",
    
    # Comments
    "CommentCreateRequest",
    "CommentUpdateRequest",
    "CommentSchema",
    
    # Interactions
    "LikeSchema",
    "BookmarkSchema", 
    "ShareRequest",
    "ShareSchema",
    
    # Query params
    "PostQueryParams",
    "CommentQueryParams",
    
    # Response lists
    "PostListResponse",
    "CommentListResponse",
    "BookmarkListResponse",
    
    # Action responses
    "LikeActionResponse",
    "BookmarkActionResponse",
    "ShareActionResponse",
]
