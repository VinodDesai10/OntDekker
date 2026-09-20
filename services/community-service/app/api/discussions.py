"""
Community Service — Discussion & Comment API Endpoints

Routes for discussion thread and comment management.
All paths are prefixed by /api/v1/communities in routes.py.
"""

import uuid
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import DiscussionService
from app.schemas.community import (
    DiscussionCreateRequest,
    DiscussionUpdateRequest,
    DiscussionSchema,
    DiscussionListResponse,
    DiscussionCommentCreateRequest,
    DiscussionCommentUpdateRequest,
    DiscussionCommentSchema,
    DiscussionCommentListResponse,
    DiscussionQueryParams,
    CommentQueryParams,
)
from shared.dependencies import get_current_user, optional_current_user, get_db
from shared.exceptions import NotFoundError, ForbiddenError, ValidationError

router = APIRouter(tags=["Discussions"])


def _user_id(payload: Dict[str, Any]) -> uuid.UUID:
    return uuid.UUID(payload["sub"])


# ---------------------------------------------------------------------------
# Discussion CRUD
# ---------------------------------------------------------------------------

@router.get("/{community_id}/discussions", response_model=DiscussionListResponse)
async def list_discussions(
    community_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List discussions for a community."""
    params = DiscussionQueryParams(limit=limit, offset=offset)
    service = DiscussionService(db)
    try:
        user_id = _user_id(current_user) if current_user else None
        return await service.list_discussions(community_id, params, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post(
    "/{community_id}/discussions",
    response_model=DiscussionSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_discussion(
    community_id: uuid.UUID,
    request: DiscussionCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new discussion thread — active members only."""
    service = DiscussionService(db)
    try:
        return await service.create_discussion(community_id, request, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/discussions/{discussion_id}", response_model=DiscussionSchema)
async def get_discussion(
    discussion_id: uuid.UUID,
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a discussion by ID."""
    service = DiscussionService(db)
    try:
        user_id = _user_id(current_user) if current_user else None
        return await service.get_discussion(discussion_id, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/discussions/{discussion_id}", response_model=DiscussionSchema)
async def update_discussion(
    discussion_id: uuid.UUID,
    request: DiscussionUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a discussion — author, MOD, or OWNER."""
    service = DiscussionService(db)
    try:
        return await service.update_discussion(discussion_id, request, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/discussions/{discussion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_discussion(
    discussion_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a discussion — author, MOD, or OWNER."""
    service = DiscussionService(db)
    try:
        success = await service.delete_discussion(discussion_id, _user_id(current_user))
        if not success:
            raise HTTPException(status_code=404, detail="Discussion not found")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ---------------------------------------------------------------------------
# Discussion Comments
# ---------------------------------------------------------------------------

@router.post(
    "/discussions/{discussion_id}/comments",
    response_model=DiscussionCommentSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    discussion_id: uuid.UUID,
    request: DiscussionCommentCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a discussion — active members only."""
    service = DiscussionService(db)
    try:
        return await service.create_comment(discussion_id, request, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/discussions/{discussion_id}/comments",
    response_model=DiscussionCommentListResponse,
)
async def list_comments(
    discussion_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List comments for a discussion."""
    params = CommentQueryParams(limit=limit, offset=offset)
    service = DiscussionService(db)
    try:
        user_id = _user_id(current_user) if current_user else None
        return await service.list_comments(discussion_id, params, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put(
    "/discussions/comments/{comment_id}",
    response_model=DiscussionCommentSchema,
)
async def update_comment(
    comment_id: uuid.UUID,
    request: DiscussionCommentUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a comment — author, MOD, or OWNER."""
    service = DiscussionService(db)
    try:
        return await service.update_comment(comment_id, request, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/discussions/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    comment_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a comment — author, MOD, or OWNER."""
    service = DiscussionService(db)
    try:
        success = await service.delete_comment(comment_id, _user_id(current_user))
        if not success:
            raise HTTPException(status_code=404, detail="Comment not found")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
