"""
Participants router — sub-resource under /api/v1/expeditions/{expedition_id}
"""

from __future__ import annotations

from typing import Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared.dependencies import get_current_user

from app.dependencies.expedition_deps import get_participant_service
from app.schemas.participant import ParticipantResponse, ParticipantRoleUpdate
from app.services.participant_service import ParticipantService

router = APIRouter(
    prefix="/api/v1/expeditions",
    tags=["Participants"],
)


@router.get(
    "/{expedition_id}/participants",
    response_model=List[ParticipantResponse],
    status_code=status.HTTP_200_OK,
    summary="List expedition participants",
)
async def list_participants(
    expedition_id: UUID,
    active_only: bool = True,
    service: ParticipantService = Depends(get_participant_service),
) -> List[ParticipantResponse]:
    return await service.list_participants(expedition_id, active_only=active_only)


@router.delete(
    "/{expedition_id}/participants/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a participant",
    description="Organiser or co-organiser only. Cannot remove the organiser.",
)
async def remove_participant(
    expedition_id: UUID,
    user_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ParticipantService = Depends(get_participant_service),
) -> None:
    current_user_id = UUID(current_user["sub"])
    await service.remove_participant(expedition_id, user_id, current_user_id)


@router.patch(
    "/{expedition_id}/participants/{user_id}/role",
    response_model=ParticipantResponse,
    status_code=status.HTTP_200_OK,
    summary="Update participant role",
    description="Organiser only. Promotes to CO_ORGANIZER or demotes back to PARTICIPANT.",
)
async def update_participant_role(
    expedition_id: UUID,
    user_id: UUID,
    payload: ParticipantRoleUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ParticipantService = Depends(get_participant_service),
) -> ParticipantResponse:
    current_user_id = UUID(current_user["sub"])
    return await service.update_role(expedition_id, user_id, payload.role, current_user_id)


@router.delete(
    "/{expedition_id}/leave",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Leave an expedition",
    description="The current user leaves the expedition. The organiser cannot leave.",
)
async def leave_expedition(
    expedition_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ParticipantService = Depends(get_participant_service),
) -> None:
    current_user_id = UUID(current_user["sub"])
    await service.leave_expedition(expedition_id, current_user_id)
