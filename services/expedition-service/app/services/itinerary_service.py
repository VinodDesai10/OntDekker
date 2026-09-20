"""
ItineraryService — business logic for expedition itinerary management.

Rules enforced:
  - Itinerary can only be edited on DRAFT, PUBLISHED, or ACTIVE expeditions
  - Only organiser or co-organiser can modify the itinerary
  - Bulk replace is atomic (delete-then-insert in one transaction flush)
  - day_number uniqueness within the payload is validated in the schema
"""

from __future__ import annotations

from uuid import UUID

from shared import ForbiddenException, NotFoundException, ValidationException

from app.models.expedition import ExpeditionStatus
from app.models.participant import ParticipantRole
from app.repositories.expedition_repository import ExpeditionRepository
from app.repositories.itinerary_repository import ItineraryRepository
from app.repositories.participant_repository import ParticipantRepository
from app.schemas.itinerary import (
    ItineraryBulkUpdate,
    ItineraryDayCreate,
    ItineraryDayResponse,
    ItineraryDayUpdate,
    ItineraryResponse,
)

_EDITABLE_STATUSES = {
    ExpeditionStatus.DRAFT,
    ExpeditionStatus.PUBLISHED,
    ExpeditionStatus.ACTIVE,
}


class ItineraryService:

    def __init__(
        self,
        expedition_repo: ExpeditionRepository,
        itinerary_repo: ItineraryRepository,
        participant_repo: ParticipantRepository,
    ) -> None:
        self._expedition_repo = expedition_repo
        self._itinerary_repo = itinerary_repo
        self._participant_repo = participant_repo

    async def get_itinerary(self, expedition_id: UUID) -> ItineraryResponse:
        """Return all itinerary days for an expedition."""
        if not await self._expedition_repo.exists(expedition_id):
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )
        days = await self._itinerary_repo.get_by_expedition(expedition_id)
        return ItineraryResponse(
            expedition_id=expedition_id,
            days=[ItineraryDayResponse.model_validate(d) for d in days],
            total_days=len(days),
        )

    async def replace_itinerary(
        self,
        expedition_id: UUID,
        payload: ItineraryBulkUpdate,
        current_user_id: UUID,
    ) -> ItineraryResponse:
        """Replace the full itinerary atomically. Organiser/co-organiser only."""
        expedition = await self._require_editable(expedition_id, current_user_id)
        new_days = await self._itinerary_repo.replace_all(
            expedition_id, payload.days
        )
        return ItineraryResponse(
            expedition_id=expedition_id,
            days=[ItineraryDayResponse.model_validate(d) for d in new_days],
            total_days=len(new_days),
        )

    async def add_day(
        self,
        expedition_id: UUID,
        payload: ItineraryDayCreate,
        current_user_id: UUID,
    ) -> ItineraryDayResponse:
        """Add a single itinerary day."""
        await self._require_editable(expedition_id, current_user_id)
        # Check for duplicate day_number
        existing = await self._itinerary_repo.get_day(expedition_id, payload.day_number)
        if existing:
            raise ValidationException(
                f"Day {payload.day_number} already exists in this itinerary.",
                error_code="DUPLICATE_DAY_NUMBER",
            )
        day = await self._itinerary_repo.add_day(expedition_id, payload)
        return ItineraryDayResponse.model_validate(day)

    async def update_day(
        self,
        expedition_id: UUID,
        day_number: int,
        payload: ItineraryDayUpdate,
        current_user_id: UUID,
    ) -> ItineraryDayResponse:
        """Partially update a single itinerary day."""
        await self._require_editable(expedition_id, current_user_id)
        update_data = payload.model_dump(exclude_none=True)
        updated = await self._itinerary_repo.update_day(
            expedition_id, day_number, **update_data
        )
        if not updated:
            raise NotFoundException(
                f"Day {day_number} not found in this expedition's itinerary.",
                error_code="ITINERARY_DAY_NOT_FOUND",
            )
        return ItineraryDayResponse.model_validate(updated)

    async def delete_day(
        self,
        expedition_id: UUID,
        day_number: int,
        current_user_id: UUID,
    ) -> None:
        """Delete a single itinerary day."""
        await self._require_editable(expedition_id, current_user_id)
        deleted = await self._itinerary_repo.delete_day(expedition_id, day_number)
        if not deleted:
            raise NotFoundException(
                f"Day {day_number} not found in this expedition's itinerary.",
                error_code="ITINERARY_DAY_NOT_FOUND",
            )

    async def _require_editable(self, expedition_id: UUID, user_id: UUID):
        expedition = await self._expedition_repo.get_by_id(expedition_id)
        if not expedition:
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )
        if expedition.status not in _EDITABLE_STATUSES:
            raise ValidationException(
                f"Cannot edit itinerary for an expedition with status '{expedition.status}'.",
                error_code="EXPEDITION_NOT_EDITABLE",
            )
        participant = await self._participant_repo.get_by_expedition_and_user(
            expedition_id, user_id
        )
        if not participant or participant.role not in (
            ParticipantRole.ORGANIZER,
            ParticipantRole.CO_ORGANIZER,
        ):
            raise ForbiddenException(
                "Only the organiser or co-organiser can modify the itinerary.",
                error_code="NOT_ORGANISER_OR_CO",
            )
        return expedition
