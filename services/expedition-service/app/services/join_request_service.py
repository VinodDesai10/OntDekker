"""
JoinRequestService — business logic for join request workflow.

Rules enforced:
  - Join requests only apply to PRIVATE expeditions
  - A user cannot submit two pending requests
  - A user cannot request to join if already a participant
  - Organiser/co-organiser can approve or reject pending requests
  - Approving a request: creates participant row + marks request APPROVED
  - Rejecting: marks request REJECTED with optional reason
  - Cancelling: requester withdraws their own PENDING request
  - Capacity is checked at approval time, not at request time
"""

from __future__ import annotations

from uuid import UUID

from shared import ConflictException, ForbiddenException, NotFoundException, ValidationException

from app.models.expedition import ExpeditionStatus, ExpeditionVisibility
from app.models.join_request import JoinRequestStatus
from app.models.participant import ParticipantRole, ParticipantStatus
from app.repositories.expedition_repository import ExpeditionRepository
from app.repositories.join_request_repository import JoinRequestRepository
from app.repositories.participant_repository import ParticipantRepository
from app.schemas.join_request import JoinRequestResponse


class JoinRequestService:

    def __init__(
        self,
        expedition_repo: ExpeditionRepository,
        join_request_repo: JoinRequestRepository,
        participant_repo: ParticipantRepository,
    ) -> None:
        self._expedition_repo = expedition_repo
        self._join_request_repo = join_request_repo
        self._participant_repo = participant_repo

    # ------------------------------------------------------------------
    # SUBMIT REQUEST
    # ------------------------------------------------------------------

    async def submit_request(
        self,
        expedition_id: UUID,
        current_user_id: UUID,
        message: str | None = None,
    ) -> JoinRequestResponse:
        """Submit a join request to a PRIVATE expedition."""
        expedition = await self._expedition_repo.get_by_id(expedition_id)
        if not expedition:
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )

        if expedition.visibility != ExpeditionVisibility.PRIVATE:
            raise ValidationException(
                "This expedition is public. Use the direct join endpoint.",
                error_code="USE_DIRECT_JOIN",
            )

        if expedition.status not in (ExpeditionStatus.PUBLISHED, ExpeditionStatus.ACTIVE):
            raise ValidationException(
                f"Cannot request to join an expedition with status '{expedition.status}'.",
                error_code="EXPEDITION_NOT_JOINABLE",
            )

        # Already an active participant?
        if await self._participant_repo.is_participant(expedition_id, current_user_id):
            raise ConflictException(
                "You are already a participant in this expedition.",
                error_code="ALREADY_PARTICIPANT",
            )

        # Already has a pending request?
        if await self._join_request_repo.has_pending_request(expedition_id, current_user_id):
            raise ConflictException(
                "You already have a pending join request for this expedition.",
                error_code="DUPLICATE_JOIN_REQUEST",
            )

        request = await self._join_request_repo.create(
            expedition_id=expedition_id,
            user_id=current_user_id,
            message=message,
        )
        return JoinRequestResponse.model_validate(request)

    # ------------------------------------------------------------------
    # LIST (organiser inbox)
    # ------------------------------------------------------------------

    async def list_requests(
        self,
        expedition_id: UUID,
        current_user_id: UUID,
        *,
        pending_only: bool = True,
    ) -> list[JoinRequestResponse]:
        """Return join requests for an expedition.

        Only the organiser or co-organiser can view the inbox.
        """
        if not await self._expedition_repo.exists(expedition_id):
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )
        await self._require_organiser_or_co(expedition_id, current_user_id)

        status_filter = JoinRequestStatus.PENDING if pending_only else None
        requests = await self._join_request_repo.list_by_expedition(
            expedition_id, status=status_filter
        )
        return [JoinRequestResponse.model_validate(r) for r in requests]

    # ------------------------------------------------------------------
    # APPROVE
    # ------------------------------------------------------------------

    async def approve_request(
        self,
        expedition_id: UUID,
        applicant_user_id: UUID,
        current_user_id: UUID,
    ) -> JoinRequestResponse:
        """Approve a pending join request and add the applicant as participant."""
        if not await self._expedition_repo.exists(expedition_id):
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )
        await self._require_organiser_or_co(expedition_id, current_user_id)

        request = await self._join_request_repo.get_by_expedition_and_user(
            expedition_id, applicant_user_id
        )
        if not request or request.status != JoinRequestStatus.PENDING:
            raise NotFoundException(
                "No pending join request found for this user.",
                error_code="JOIN_REQUEST_NOT_FOUND",
            )

        # Capacity check at approval time
        expedition = await self._expedition_repo.get_by_id(expedition_id)
        current_count = await self._participant_repo.count_active(expedition_id)
        if current_count >= expedition.max_participants:
            raise ValidationException(
                "Cannot approve: expedition has reached its maximum participant limit.",
                error_code="EXPEDITION_FULL",
            )

        # Create participant row
        await self._participant_repo.add(
            expedition_id=expedition_id,
            user_id=applicant_user_id,
            role=ParticipantRole.PARTICIPANT,
        )

        # Mark request as approved
        updated = await self._join_request_repo.update_status(
            request.id,
            JoinRequestStatus.APPROVED,
            reviewed_by=current_user_id,
        )
        return JoinRequestResponse.model_validate(updated)

    # ------------------------------------------------------------------
    # REJECT
    # ------------------------------------------------------------------

    async def reject_request(
        self,
        expedition_id: UUID,
        applicant_user_id: UUID,
        current_user_id: UUID,
        rejection_reason: str | None = None,
    ) -> JoinRequestResponse:
        """Reject a pending join request."""
        if not await self._expedition_repo.exists(expedition_id):
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )
        await self._require_organiser_or_co(expedition_id, current_user_id)

        request = await self._join_request_repo.get_by_expedition_and_user(
            expedition_id, applicant_user_id
        )
        if not request or request.status != JoinRequestStatus.PENDING:
            raise NotFoundException(
                "No pending join request found for this user.",
                error_code="JOIN_REQUEST_NOT_FOUND",
            )

        updated = await self._join_request_repo.update_status(
            request.id,
            JoinRequestStatus.REJECTED,
            reviewed_by=current_user_id,
            rejection_reason=rejection_reason,
        )
        return JoinRequestResponse.model_validate(updated)

    # ------------------------------------------------------------------
    # CANCEL (requester withdraws their own request)
    # ------------------------------------------------------------------

    async def cancel_request(
        self,
        expedition_id: UUID,
        current_user_id: UUID,
    ) -> None:
        """Cancel the current user's own pending join request."""
        request = await self._join_request_repo.get_by_expedition_and_user(
            expedition_id, current_user_id
        )
        if not request or request.status != JoinRequestStatus.PENDING:
            raise NotFoundException(
                "No pending join request found to cancel.",
                error_code="JOIN_REQUEST_NOT_FOUND",
            )
        await self._join_request_repo.update_status(
            request.id, JoinRequestStatus.CANCELLED
        )

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    async def _require_organiser_or_co(self, expedition_id: UUID, user_id: UUID) -> None:
        participant = await self._participant_repo.get_by_expedition_and_user(
            expedition_id, user_id
        )
        if not participant or participant.role not in (
            ParticipantRole.ORGANIZER,
            ParticipantRole.CO_ORGANIZER,
        ):
            raise ForbiddenException(
                "Only the organiser or co-organiser can manage join requests.",
                error_code="NOT_ORGANISER_OR_CO",
            )
