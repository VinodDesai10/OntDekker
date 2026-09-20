"""
Guide Locations router — geographic coverage areas sub-resource.

Routes: /api/v1/guides/{guide_id}/locations

Endpoints:
  GET    /api/v1/guides/{guide_id}/locations              — list all locations
  POST   /api/v1/guides/{guide_id}/locations              — add a location
  DELETE /api/v1/guides/{guide_id}/locations/{location_id} — remove a location
"""

from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared.dependencies import get_current_user

from app.dependencies.guide_deps import get_guide_location_service
from app.schemas.guide_location import GuideLocationCreate, GuideLocationResponse
from app.services.guide_location_service import GuideLocationService

router = APIRouter(
    prefix="/api/v1/guides",
    tags=["Guide Locations"],
)


# ---------------------------------------------------------------------------
# GET /api/v1/guides/{guide_id}/locations
# ---------------------------------------------------------------------------

@router.get(
    "/{guide_id}/locations",
    response_model=List[GuideLocationResponse],
    status_code=status.HTTP_200_OK,
    summary="List guide locations",
    description="Returns all geographic coverage areas for a guide. Publicly readable.",
)
async def list_locations(
    guide_id: UUID,
    service: GuideLocationService = Depends(get_guide_location_service),
) -> List[GuideLocationResponse]:
    return await service.list_locations(guide_id)


# ---------------------------------------------------------------------------
# POST /api/v1/guides/{guide_id}/locations
# ---------------------------------------------------------------------------

@router.post(
    "/{guide_id}/locations",
    response_model=GuideLocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a coverage location",
    description=(
        "Adds a new geographic coverage area to the guide's profile. "
        "country is required; region and city are optional. "
        "Guide owner only. Maximum 20 locations per guide."
    ),
)
async def add_location(
    guide_id: UUID,
    payload: GuideLocationCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideLocationService = Depends(get_guide_location_service),
) -> GuideLocationResponse:
    user_id = UUID(current_user["sub"])
    return await service.add_location(guide_id, payload, user_id)


# ---------------------------------------------------------------------------
# DELETE /api/v1/guides/{guide_id}/locations/{location_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{guide_id}/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a coverage location",
    description="Removes a geographic coverage area. Guide owner only.",
)
async def delete_location(
    guide_id: UUID,
    location_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideLocationService = Depends(get_guide_location_service),
) -> None:
    user_id = UUID(current_user["sub"])
    await service.delete_location(guide_id, location_id, user_id)
