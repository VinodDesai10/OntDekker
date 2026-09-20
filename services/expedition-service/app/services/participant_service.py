"""
ParticipantService — business logic for participant management.

Rules enforced:
  - Only active (non-deleted, non-cancelled) expeditions accept new participants
  - Capacity must not exceed max_participants
  - A user cannot join twice (UniqueConstraint guard before DB hit)
  - Only the organiser or co-organiser can remove participants
  - The organiser cannot remove themselves
  - Only the organiser can promote/demote roles
"""

from __future__ import annotations

from typing import Sequence
from uuid import UUID

from shared import ConflictException, ForbiddenException, NotFoundException, ValidationException

from app.models.expedition import ExpeditionStatus
from app.models.participant import ParticipantRole, ParticipantStatus
from app.repositories.expedition_repository import ExpeditionRepository
from app.repositories.participant_repository import ParticipantRepository
from app.schemas.participant import ParticipantResponse


class ParticipantService:

    def __init__(
        self,
        expedition_repo: ExpeditionRepository,
        participant_repo: ParticipantRepository,
    ) -> None:
        self._expedition_repo = expedition_repo
        self._participant_repo = participant_repo

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    async def list_participants(
        self,
        expedition_id: UUID,
        *,
        active_only: bool = True,
    ) -> list[ParticipantResponse]:
        """Return participants for an expedition. 404 if expedition missing."""
        await self._require_expedition(expedition_id)
        participants = await self._participant_repo.list_by_expedition(
            expedition_id, active_only=active_only
        )
        return [ParticipantResponse.model_validate(p) for p in participants]

    # ------------------------------------------------------------------
    # JOIN — PUBLIC expedition
    # ------------------------------------------------------------------

    async def join_expedition(
        self,
        expedition_id: UUID,
        current_user_id: UUID,
    ) -> ParticipantResponse:
        """Add the current user as a PARTICIPANT directly.

        Only valid for PUBLIC expeditions that are PUBLISHED or ACTIVE.
        For PRIVATE expeditions the join-request workflow applies.
        """
        expedition = await self._require_expedition(expedition_id)

        if expedition.visibility != expedition.visibility.PUBLIC:
            raise ValidationException(
                "This expedition requires a join request. "
                "Use POST /expeditions/{id}/join instead.",
                error_code="USE_JOIN_REQUEST",
            )

        if expedition.status not in (ExpeditionStatus.PUBLISHED, ExpeditionStatus.ACTIVE):
            raise ValidationException(
                f"Cannot join an expedition with status '{expedition.status}'.",
                error_code="EXPEDITION_NOT_JOINABLE",
            )

        # Duplicate check
        existing = await self._participant_repo.get_by_expedition_and_user(
            expedition_id, current_user_id
        )
        if existing and existing.status == ParticipantStatus.ACTIVE:
            raise ConflictException(
                "You are already a participant in this expedition.",
                error_code="ALREADY_PARTICIPANT",
            )

        # Capacity check
        current_count = await self._participant_repo.count_active(expedition_id)
        if current_count >= expedition.max_participants:
            raise ValidationException(
                "This expedition has reached its maximum participant limit.",
                error_code="EXPEDITION_FULL",
            )

        participant = await self._participant_repo.add(
            expedition_id=expedition_id,
            user_id=current_user_id,
            role=ParticipantRole.PARTICIPANT,
        )
        return ParticipantResponse.model_validate(participant)

    # ------------------------------------------------------------------
    # LEAVE
    # ------------------------------------------------------------------

    async def leave_expedition(
        self,
        expedition_id: UUID,
        current_user_id: UUID,
    ) -> None:
        """Mark the current user as LEFT."""
        await self._require_expedition(expedition_id)

        participant = await self._participant_repo.get_by_expedition_and_user(
            expedition_id, current_user_id
        )
        if not participant or participant.status != ParticipantStatus.ACTIVE:
            raise NotFoundException(
                "You are not an active participant in this expedition.",
                error_code="NOT_PARTICIPANT",
            )

        if participant.role == ParticipantRole.ORGANIZER:
            raise ValidationException(
                "The organiser cannot leave the expedition. "
                "Transfer organiser role or cancel the expedition first.",
                error_code="ORGANISER_CANNOT_LEAVE",
            )

        await self._participant_repo.update_status(
            expedition_id, current_user_id, ParticipantStatus.LEFT
        )

    # ------------------------------------------------------------------
    # REMOVE (organiser action)
    # ------------------------------------------------------------------

    async def remove_participant(
        self,
        expedition_id: UUID,
        target_user_id: UUID,
        current_user_id: UUID,
    ) -> None:
        """Remove a participant. Only organiser or co-organiser can do this."""
        await self._require_expedition(expedition_id)
        await self._require_organiser_or_co(expedition_id, current_user_id)

        target = await self._participant_repo.get_by_expedition_and_user(
            expedition_id, target_user_id
        )
        if not target or target.status != ParticipantStatus.ACTIVE:
            raise NotFoundException(
                "Participant not found in this expedition.",
                error_code="PARTICIPANT_NOT_FOUND",
            )

        if target.role == ParticipantRole.ORGANIZER:
            raise ValidationException(
                "Cannot remove the expedition organiser.",
                error_code="CANNOT_REMOVE_ORGANISER",
            )

        await self._participant_repo.update_status(
            expedition_id, target_user_id, ParticipantStatus.REMOVED
        )

    # ------------------------------------------------------------------
    # ROLE UPDATE (organiser action)
    # ------------------------------------------------------------------

    async def update_role(
        self,
        expedition_id: UUID,
        target_user_id: UUID,
        new_role: ParticipantRole,
        current_user_id: UUID,
    ) -> ParticipantResponse:
        """Promote or demote a participant's role. Only organiser can do this."""
        await self._require_expedition(expedition_id)
        await self._require_organiser(expedition_id, current_user_id)

        target = await self._participant_repo.get_by_expedition_and_user(
            expedition_id, target_user_id
        )
        if not target or target.status != ParticipantStatus.ACTIVE:
            raise NotFoundException(
                "Participant not found in this expedition.",
                error_code="PARTICIPANT_NOT_FOUND",
            )

        updated = await self._participant_repo.update_role(
            expedition_id, target_user_id, new_role
        )
        return ParticipantResponse.model_validate(updated)

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    async def _require_expedition(self, expedition_id: UUID):
        expedition = await self._expedition_repo.get_by_id(expedition_id)
        if not expedition:
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )
        return expedition

    async def _require_organiser(self, expedition_id: UUID, user_id: UUID) -> None:
        participant = await self._participant_repo.get_by_expedition_and_user(
            expedition_id, user_id
        )
        if not participant or participant.role != ParticipantRole.ORGANIZER:
            raise ForbiddenException(
                "Only the expedition organiser can perform this action.",
                error_code="NOT_ORGANISER",
            )

    async def _require_organiser_or_co(self, expedition_id: UUID, user_id: UUID) -> None:
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
