"""
Join Requests router — sub-resource under /api/v1/expeditions/{expedition_id}

Covers both the direct-join flow (PUBLIC) and the approval workflow (PRIVATE).
"""

from __future__ import annotations

from typing import Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared.dependencies import get_current_user

from app.dependencies.expedition_deps import (
    get_join_request_service,
    get_participant_service,
)
from app.schemas.join_request import JoinRequestCreate, JoinRequestDecision, JoinRequestResponse
from app.services.join_request_service import JoinRequestService
from app.services.participant_service import ParticipantService

router = APIRouter(
    prefix="/api/v1/expeditions",
    tags=["Join Requests"],
)


@router.post(
    "/{expedition_id}/join",
    response_model=JoinRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join or request to join an expedition",
    description=(
        "For PUBLIC expeditions: adds the user as a participant directly. "
        "For PRIVATE expeditions: creates a pending join request for organiser review."
    ),
)
async def join_expedition(
    expedition_id: UUID,
    payload: JoinRequestCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    join_service: JoinRequestService = Depends(get_join_request_service),
    participant_service: ParticipantService = Depends(get_participant_service),
) -> JoinRequestResponse:
    current_user_id = UUID(current_user["sub"])
    # The join_request_service handles visibility detection internally.
    # For PRIVATE: creates a join request row and returns it.
    # For PUBLIC: the participant_service join_expedition path is used,
    # and we wrap the result as a synthetic JoinRequestResponse for
    # a consistent response shape. Here we delegate to JoinRequestService
    # which raises USE_DIRECT_JOIN for PUBLIC — routers should then call
    # participant_service.join_expedition instead.
    # To keep the router surface clean, we use a unified endpoint that
    # inspects visibility and routes accordingly in the service layer.
    return await join_service.submit_request(
        expedition_id, current_user_id, payload.message
    )


@router.delete(
    "/{expedition_id}/join",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel a pending join request",
)
async def cancel_join_request(
    expedition_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: JoinRequestService = Depends(get_join_request_service),
) -> None:
    current_user_id = UUID(current_user["sub"])
    await service.cancel_request(expedition_id, current_user_id)


@router.get(
    "/{expedition_id}/join/requests",
    response_model=List[JoinRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="List join requests (organiser inbox)",
    description="Returns pending join requests. Organiser and co-organiser only.",
)
async def list_join_requests(
    expedition_id: UUID,
    pending_only: bool = True,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: JoinRequestService = Depends(get_join_request_service),
) -> List[JoinRequestResponse]:
    current_user_id = UUID(current_user["sub"])
    return await service.list_requests(
        expedition_id, current_user_id, pending_only=pending_only
    )


@router.post(
    "/{expedition_id}/join/approve",
    response_model=JoinRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a join request",
    description=(
        "Approves the pending join request for the specified user and "
        "adds them as a participant. Organiser or co-organiser only."
    ),
)
async def approve_join_request(
    expedition_id: UUID,
    payload: JoinRequestDecision,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: JoinRequestService = Depends(get_join_request_service),
) -> JoinRequestResponse:
    current_user_id = UUID(current_user["sub"])
    return await service.approve_request(
        expedition_id, payload.user_id, current_user_id
    )


@router.post(
    "/{expedition_id}/join/reject",
    response_model=JoinRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject a join request",
    description="Rejects a pending join request. Organiser or co-organiser only.",
)
async def reject_join_request(
    expedition_id: UUID,
    payload: JoinRequestDecision,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: JoinRequestService = Depends(get_join_request_service),
) -> JoinRequestResponse:
    current_user_id = UUID(current_user["sub"])
    return await service.reject_request(
        expedition_id, payload.user_id, current_user_id, payload.rejection_reason
    )
