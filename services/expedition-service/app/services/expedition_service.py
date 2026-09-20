"""
ExpeditionService — business logic for expedition lifecycle.

This is the only layer that:
  - enforces business rules (status transitions, ownership, capacity)
  - coordinates multiple repositories in a single operation
  - raises domain exceptions for invalid operations
  - builds paginated response objects from raw repository data

The service never touches the database directly — it delegates all
persistence to ExpeditionRepository and ParticipantRepository.

Documented status machine (from 03-microservices.md):
  DRAFT → PUBLISHED → ACTIVE → COMPLETED → ARCHIVED
                    ↘ CANCELLED (from any non-terminal state)
"""

from __future__ import annotations

import math
from typing import Optional
from uuid import UUID

from shared import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from shared.logging import setup_logging

from app.models.expedition import ExpeditionStatus, ExpeditionVisibility
from app.models.participant import ParticipantRole, ParticipantStatus
from app.repositories.expedition_repository import ExpeditionRepository
from app.repositories.participant_repository import ParticipantRepository
from app.schemas.common import ExpeditionFilter, PaginatedResponse, PaginationMeta
from app.schemas.expedition import (
    ExpeditionCreate,
    ExpeditionResponse,
    ExpeditionSummary,
    ExpeditionUpdate,
)

logger = setup_logging(service_name="expedition-service", log_level="INFO")

# Valid status transitions: {current_status: set_of_allowed_next_statuses}
_VALID_TRANSITIONS: dict[ExpeditionStatus, set[ExpeditionStatus]] = {
    ExpeditionStatus.DRAFT:      {ExpeditionStatus.PUBLISHED, ExpeditionStatus.CANCELLED},
    ExpeditionStatus.PUBLISHED:  {ExpeditionStatus.ACTIVE, ExpeditionStatus.CANCELLED},
    ExpeditionStatus.ACTIVE:     {ExpeditionStatus.COMPLETED, ExpeditionStatus.CANCELLED},
    ExpeditionStatus.COMPLETED:  {ExpeditionStatus.ARCHIVED},
    ExpeditionStatus.CANCELLED:  set(),
    ExpeditionStatus.ARCHIVED:   set(),
}


class ExpeditionService:
    """Coordinates business logic for expedition CRUD and lifecycle."""

    def __init__(
        self,
        expedition_repo: ExpeditionRepository,
        participant_repo: ParticipantRepository,
    ) -> None:
        self._expedition_repo = expedition_repo
        self._participant_repo = participant_repo

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create_expedition(
        self,
        payload: ExpeditionCreate,
        current_user_id: UUID,
    ) -> ExpeditionResponse:
        """Create a new expedition in DRAFT status.

        The organizer_id is always the authenticated user — never from
        the request payload. The organiser is automatically added as
        the first ACTIVE ORGANIZER participant.
        """
        expedition = await self._expedition_repo.create(
            community_id=payload.community_id,
            organizer_id=current_user_id,
            title=payload.title,
            destination=payload.destination,
            description=payload.description,
            meeting_point=payload.meeting_point,
            start_date=payload.start_date,
            end_date=payload.end_date,
            max_participants=payload.max_participants,
            budget=payload.budget,
            visibility=payload.visibility,
            cover_image_url=payload.cover_image_url,
            created_by=current_user_id,
        )

        # Auto-add organiser as ORGANIZER participant
        await self._participant_repo.add(
            expedition_id=expedition.id,
            user_id=current_user_id,
            role=ParticipantRole.ORGANIZER,
        )

        return ExpeditionResponse.model_validate(expedition)

    # ------------------------------------------------------------------
    # READ — single
    # ------------------------------------------------------------------

    async def get_expedition(self, expedition_id: UUID) -> ExpeditionResponse:
        """Fetch a single expedition. Raises 404 if not found."""
        expedition = await self._expedition_repo.get_by_id(expedition_id)
        if not expedition:
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )
        return ExpeditionResponse.model_validate(expedition)

    # ------------------------------------------------------------------
    # READ — paginated list
    # ------------------------------------------------------------------

    async def list_expeditions(
        self,
        filters: ExpeditionFilter,
    ) -> PaginatedResponse[ExpeditionSummary]:
        """Return a filtered, paginated list of expeditions."""
        items, total = await self._expedition_repo.list_expeditions(filters)

        total_pages = max(1, math.ceil(total / filters.page_size))
        pagination = PaginationMeta(
            page=filters.page,
            page_size=filters.page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=filters.page < total_pages,
            has_previous=filters.page > 1,
        )
        return PaginatedResponse[ExpeditionSummary](
            items=[ExpeditionSummary.model_validate(e) for e in items],
            pagination=pagination,
        )

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    async def update_expedition(
        self,
        expedition_id: UUID,
        payload: ExpeditionUpdate,
        current_user_id: UUID,
    ) -> ExpeditionResponse:
        """Partially update an expedition.

        Only the organiser or a co-organiser may update.
        Status changes are rejected here — use transition_status().
        """
        expedition = await self._expedition_repo.get_by_id(expedition_id)
        if not expedition:
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )

        await self._require_organiser_or_co(expedition_id, current_user_id)

        # Block updates on terminal states
        if expedition.status in (
            ExpeditionStatus.COMPLETED,
            ExpeditionStatus.CANCELLED,
            ExpeditionStatus.ARCHIVED,
        ):
            raise ValidationException(
                f"Cannot update an expedition with status '{expedition.status}'.",
                error_code="EXPEDITION_NOT_EDITABLE",
            )

        # Extract only non-None fields from the update payload
        update_data = payload.model_dump(exclude_none=True)

        updated = await self._expedition_repo.update(
            expedition_id,
            updated_by=current_user_id,
            **update_data,
        )
        if not updated:
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )
        return ExpeditionResponse.model_validate(updated)

    # ------------------------------------------------------------------
    # STATUS TRANSITIONS
    # ------------------------------------------------------------------

    async def transition_status(
        self,
        expedition_id: UUID,
        new_status: ExpeditionStatus,
        current_user_id: UUID,
    ) -> ExpeditionResponse:
        """Transition an expedition to a new lifecycle status.

        Enforces the state machine defined in _VALID_TRANSITIONS.
        Only the organiser may perform status transitions.
        """
        expedition = await self._expedition_repo.get_by_id(expedition_id)
        if not expedition:
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )

        await self._require_organiser(expedition_id, current_user_id)

        allowed = _VALID_TRANSITIONS.get(expedition.status, set())
        if new_status not in allowed:
            raise ValidationException(
                f"Cannot transition from '{expedition.status}' to '{new_status}'.",
                error_code="INVALID_STATUS_TRANSITION",
            )

        updated = await self._expedition_repo.update_status(
            expedition_id,
            new_status,
            updated_by=current_user_id,
        )
        return ExpeditionResponse.model_validate(updated)

    # ------------------------------------------------------------------
    # SOFT DELETE (cancel / archive)
    # ------------------------------------------------------------------

    async def delete_expedition(
        self,
        expedition_id: UUID,
        current_user_id: UUID,
    ) -> None:
        """Soft-delete an expedition. Only the organiser may do this.

        Soft delete is only allowed on DRAFT or CANCELLED expeditions.
        Active or completed expeditions must be cancelled first.
        """
        expedition = await self._expedition_repo.get_by_id(expedition_id)
        if not expedition:
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )

        await self._require_organiser(expedition_id, current_user_id)

        if expedition.status not in (
            ExpeditionStatus.DRAFT,
            ExpeditionStatus.CANCELLED,
            ExpeditionStatus.ARCHIVED,
        ):
            raise ValidationException(
                "Only DRAFT, CANCELLED, or ARCHIVED expeditions can be deleted. "
                "Cancel the expedition first.",
                error_code="EXPEDITION_NOT_DELETABLE",
            )

        deleted = await self._expedition_repo.soft_delete(
            expedition_id, deleted_by=current_user_id
        )
        if not deleted:
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )

    # ------------------------------------------------------------------
    # PRIVATE HELPERS — authorisation guards
    # ------------------------------------------------------------------

    async def _require_organiser(
        self, expedition_id: UUID, user_id: UUID
    ) -> None:
        """Raise 403 if the user is not the ORGANIZER of this expedition."""
        participant = await self._participant_repo.get_by_expedition_and_user(
            expedition_id, user_id
        )
        if not participant or participant.role != ParticipantRole.ORGANIZER:
            raise ForbiddenException(
                "Only the expedition organiser can perform this action.",
                error_code="NOT_ORGANISER",
            )

    async def _require_organiser_or_co(
        self, expedition_id: UUID, user_id: UUID
    ) -> None:
        """Raise 403 if the user is not ORGANIZER or CO_ORGANIZER."""
        participant = await self._participant_repo.get_by_expedition_and_user(
            expedition_id, user_id
        )
        if not participant or participant.role not in (
            ParticipantRole.ORGANIZER,
            ParticipantRole.CO_ORGANIZER,
        ):
            raise ForbiddenException(
                "Only the organiser or co-organiser can perform this action.",
                error_code="NOT_ORGANISER_OR_CO",
            )
