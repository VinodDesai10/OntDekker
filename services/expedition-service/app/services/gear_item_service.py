"""
GearItemService — business logic for the Pack Weight Optimizer.

Rules enforced:
  - Only active participants can add/edit gear items
  - Only the item adder or organiser can delete or update an item
  - Gear management is available on DRAFT, PUBLISHED, and ACTIVE expeditions

Weight classification (service-layer constants, not stored in DB):
  ULTRALIGHT  : base_pack_grams < 5,000
  LIGHTWEIGHT : base_pack_grams < 9,000
  STANDARD    : base_pack_grams < 18,000
  HEAVY       : base_pack_grams >= 18,000
"""

from __future__ import annotations

from uuid import UUID

from shared import ForbiddenException, NotFoundException, ValidationException

from app.models.expedition import ExpeditionStatus
from app.models.gear_item import GearCategory
from app.models.participant import ParticipantRole
from app.repositories.expedition_repository import ExpeditionRepository
from app.repositories.gear_item_repository import GearItemRepository
from app.repositories.participant_repository import ParticipantRepository
from app.schemas.gear_item import (
    GearItemCreate,
    GearItemResponse,
    GearItemUpdate,
    GearListResponse,
    PackWeightClassification,
    PackWeightSummary,
)

_GEAR_EDITABLE_STATUSES = {
    ExpeditionStatus.DRAFT,
    ExpeditionStatus.PUBLISHED,
    ExpeditionStatus.ACTIVE,
}

# Weight classification thresholds in grams (based on BASE_PACK only)
_ULTRALIGHT_THRESHOLD  = 5_000
_LIGHTWEIGHT_THRESHOLD = 9_000
_STANDARD_THRESHOLD    = 18_000


def _classify_weight(base_pack_grams: int) -> PackWeightClassification:
    if base_pack_grams < _ULTRALIGHT_THRESHOLD:
        return PackWeightClassification.ULTRALIGHT
    if base_pack_grams < _LIGHTWEIGHT_THRESHOLD:
        return PackWeightClassification.LIGHTWEIGHT
    if base_pack_grams < _STANDARD_THRESHOLD:
        return PackWeightClassification.STANDARD
    return PackWeightClassification.HEAVY


class GearItemService:

    def __init__(
        self,
        expedition_repo: ExpeditionRepository,
        gear_repo: GearItemRepository,
        participant_repo: ParticipantRepository,
    ) -> None:
        self._expedition_repo = expedition_repo
        self._gear_repo = gear_repo
        self._participant_repo = participant_repo

    async def get_gear_list(
        self, expedition_id: UUID, current_user_id: UUID
    ) -> GearListResponse:
        """Return all gear items + computed weight summary."""
        await self._require_participant(expedition_id, current_user_id)
        items = await self._gear_repo.list_by_expedition(expedition_id)
        packed_count = await self._gear_repo.count_packed(expedition_id)
        weight_by_category = await self._gear_repo.get_weight_totals_by_category(
            expedition_id
        )

        base_pack_grams  = weight_by_category.get(GearCategory.BASE_PACK,  0)
        consumables_grams = weight_by_category.get(GearCategory.CONSUMABLES, 0)
        worn_gear_grams  = weight_by_category.get(GearCategory.WORN_GEAR,  0)
        total_weight     = base_pack_grams + consumables_grams + worn_gear_grams

        summary = PackWeightSummary(
            total_weight_grams=total_weight,
            base_pack_grams=base_pack_grams,
            consumables_grams=consumables_grams,
            worn_gear_grams=worn_gear_grams,
            packed_items_count=packed_count,
            total_items_count=len(items),
            classification=_classify_weight(base_pack_grams),
        )
        return GearListResponse(
            expedition_id=expedition_id,
            items=[GearItemResponse.model_validate(i) for i in items],
            summary=summary,
        )

    async def add_item(
        self,
        expedition_id: UUID,
        payload: GearItemCreate,
        current_user_id: UUID,
    ) -> GearItemResponse:
        """Add a gear item. User must be an active participant."""
        await self._require_editable_participant(expedition_id, current_user_id)
        item = await self._gear_repo.add(
            expedition_id=expedition_id,
            added_by=current_user_id,
            name=payload.name,
            category=payload.category,
            weight_grams=payload.weight_grams,
            quantity=payload.quantity,
            is_packed=payload.is_packed,
        )
        return GearItemResponse.model_validate(item)

    async def update_item(
        self,
        expedition_id: UUID,
        item_id: UUID,
        payload: GearItemUpdate,
        current_user_id: UUID,
    ) -> GearItemResponse:
        """Update a gear item. Adder or organiser only."""
        await self._require_editable_participant(expedition_id, current_user_id)
        item = await self._gear_repo.get_by_id(item_id)
        if not item or item.expedition_id != expedition_id:
            raise NotFoundException("Gear item not found.", error_code="GEAR_ITEM_NOT_FOUND")
        await self._require_adder_or_organiser(expedition_id, item.added_by, current_user_id)
        update_data = payload.model_dump(exclude_none=True)
        updated = await self._gear_repo.update(item_id, **update_data)
        return GearItemResponse.model_validate(updated)

    async def delete_item(
        self,
        expedition_id: UUID,
        item_id: UUID,
        current_user_id: UUID,
    ) -> None:
        """Delete a gear item. Adder or organiser only."""
        await self._require_editable_participant(expedition_id, current_user_id)
        item = await self._gear_repo.get_by_id(item_id)
        if not item or item.expedition_id != expedition_id:
            raise NotFoundException("Gear item not found.", error_code="GEAR_ITEM_NOT_FOUND")
        await self._require_adder_or_organiser(expedition_id, item.added_by, current_user_id)
        await self._gear_repo.delete(item_id)

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    async def _require_participant(self, expedition_id: UUID, user_id: UUID) -> None:
        if not await self._expedition_repo.exists(expedition_id):
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )
        if not await self._participant_repo.is_participant(expedition_id, user_id):
            raise ForbiddenException(
                "Only expedition participants can access gear items.",
                error_code="NOT_PARTICIPANT",
            )

    async def _require_editable_participant(
        self, expedition_id: UUID, user_id: UUID
    ) -> None:
        expedition = await self._expedition_repo.get_by_id(expedition_id)
        if not expedition:
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )
        if expedition.status not in _GEAR_EDITABLE_STATUSES:
            raise ValidationException(
                f"Cannot modify gear for an expedition with status '{expedition.status}'.",
                error_code="EXPEDITION_NOT_EDITABLE",
            )
        if not await self._participant_repo.is_participant(expedition_id, user_id):
            raise ForbiddenException(
                "Only expedition participants can manage gear items.",
                error_code="NOT_PARTICIPANT",
            )

    async def _require_adder_or_organiser(
        self, expedition_id: UUID, adder_id: UUID, current_user_id: UUID
    ) -> None:
        if current_user_id == adder_id:
            return
        participant = await self._participant_repo.get_by_expedition_and_user(
            expedition_id, current_user_id
        )
        if not participant or participant.role not in (
            ParticipantRole.ORGANIZER,
            ParticipantRole.CO_ORGANIZER,
        ):
            raise ForbiddenException(
                "Only the item owner or expedition organiser can modify this gear item.",
                error_code="NOT_ITEM_OWNER",
            )
