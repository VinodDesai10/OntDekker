"""
Feed Service — Interaction API Routes

Endpoints for post interactions: likes, bookmarks, shares.
"""

import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import PostService
from app.schemas.feed import (
    LikeActionResponse,
    BookmarkActionResponse,
    ShareActionResponse,
    ShareRequest,
    BookmarkListResponse,
)
from shared.dependencies import get_db, get_current_user
from shared.exceptions import NotFoundError, ForbiddenError

router = APIRouter(prefix="/api/v1/feed", tags=["Interactions"])


def _user_id(payload: Dict[str, Any]) -> uuid.UUID:
    """Extract user UUID from JWT payload sub claim."""
    return uuid.UUID(payload["sub"])


# -------------------------------------------------------------------------
# Like Endpoints
# -------------------------------------------------------------------------

@router.post("/posts/{post_id}/like", response_model=LikeActionResponse)
async def like_post(
    post_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Like a post (idempotent)."""
    service = PostService(db)
    try:
        return await service.like_post(post_id, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/posts/{post_id}/like", response_model=LikeActionResponse)
async def unlike_post(
    post_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unlike a post (idempotent)."""
    service = PostService(db)
    return await service.unlike_post(post_id, _user_id(current_user))


# -------------------------------------------------------------------------
# Bookmark Endpoints
# -------------------------------------------------------------------------

@router.post("/posts/{post_id}/bookmark", response_model=BookmarkActionResponse)
async def bookmark_post(
    post_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bookmark a post (idempotent)."""
    service = PostService(db)
    try:
        return await service.bookmark_post(post_id, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/posts/{post_id}/bookmark", response_model=BookmarkActionResponse)
async def unbookmark_post(
    post_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove bookmark from a post (idempotent)."""
    service = PostService(db)
    return await service.unbookmark_post(post_id, _user_id(current_user))


@router.get("/me/bookmarks", response_model=BookmarkListResponse)
async def get_my_bookmarks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's bookmarked posts."""
    service = PostService(db)
    return await service.get_user_bookmarks(_user_id(current_user), limit, offset)


# -------------------------------------------------------------------------
# Share Endpoints
# -------------------------------------------------------------------------

@router.post("/posts/{post_id}/share", response_model=ShareActionResponse)
async def share_post(
    post_id: uuid.UUID,
    request: ShareRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Share a post (not idempotent — each share creates a new event record)."""
    service = PostService(db)
    try:
        return await service.share_post(post_id, _user_id(current_user), request)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
