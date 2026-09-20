"""
Expeditions router — core CRUD and lifecycle endpoints.

All routes are under the prefix /api/v1/expeditions.
Sub-resources (participants, itinerary, gallery, gear, reviews)
live in their own router files and are included here.
"""

from __future__ import annotations

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared.dependencies import get_current_user

from app.dependencies.expedition_deps import get_expedition_service
from app.models.expedition import ExpeditionStatus
from app.schemas.common import ApiResponse, ExpeditionFilter, PaginatedResponse
from app.schemas.expedition import (
    ExpeditionCreate,
    ExpeditionResponse,
    ExpeditionSummary,
    ExpeditionUpdate,
)
from app.services.expedition_service import ExpeditionService

router = APIRouter(
    prefix="/api/v1/expeditions",
    tags=["Expeditions"],
)


# ---------------------------------------------------------------------------
# POST /api/v1/expeditions — create expedition
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ApiResponse[ExpeditionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new expedition",
    description=(
        "Creates a new expedition in DRAFT status. "
        "The authenticated user becomes the organiser. "
        "The organiser is automatically added as the first participant."
    ),
)
async def create_expedition(
    payload: ExpeditionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ExpeditionService = Depends(get_expedition_service),
) -> ApiResponse[ExpeditionResponse]:
    user_id = UUID(current_user["sub"])
    expedition = await service.create_expedition(payload, user_id)
    return ApiResponse[ExpeditionResponse](
        message="Expedition created successfully.",
        data=expedition,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/expeditions — list expeditions
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=PaginatedResponse[ExpeditionSummary],
    status_code=status.HTTP_200_OK,
    summary="List expeditions",
    description=(
        "Returns a paginated list of expeditions. "
        "Filter by community_id, organizer_id, status, or visibility."
    ),
)
async def list_expeditions(
    filters: ExpeditionFilter = Depends(),
    service: ExpeditionService = Depends(get_expedition_service),
) -> PaginatedResponse[ExpeditionSummary]:
    return await service.list_expeditions(filters)


# ---------------------------------------------------------------------------
# GET /api/v1/expeditions/{expedition_id} — get single expedition
# ---------------------------------------------------------------------------

@router.get(
    "/{expedition_id}",
    response_model=ApiResponse[ExpeditionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get expedition details",
)
async def get_expedition(
    expedition_id: UUID,
    service: ExpeditionService = Depends(get_expedition_service),
) -> ApiResponse[ExpeditionResponse]:
    expedition = await service.get_expedition(expedition_id)
    return ApiResponse[ExpeditionResponse](
        message="Expedition retrieved successfully.",
        data=expedition,
    )


# ---------------------------------------------------------------------------
# PATCH /api/v1/expeditions/{expedition_id} — update expedition
# ---------------------------------------------------------------------------

@router.patch(
    "/{expedition_id}",
    response_model=ApiResponse[ExpeditionResponse],
    status_code=status.HTTP_200_OK,
    summary="Update expedition details",
    description=(
        "Partially updates an expedition. "
        "Only the organiser or co-organiser may update. "
        "Status changes must use the /status endpoint."
    ),
)
async def update_expedition(
    expedition_id: UUID,
    payload: ExpeditionUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ExpeditionService = Depends(get_expedition_service),
) -> ApiResponse[ExpeditionResponse]:
    user_id = UUID(current_user["sub"])
    expedition = await service.update_expedition(expedition_id, payload, user_id)
    return ApiResponse[ExpeditionResponse](
        message="Expedition updated successfully.",
        data=expedition,
    )


# ---------------------------------------------------------------------------
# PATCH /api/v1/expeditions/{expedition_id}/status — lifecycle transition
# ---------------------------------------------------------------------------

@router.patch(
    "/{expedition_id}/status",
    response_model=ApiResponse[ExpeditionResponse],
    status_code=status.HTTP_200_OK,
    summary="Transition expedition status",
    description=(
        "Transitions the expedition to a new lifecycle status. "
        "Only the organiser may perform status transitions. "
        "Valid transitions: DRAFT→PUBLISHED→ACTIVE→COMPLETED→ARCHIVED, "
        "any non-terminal→CANCELLED."
    ),
)
async def transition_status(
    expedition_id: UUID,
    new_status: ExpeditionStatus,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ExpeditionService = Depends(get_expedition_service),
) -> ApiResponse[ExpeditionResponse]:
    user_id = UUID(current_user["sub"])
    expedition = await service.transition_status(expedition_id, new_status, user_id)
    return ApiResponse[ExpeditionResponse](
        message=f"Expedition status updated to {new_status}.",
        data=expedition,
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/expeditions/{expedition_id} — soft delete
# ---------------------------------------------------------------------------

@router.delete(
    "/{expedition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an expedition",
    description=(
        "Soft-deletes an expedition. "
        "Only allowed on DRAFT, CANCELLED, or ARCHIVED expeditions. "
        "Cancel the expedition first if it is in another state."
    ),
)
async def delete_expedition(
    expedition_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ExpeditionService = Depends(get_expedition_service),
) -> None:
    user_id = UUID(current_user["sub"])
    await service.delete_expedition(expedition_id, user_id)
