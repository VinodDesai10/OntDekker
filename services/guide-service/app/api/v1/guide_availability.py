"""
Guide Availability router — one-to-one availability sub-resource.

Routes: /api/v1/guides/{guide_id}/availability

Endpoints:
  GET /api/v1/guides/{guide_id}/availability — get current availability
  PUT /api/v1/guides/{guide_id}/availability — set/update availability (upsert)
"""

from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared.dependencies import get_current_user

from app.dependencies.guide_deps import get_guide_availability_service
from app.schemas.guide_availability import GuideAvailabilityResponse, GuideAvailabilityUpdate
from app.services.guide_availability_service import GuideAvailabilityService

router = APIRouter(
    prefix="/api/v1/guides",
    tags=["Guide Availability"],
)


# ---------------------------------------------------------------------------
# GET /api/v1/guides/{guide_id}/availability
# ---------------------------------------------------------------------------

@router.get(
    "/{guide_id}/availability",
    response_model=GuideAvailabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get guide availability",
    description=(
        "Returns the guide's current availability status and optional note. "
        "Publicly readable. Returns AVAILABLE with no note if not yet set."
    ),
)
async def get_availability(
    guide_id: UUID,
    service: GuideAvailabilityService = Depends(get_guide_availability_service),
) -> GuideAvailabilityResponse:
    return await service.get_availability(guide_id)


# ---------------------------------------------------------------------------
# PUT /api/v1/guides/{guide_id}/availability
# ---------------------------------------------------------------------------

@router.put(
    "/{guide_id}/availability",
    response_model=GuideAvailabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Set guide availability",
    description=(
        "Creates or updates the guide's availability record (upsert). "
        "Both status and note are optional — omit to leave unchanged. "
        "Guide owner only."
    ),
)
async def set_availability(
    guide_id: UUID,
    payload: GuideAvailabilityUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideAvailabilityService = Depends(get_guide_availability_service),
) -> GuideAvailabilityResponse:
    user_id = UUID(current_user["sub"])
    return await service.set_availability(guide_id, payload, user_id)
