"""
Discussion router — /api/v1/trips/{trip_id}/discussion endpoints.

Provides the discussion API surface for expedition members:
  GET  /api/v1/trips/{trip_id}/discussion  — list messages (paginated)
  POST /api/v1/trips/{trip_id}/discussion  — post a new message

Security:
  - Both endpoints require a valid Bearer token (get_current_user).
  - POST additionally enforces active expedition membership at the
    service layer (ForbiddenException for non-members).

Author identity:
  - author_id is NEVER accepted from the request body.
  - The server always derives author_id from the JWT sub claim.
"""

from __future__ import annotations

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from shared.dependencies import get_current_user

from app.dependencies.expedition_deps import get_discussion_service
from app.schemas.discussion import (
    DiscussionListResponse,
    DiscussionMessageCreate,
    DiscussionMessageResponse,
)
from app.services.discussion_service import DiscussionService

router = APIRouter(tags=["Discussion"])


# ---------------------------------------------------------------------------
# GET /api/v1/trips/{trip_id}/discussion
# ---------------------------------------------------------------------------

@router.get(
    "/api/v1/trips/{trip_id}/discussion",
    response_model=DiscussionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List expedition discussion messages",
    description=(
        "Returns all discussion messages for the specified trip, "
        "ordered oldest → newest. Requires authentication."
    ),
)
async def list_discussion(
    trip_id: UUID,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)."),
    page_size: int = Query(
        default=50,
        ge=1,
        le=100,
        alias="pageSize",
        description="Messages per page (max 100).",
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: DiscussionService = Depends(get_discussion_service),
) -> DiscussionListResponse:
    return await service.list_messages(
        trip_id,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/trips/{trip_id}/discussion
# ---------------------------------------------------------------------------

@router.post(
    "/api/v1/trips/{trip_id}/discussion",
    response_model=DiscussionMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post a discussion message",
    description=(
        "Creates a new discussion message in the specified trip. "
        "The caller must be an active participant or organizer. "
        "author_id is always derived from the JWT — never from the request body."
    ),
)
async def post_discussion_message(
    trip_id: UUID,
    payload: DiscussionMessageCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: DiscussionService = Depends(get_discussion_service),
) -> DiscussionMessageResponse:
    user_id = UUID(current_user["sub"])
    return await service.create_message(trip_id, payload, user_id)
