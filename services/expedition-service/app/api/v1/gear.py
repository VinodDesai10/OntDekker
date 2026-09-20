"""
Gear router — Pack Weight Optimizer sub-resource.
Routes: /api/v1/expeditions/{expedition_id}/gear
"""

from __future__ import annotations

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared.dependencies import get_current_user

from app.dependencies.expedition_deps import get_gear_item_service
from app.schemas.gear_item import (
    GearItemCreate,
    GearItemResponse,
    GearItemUpdate,
    GearListResponse,
)
from app.services.gear_item_service import GearItemService

router = APIRouter(
    prefix="/api/v1/expeditions",
    tags=["Gear Planner"],
)


@router.get(
    "/{expedition_id}/gear",
    response_model=GearListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get packing list and weight summary",
    description=(
        "Returns all gear items with a computed PackWeightSummary including "
        "total weight, per-category breakdown, and weight classification "
        "(ULTRALIGHT / LIGHTWEIGHT / STANDARD / HEAVY). Participants only."
    ),
)
async def get_gear_list(
    expedition_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GearItemService = Depends(get_gear_item_service),
) -> GearListResponse:
    current_user_id = UUID(current_user["sub"])
    return await service.get_gear_list(expedition_id, current_user_id)


@router.post(
    "/{expedition_id}/gear",
    response_model=GearItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a gear item",
    description="Active participants only.",
)
async def add_gear_item(
    expedition_id: UUID,
    payload: GearItemCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GearItemService = Depends(get_gear_item_service),
) -> GearItemResponse:
    current_user_id = UUID(current_user["sub"])
    return await service.add_item(expedition_id, payload, current_user_id)


@router.patch(
    "/{expedition_id}/gear/{item_id}",
    response_model=GearItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a gear item",
    description="Item owner or organiser/co-organiser only.",
)
async def update_gear_item(
    expedition_id: UUID,
    item_id: UUID,
    payload: GearItemUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GearItemService = Depends(get_gear_item_service),
) -> GearItemResponse:
    current_user_id = UUID(current_user["sub"])
    return await service.update_item(expedition_id, item_id, payload, current_user_id)


@router.delete(
    "/{expedition_id}/gear/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a gear item",
    description="Item owner or organiser/co-organiser only.",
)
async def delete_gear_item(
    expedition_id: UUID,
    item_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GearItemService = Depends(get_gear_item_service),
) -> None:
    current_user_id = UUID(current_user["sub"])
    await service.delete_item(expedition_id, item_id, current_user_id)
