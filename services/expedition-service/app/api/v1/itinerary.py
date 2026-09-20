"""
Itinerary router — sub-resource under /api/v1/expeditions/{expedition_id}
"""

from __future__ import annotations

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared.dependencies import get_current_user

from app.dependencies.expedition_deps import get_itinerary_service
from app.schemas.itinerary import (
    ItineraryBulkUpdate,
    ItineraryDayCreate,
    ItineraryDayResponse,
    ItineraryDayUpdate,
    ItineraryResponse,
)
from app.services.itinerary_service import ItineraryService

router = APIRouter(
    prefix="/api/v1/expeditions",
    tags=["Itinerary"],
)


@router.get(
    "/{expedition_id}/itinerary",
    response_model=ItineraryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get expedition itinerary",
)
async def get_itinerary(
    expedition_id: UUID,
    service: ItineraryService = Depends(get_itinerary_service),
) -> ItineraryResponse:
    return await service.get_itinerary(expedition_id)


@router.put(
    "/{expedition_id}/itinerary",
    response_model=ItineraryResponse,
    status_code=status.HTTP_200_OK,
    summary="Replace full itinerary",
    description=(
        "Replaces the entire itinerary atomically. All existing days are "
        "deleted and the provided list is inserted. Organiser or co-organiser only."
    ),
)
async def replace_itinerary(
    expedition_id: UUID,
    payload: ItineraryBulkUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ItineraryService = Depends(get_itinerary_service),
) -> ItineraryResponse:
    current_user_id = UUID(current_user["sub"])
    return await service.replace_itinerary(expedition_id, payload, current_user_id)


@router.post(
    "/{expedition_id}/itinerary",
    response_model=ItineraryDayResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a single itinerary day",
)
async def add_itinerary_day(
    expedition_id: UUID,
    payload: ItineraryDayCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ItineraryService = Depends(get_itinerary_service),
) -> ItineraryDayResponse:
    current_user_id = UUID(current_user["sub"])
    return await service.add_day(expedition_id, payload, current_user_id)


@router.patch(
    "/{expedition_id}/itinerary/{day_number}",
    response_model=ItineraryDayResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a single itinerary day",
)
async def update_itinerary_day(
    expedition_id: UUID,
    day_number: int,
    payload: ItineraryDayUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ItineraryService = Depends(get_itinerary_service),
) -> ItineraryDayResponse:
    current_user_id = UUID(current_user["sub"])
    return await service.update_day(expedition_id, day_number, payload, current_user_id)


@router.delete(
    "/{expedition_id}/itinerary/{day_number}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a single itinerary day",
)
async def delete_itinerary_day(
    expedition_id: UUID,
    day_number: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ItineraryService = Depends(get_itinerary_service),
) -> None:
    current_user_id = UUID(current_user["sub"])
    await service.delete_day(expedition_id, day_number, current_user_id)
