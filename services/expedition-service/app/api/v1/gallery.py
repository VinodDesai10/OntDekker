"""
Gallery router — sub-resource under /api/v1/expeditions/{expedition_id}
"""

from __future__ import annotations

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared.dependencies import get_current_user

from app.dependencies.expedition_deps import get_gallery_service
from app.schemas.gallery import (
    GalleryPhotoCreate,
    GalleryPhotoResponse,
    GalleryPhotoUpdate,
    GalleryResponse,
)
from app.services.gallery_service import GalleryService

router = APIRouter(
    prefix="/api/v1/expeditions",
    tags=["Gallery"],
)


@router.get(
    "/{expedition_id}/gallery",
    response_model=GalleryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get expedition gallery",
    description="Returns all photos ordered by display_order. Participants only.",
)
async def get_gallery(
    expedition_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GalleryService = Depends(get_gallery_service),
) -> GalleryResponse:
    current_user_id = UUID(current_user["sub"])
    return await service.get_gallery(expedition_id, current_user_id)


@router.post(
    "/{expedition_id}/gallery",
    response_model=GalleryPhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a photo to the gallery",
    description=(
        "Registers a MinIO object URL as a gallery photo. "
        "Upload the binary to MinIO first, then call this endpoint with the URL. "
        "Active participants only."
    ),
)
async def add_photo(
    expedition_id: UUID,
    payload: GalleryPhotoCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GalleryService = Depends(get_gallery_service),
) -> GalleryPhotoResponse:
    current_user_id = UUID(current_user["sub"])
    return await service.add_photo(expedition_id, payload, current_user_id)


@router.patch(
    "/{expedition_id}/gallery/{photo_id}",
    response_model=GalleryPhotoResponse,
    status_code=status.HTTP_200_OK,
    summary="Update photo caption or display order",
    description="Uploader or organiser/co-organiser only.",
)
async def update_photo(
    expedition_id: UUID,
    photo_id: UUID,
    payload: GalleryPhotoUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GalleryService = Depends(get_gallery_service),
) -> GalleryPhotoResponse:
    current_user_id = UUID(current_user["sub"])
    return await service.update_photo(expedition_id, photo_id, payload, current_user_id)


@router.delete(
    "/{expedition_id}/gallery/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a gallery photo",
    description="Uploader or organiser/co-organiser only.",
)
async def delete_photo(
    expedition_id: UUID,
    photo_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GalleryService = Depends(get_gallery_service),
) -> None:
    current_user_id = UUID(current_user["sub"])
    await service.delete_photo(expedition_id, photo_id, current_user_id)
