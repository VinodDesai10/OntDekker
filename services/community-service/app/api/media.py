"""
Community Service — Media API Endpoints

Routes for community logo and banner upload URL generation and persistence.
All paths are prefixed by /api/v1/communities in routes.py.
"""

import uuid
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import MediaService
from app.schemas.community import (
    MediaUploadRequest,
    MediaUploadResponse,
    CommunityMediaSetRequest,
    CommunitySchema,
)
from shared.dependencies import get_current_user, get_db
from shared.exceptions import NotFoundError, ForbiddenError, ValidationError

router = APIRouter(tags=["Community Media"])


def _user_id(payload: Dict[str, Any]) -> uuid.UUID:
    return uuid.UUID(payload["sub"])


# ---------------------------------------------------------------------------
# Logo
# ---------------------------------------------------------------------------

@router.post("/{community_id}/logo/upload-url", response_model=MediaUploadResponse)
async def get_logo_upload_url(
    community_id: uuid.UUID,
    request: MediaUploadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a presigned PUT URL for uploading a community logo.

    Steps:
    1. Call this endpoint to get an upload URL and object_key.
    2. PUT the image binary directly to the returned `upload_url`.
    3. Call PUT /communities/{id}/logo with the `object_key` to persist.

    OWNER only.
    """
    service = MediaService(db)
    try:
        return await service.generate_logo_upload_url(
            community_id, request, _user_id(current_user)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{community_id}/logo", response_model=CommunitySchema)
async def set_community_logo(
    community_id: uuid.UUID,
    request: CommunityMediaSetRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Persist a community logo after the client has uploaded the binary to MinIO.

    OWNER only.
    """
    service = MediaService(db)
    try:
        return await service.set_community_logo(
            community_id, request, _user_id(current_user)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

@router.post("/{community_id}/banner/upload-url", response_model=MediaUploadResponse)
async def get_banner_upload_url(
    community_id: uuid.UUID,
    request: MediaUploadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a presigned PUT URL for uploading a community banner.

    OWNER only.
    """
    service = MediaService(db)
    try:
        return await service.generate_banner_upload_url(
            community_id, request, _user_id(current_user)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{community_id}/banner", response_model=CommunitySchema)
async def set_community_banner(
    community_id: uuid.UUID,
    request: CommunityMediaSetRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Persist a community banner after the client has uploaded the binary to MinIO.

    OWNER only.
    """
    service = MediaService(db)
    try:
        return await service.set_community_banner(
            community_id, request, _user_id(current_user)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
