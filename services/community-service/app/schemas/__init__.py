"""
Community Service Schemas

Exports all Pydantic schemas for request/response handling.
"""

from .community import (
    # Community
    CommunityCreateRequest,
    CommunityUpdateRequest,
    CommunitySchema,
    CommunitySummarySchema,
    CommunityListResponse,
    CommunityQueryParams,
    # Media
    MediaUploadRequest,
    MediaUploadResponse,
    CommunityMediaSetRequest,
    # Membership
    MemberSchema,
    MemberRoleUpdateRequest,
    MemberListResponse,
    MemberQueryParams,
    # Join Requests
    JoinCommunityRequest,
    JoinRequestSchema,
    JoinRequestActionRequest,
    JoinRequestListResponse,
    # Rules
    CommunityRuleCreateRequest,
    CommunityRuleUpdateRequest,
    CommunityRuleSchema,
    CommunityRuleListResponse,
    # Discussions
    DiscussionCreateRequest,
    DiscussionUpdateRequest,
    DiscussionSchema,
    DiscussionSummarySchema,
    DiscussionListResponse,
    DiscussionQueryParams,
    # Discussion Comments
    DiscussionCommentCreateRequest,
    DiscussionCommentUpdateRequest,
    DiscussionCommentSchema,
    DiscussionCommentListResponse,
    CommentQueryParams,
)

__all__ = [
    "CommunityCreateRequest",
    "CommunityUpdateRequest",
    "CommunitySchema",
    "CommunitySummarySchema",
    "CommunityListResponse",
    "CommunityQueryParams",
    "MediaUploadRequest",
    "MediaUploadResponse",
    "CommunityMediaSetRequest",
    "MemberSchema",
    "MemberRoleUpdateRequest",
    "MemberListResponse",
    "MemberQueryParams",
    "JoinCommunityRequest",
    "JoinRequestSchema",
    "JoinRequestActionRequest",
    "JoinRequestListResponse",
    "CommunityRuleCreateRequest",
    "CommunityRuleUpdateRequest",
    "CommunityRuleSchema",
    "CommunityRuleListResponse",
    "DiscussionCreateRequest",
    "DiscussionUpdateRequest",
    "DiscussionSchema",
    "DiscussionSummarySchema",
    "DiscussionListResponse",
    "DiscussionQueryParams",
    "DiscussionCommentCreateRequest",
    "DiscussionCommentUpdateRequest",
    "DiscussionCommentSchema",
    "DiscussionCommentListResponse",
    "CommentQueryParams",
]
