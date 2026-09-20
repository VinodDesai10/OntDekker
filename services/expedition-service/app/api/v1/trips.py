"""
Trips router — /api/v1/trips endpoints.

Provides the trip-centric API surface required by MCP-1:
  POST   /api/v1/trips
  GET    /api/v1/trips
  GET    /api/v1/trips/{id}
  PUT    /api/v1/trips/{id}
  DELETE /api/v1/trips/{id}
  POST   /api/v1/trips/{id}/join
  POST   /api/v1/trips/{id}/leave
  GET    /api/v1/users/me/trips
  GET    /api/v1/trips/{id}/me/participant
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status

from shared.dependencies import get_current_user

from app.dependencies.expedition_deps import get_trip_service, get_participant_repository
from app.models.expedition import ExpeditionStatus
from app.schemas.common import PaginatedResponse
from app.schemas.trip import TripCreate, TripFilter, TripResponse, TripSummary, TripUpdate
from app.schemas.participant import ParticipantResponse
from app.services.trip_service import TripService
from app.repositories.participant_repository import ParticipantRepository

router = APIRouter(tags=["Trips"])


# ---------------------------------------------------------------------------
# POST /api/v1/trips — create trip
# ---------------------------------------------------------------------------

@router.post(
    "/api/v1/trips",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a trip",
)
async def create_trip(
    payload: TripCreate,
    authorization: Optional[str] = Header(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    user_id = UUID(current_user["sub"])
    token = authorization.split(" ")[1] if authorization and " " in authorization else ""
    return await service.create_trip(payload, user_id, auth_token=token)


# ---------------------------------------------------------------------------
# GET /api/v1/trips — public listing with search/filter
# ---------------------------------------------------------------------------

@router.get(
    "/api/v1/trips",
    response_model=PaginatedResponse[TripSummary],
    status_code=status.HTTP_200_OK,
    summary="List public trips",
)
async def list_trips(
    search: Optional[str] = Query(default=None),
    community_id: Optional[UUID] = Query(default=None),
    personal_only: bool = Query(default=False),
    status_filter: Optional[ExpeditionStatus] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: TripService = Depends(get_trip_service),
) -> PaginatedResponse[TripSummary]:
    filters = TripFilter(
        search=search,
        community_id=community_id,
        personal_only=personal_only,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return await service.list_trips(filters)


# ---------------------------------------------------------------------------
# GET /api/v1/trips/{trip_id} — single trip detail
# ---------------------------------------------------------------------------

@router.get(
    "/api/v1/trips/{trip_id}",
    response_model=TripResponse,
    status_code=status.HTTP_200_OK,
    summary="Get trip details",
)
async def get_trip(
    trip_id: UUID,
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    return await service.get_trip(trip_id)


# ---------------------------------------------------------------------------
# PUT /api/v1/trips/{trip_id} — update trip
# ---------------------------------------------------------------------------

@router.put(
    "/api/v1/trips/{trip_id}",
    response_model=TripResponse,
    status_code=status.HTTP_200_OK,
    summary="Update trip",
)
async def update_trip(
    trip_id: UUID,
    payload: TripUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    user_id = UUID(current_user["sub"])
    return await service.update_trip(trip_id, payload, user_id)


# ---------------------------------------------------------------------------
# DELETE /api/v1/trips/{trip_id} — soft delete
# ---------------------------------------------------------------------------

@router.delete(
    "/api/v1/trips/{trip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete trip",
)
async def delete_trip(
    trip_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> None:
    user_id = UUID(current_user["sub"])
    await service.delete_trip(trip_id, user_id)


# ---------------------------------------------------------------------------
# POST /api/v1/trips/{trip_id}/join
# ---------------------------------------------------------------------------

@router.post(
    "/api/v1/trips/{trip_id}/join",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Join a trip",
)
async def join_trip(
    trip_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> None:
    user_id = UUID(current_user["sub"])
    await service.join_trip(trip_id, user_id)


# ---------------------------------------------------------------------------
# POST /api/v1/trips/{trip_id}/leave
# ---------------------------------------------------------------------------

@router.post(
    "/api/v1/trips/{trip_id}/leave",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Leave a trip",
)
async def leave_trip(
    trip_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> None:
    user_id = UUID(current_user["sub"])
    await service.leave_trip(trip_id, user_id)


# ---------------------------------------------------------------------------
# GET /api/v1/users/me/trips — trips where I am a participant
# ---------------------------------------------------------------------------

@router.get(
    "/api/v1/users/me/trips",
    response_model=PaginatedResponse[TripSummary],
    status_code=status.HTTP_200_OK,
    summary="My trips",
    description="Returns all trips (as host or member) for the authenticated user.",
)
async def my_trips(
    status_filter: Optional[ExpeditionStatus] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> PaginatedResponse[TripSummary]:
    user_id = UUID(current_user["sub"])
    return await service.list_my_trips(user_id, status=status_filter, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# GET /api/v1/trips/{trip_id}/me/participant
# Returns the current user's participant record for this trip, or 204 if not a member.
# ---------------------------------------------------------------------------

@router.get(
    "/api/v1/trips/{trip_id}/me/participant",
    response_model=Optional[ParticipantResponse],
    status_code=status.HTTP_200_OK,
    summary="Current user's participant status for a trip",
    description=(
        "Returns the authenticated user's participant record (role + status) for the trip. "
        "Returns null if the user is not a participant. Never raises 404 for non-membership."
    ),
)
async def get_my_participant_status(
    trip_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    participant_repo: ParticipantRepository = Depends(get_participant_repository),
) -> Optional[ParticipantResponse]:
    user_id = UUID(current_user["sub"])
    participant = await participant_repo.get_by_expedition_and_user(trip_id, user_id)
    if participant is None:
        return None
    return ParticipantResponse.model_validate(participant)
