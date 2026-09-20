"""
TripService — business logic for /api/v1/trips.

Permission rules:
  - Any authenticated user can create a personal trip (community_id=None).
  - Community trips: the user must pass their community role in the request.
    The frontend reads this from the community membership context. We trust
    the JWT sub claim for ownership; the community role claim is validated
    by checking membership via the community-service HTTP call when
    COMMUNITY_SERVICE_URL is configured, or skipped in dev (permissive).
  - Only the trip host (organizer) may update or delete.
  - Any authenticated user can join a PUBLIC trip that is not full.
  - A participant can leave any trip they are in (host cannot leave).
"""

from __future__ import annotations

import math
import os
from typing import Optional
from uuid import UUID

import httpx

from shared import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from shared.logging import setup_logging

from app.models.expedition import ExpeditionStatus, ExpeditionVisibility
from app.models.participant import ParticipantRole, ParticipantStatus
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.trip_repository import TripRepository
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.trip import (
    TripCreate,
    TripFilter,
    TripResponse,
    TripSummary,
    TripUpdate,
)

logger = setup_logging(service_name="expedition-service", log_level="INFO")

# Community-service base URL — injected via env; None means permission checks
# are skipped (development / unit-test mode).
_COMMUNITY_SERVICE_URL = os.getenv("COMMUNITY_SERVICE_URL", "")


def _build_trip_response(expedition, participant_count: int = 0, host_name: Optional[str] = None) -> TripResponse:
    """Map an Expedition ORM object to a TripResponse."""
    return TripResponse(
        id=expedition.id,
        community_id=expedition.community_id,
        host_id=expedition.organizer_id,
        title=expedition.title,
        destination=expedition.destination,
        description=expedition.description,
        cover_image_url=expedition.cover_image_url,
        start_date=expedition.start_date,
        end_date=expedition.end_date,
        budget=expedition.budget,
        max_participants=expedition.max_participants,
        current_participants_count=participant_count,
        visibility=expedition.visibility,
        status=expedition.status,
        host_name=host_name,
        created_at=expedition.created_at,
        updated_at=expedition.updated_at,
    )


def _build_trip_summary(expedition, participant_count: int = 0, host_name: Optional[str] = None) -> TripSummary:
    return TripSummary(
        id=expedition.id,
        community_id=expedition.community_id,
        host_id=expedition.organizer_id,
        title=expedition.title,
        destination=expedition.destination,
        cover_image_url=expedition.cover_image_url,
        start_date=expedition.start_date,
        end_date=expedition.end_date,
        budget=expedition.budget,
        max_participants=expedition.max_participants,
        current_participants_count=participant_count,
        visibility=expedition.visibility,
        status=expedition.status,
        host_name=host_name,
        created_at=expedition.created_at,
    )


async def _check_community_role(community_id: UUID, user_id: UUID, token: str) -> bool:
    """
    Returns True if the user is HEAD or CO_HEAD in the given community.
    Falls back to True (permissive) if COMMUNITY_SERVICE_URL is not set.
    """
    if not _COMMUNITY_SERVICE_URL:
        logger.warning(
            "COMMUNITY_SERVICE_URL not set — skipping community role check (permissive mode)."
        )
        return True

    url = f"{_COMMUNITY_SERVICE_URL}/api/v1/communities/{community_id}/members/me"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code != 200:
            return False
        data = resp.json()
        role = data.get("role", "")
        return role in ("OWNER", "MODERATOR")
    except Exception as exc:
        logger.error("Community role check failed: %s", exc)
        # Fail-open in development; fail-closed in production via env flag
        return os.getenv("COMMUNITY_ROLE_CHECK_STRICT", "false").lower() != "true"


class TripService:
    def __init__(
        self,
        trip_repo: TripRepository,
        participant_repo: ParticipantRepository,
    ) -> None:
        self._trip_repo = trip_repo
        self._participant_repo = participant_repo

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create_trip(
        self,
        payload: TripCreate,
        current_user_id: UUID,
        auth_token: str = "",
    ) -> TripResponse:
        # Community trip → verify the user is HEAD or CO_HEAD
        if payload.community_id is not None:
            allowed = await _check_community_role(
                payload.community_id, current_user_id, auth_token
            )
            if not allowed:
                raise ForbiddenException(
                    "Only community heads and co-heads can create trips inside a community.",
                    error_code="NOT_COMMUNITY_HEAD",
                )

        expedition = await self._trip_repo.create(
            organizer_id=current_user_id,
            title=payload.title,
            destination=payload.destination,
            community_id=payload.community_id,
            description=payload.description,
            cover_image_url=payload.cover_image_url,
            start_date=payload.start_date,
            end_date=payload.end_date,
            budget=payload.budget,
            max_participants=payload.max_participants,
            visibility=payload.visibility,
            created_by=current_user_id,
        )

        # Auto-enroll organizer as HOST participant
        await self._participant_repo.add(
            expedition_id=expedition.id,
            user_id=current_user_id,
            role=ParticipantRole.ORGANIZER,
        )

        return _build_trip_response(expedition, participant_count=1)

    # ------------------------------------------------------------------
    # GET single
    # ------------------------------------------------------------------

    async def get_trip(self, trip_id: UUID) -> TripResponse:
        expedition = await self._trip_repo.get_by_id(trip_id)
        if not expedition:
            raise NotFoundException(f"Trip {trip_id} not found.", error_code="TRIP_NOT_FOUND")
        count = await self._trip_repo.count_active_participants(trip_id)
        return _build_trip_response(expedition, participant_count=count)

    # ------------------------------------------------------------------
    # LIST — public trips (search + filter)
    # ------------------------------------------------------------------

    async def list_trips(self, filters: TripFilter) -> PaginatedResponse[TripSummary]:
        items, total = await self._trip_repo.list_trips(filters)
        total_pages = max(1, math.ceil(total / filters.page_size))
        pagination = PaginationMeta(
            page=filters.page,
            page_size=filters.page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=filters.page < total_pages,
            has_previous=filters.page > 1,
        )
        summaries = []
        for exp in items:
            count = await self._trip_repo.count_active_participants(exp.id)
            summaries.append(_build_trip_summary(exp, participant_count=count))
        return PaginatedResponse[TripSummary](items=summaries, pagination=pagination)

    # ------------------------------------------------------------------
    # LIST — my trips (participant-based)
    # ------------------------------------------------------------------

    async def list_my_trips(
        self,
        current_user_id: UUID,
        status: Optional[ExpeditionStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[TripSummary]:
        items, total = await self._trip_repo.list_my_trips(
            current_user_id, status=status, page=page, page_size=page_size
        )
        total_pages = max(1, math.ceil(total / page_size))
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )
        summaries = []
        for exp in items:
            count = await self._trip_repo.count_active_participants(exp.id)
            summaries.append(_build_trip_summary(exp, participant_count=count))
        return PaginatedResponse[TripSummary](items=summaries, pagination=pagination)

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    async def update_trip(
        self,
        trip_id: UUID,
        payload: TripUpdate,
        current_user_id: UUID,
    ) -> TripResponse:
        expedition = await self._trip_repo.get_by_id(trip_id)
        if not expedition:
            raise NotFoundException(f"Trip {trip_id} not found.", error_code="TRIP_NOT_FOUND")
        if expedition.organizer_id != current_user_id:
            raise ForbiddenException("Only the trip host can update this trip.", error_code="NOT_HOST")

        update_data = payload.model_dump(exclude_none=True)
        updated = await self._trip_repo.update(trip_id, updated_by=current_user_id, **update_data)
        if not updated:
            raise NotFoundException(f"Trip {trip_id} not found.", error_code="TRIP_NOT_FOUND")
        count = await self._trip_repo.count_active_participants(trip_id)
        return _build_trip_response(updated, participant_count=count)

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    async def delete_trip(self, trip_id: UUID, current_user_id: UUID) -> None:
        expedition = await self._trip_repo.get_by_id(trip_id)
        if not expedition:
            raise NotFoundException(f"Trip {trip_id} not found.", error_code="TRIP_NOT_FOUND")
        if expedition.organizer_id != current_user_id:
            raise ForbiddenException("Only the trip host can delete this trip.", error_code="NOT_HOST")
        await self._trip_repo.soft_delete(trip_id, deleted_by=current_user_id)

    # ------------------------------------------------------------------
    # JOIN
    # ------------------------------------------------------------------

    async def join_trip(self, trip_id: UUID, current_user_id: UUID) -> None:
        expedition = await self._trip_repo.get_by_id(trip_id)
        if not expedition:
            raise NotFoundException(f"Trip {trip_id} not found.", error_code="TRIP_NOT_FOUND")

        if expedition.visibility != ExpeditionVisibility.PUBLIC:
            raise ValidationException(
                "This trip is private. Use the join-request flow.",
                error_code="TRIP_PRIVATE",
            )
        if expedition.status not in (ExpeditionStatus.PUBLISHED, ExpeditionStatus.ACTIVE):
            raise ValidationException(
                f"Cannot join a trip with status '{expedition.status}'.",
                error_code="TRIP_NOT_JOINABLE",
            )

        existing = await self._participant_repo.get_by_expedition_and_user(trip_id, current_user_id)
        if existing and existing.status == ParticipantStatus.ACTIVE:
            raise ConflictException("You are already a member of this trip.", error_code="ALREADY_MEMBER")

        count = await self._trip_repo.count_active_participants(trip_id)
        if count >= expedition.max_participants:
            raise ValidationException("This trip is full.", error_code="TRIP_FULL")

        await self._participant_repo.add(
            expedition_id=trip_id,
            user_id=current_user_id,
            role=ParticipantRole.PARTICIPANT,
        )

    # ------------------------------------------------------------------
    # LEAVE
    # ------------------------------------------------------------------

    async def leave_trip(self, trip_id: UUID, current_user_id: UUID) -> None:
        expedition = await self._trip_repo.get_by_id(trip_id)
        if not expedition:
            raise NotFoundException(f"Trip {trip_id} not found.", error_code="TRIP_NOT_FOUND")

        participant = await self._participant_repo.get_by_expedition_and_user(trip_id, current_user_id)
        if not participant or participant.status != ParticipantStatus.ACTIVE:
            raise NotFoundException("You are not a member of this trip.", error_code="NOT_MEMBER")
        if participant.role == ParticipantRole.ORGANIZER:
            raise ValidationException(
                "The trip host cannot leave. Delete the trip instead.",
                error_code="HOST_CANNOT_LEAVE",
            )

        await self._participant_repo.update_status(trip_id, current_user_id, ParticipantStatus.LEFT)
