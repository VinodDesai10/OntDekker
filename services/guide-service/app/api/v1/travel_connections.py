"""
Travel Connections router — My Guides and bookmark endpoints.

Endpoints:
  GET  /api/v1/guides/my-connections           — traveler's previously connected guides
  POST /api/v1/guides/{guide_id}/bookmark      — bookmark a guide
  DELETE /api/v1/guides/{guide_id}/bookmark    — remove bookmark
"""

from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from shared.dependencies import get_current_user

from app.dependencies.guide_deps import get_travel_connection_service
from app.schemas.travel_connection import TravelConnectionListResponse
from app.services.travel_connection_service import TravelConnectionService

router = APIRouter(
    prefix="/api/v1/guides",
    tags=["Travel Connections"],
)


@router.get(
    "/my-connections",
    response_model=TravelConnectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="My Guides — list previous guide connections",
    description=(
        "Returns a paginated list of guides the current traveler has previously "
        "connected with. Optionally filter to bookmarked guides only."
    ),
)
async def list_my_connections(
    bookmarked_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: TravelConnectionService = Depends(get_travel_connection_service),
) -> TravelConnectionListResponse:
    traveler_id = UUID(current_user["sub"])
    return await service.list_my_connections(
        traveler_id,
        bookmarked_only=bookmarked_only,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{guide_id}/bookmark",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bookmark a guide",
    description=(
        "Bookmarks a guide for quick access in My Guides. "
        "Creates a connection record if one does not yet exist."
    ),
)
async def bookmark_guide(
    guide_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: TravelConnectionService = Depends(get_travel_connection_service),
) -> None:
    traveler_id = UUID(current_user["sub"])
    await service.set_bookmark(guide_id, traveler_id, bookmarked=True)


@router.delete(
    "/{guide_id}/bookmark",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove guide bookmark",
    description="Removes the bookmark from a guide connection.",
)
async def unbookmark_guide(
    guide_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: TravelConnectionService = Depends(get_travel_connection_service),
) -> None:
    traveler_id = UUID(current_user["sub"])
    await service.set_bookmark(guide_id, traveler_id, bookmarked=False)
