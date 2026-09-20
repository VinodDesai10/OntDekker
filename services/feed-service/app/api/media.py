"""
Feed Service — Media API Routes

Endpoints for post media upload URL generation and metadata persistence.
"""

import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import MediaService
from app.schemas.feed import (
    MediaUploadRequest,
    MediaUploadResponse,
    PostMediaCreateRequest,
    PostMediaSchema,
)
from shared.dependencies import get_db, get_current_user
from shared.exceptions import NotFoundError, ValidationError, ForbiddenError

router = APIRouter(prefix="/api/v1/feed", tags=["Media"])


def _user_id(payload: Dict[str, Any]) -> uuid.UUID:
    """Extract user UUID from JWT payload sub claim."""
    return uuid.UUID(payload["sub"])


# -------------------------------------------------------------------------
# Media Upload Endpoints
# -------------------------------------------------------------------------

@router.post("/posts/{post_id}/media/upload-url", response_model=MediaUploadResponse)
async def generate_media_upload_url(
    post_id: uuid.UUID,
    request: MediaUploadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a presigned PUT URL for uploading media to a post.

    Steps:
    1. Call this endpoint to get an upload URL and object_key.
    2. PUT the image binary directly to the returned `upload_url`.
    3. Call POST /posts/{post_id}/media with the `object_key` to persist.

    Post author only.
    """
    service = MediaService(db)
    try:
        return await service.generate_upload_url(post_id, request, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/posts/{post_id}/media",
    response_model=PostMediaSchema,
    status_code=status.HTTP_201_CREATED,
)
async def associate_media_with_post(
    post_id: uuid.UUID,
    request: PostMediaCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Persist media metadata after the client has uploaded the binary to MinIO.

    Post author only.
    """
    service = MediaService(db)
    try:
        media = await service.associate_media_with_post(post_id, request, _user_id(current_user))
        if not media:
            raise HTTPException(status_code=400, detail="Failed to associate media")
        return PostMediaSchema.model_validate(media)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/posts/{post_id}/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_media_from_post(
    post_id: uuid.UUID,
    media_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove media from a post (post author only)."""
    from app.repositories import PostRepository

    post_repo = PostRepository(db)
    post = await post_repo.get_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.author_id != _user_id(current_user):
        raise HTTPException(status_code=403, detail="You can only remove media from your own posts")

    success = await post_repo.remove_media(post_id, media_id)
    if not success:
        raise HTTPException(status_code=404, detail="Media not found")
