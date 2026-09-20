"""
GuideAvailabilityService — business logic for managing a guide's
availability status and optional note (guide_availability table).

The table is one-to-one with guide_profiles. The repository implements
an upsert: if no availability record exists yet, one is created on the
first PUT; subsequent calls update the existing row.

Rules:
  - Only the guide owner may update their availability.
  - Reading availability is public (anyone may view a guide's availability).
  - If no availability record exists, the service returns a sensible
    default (AVAILABLE with no note) rather than a 404.
"""

from __future__ import annotations

from uuid import UUID

from shared import (
    ForbiddenException,
    NotFoundException,
)
from shared.logging import setup_logging

from app.models.guide_availability import AvailabilityStatus
from app.repositories.guide_availability_repository import GuideAvailabilityRepository
from app.repositories.guide_profile_repository import GuideProfileRepository
from app.schemas.guide_availability import (
    GuideAvailabilityResponse,
    GuideAvailabilityUpdate,
)

logger = setup_logging(service_name="guide-service", log_level="INFO")


class GuideAvailabilityService:
    """Coordinates business logic for guide availability management."""

    def __init__(
        self,
        profile_repo: GuideProfileRepository,
        availability_repo: GuideAvailabilityRepository,
    ) -> None:
        self._profile_repo = profile_repo
        self._availability_repo = availability_repo

    # ------------------------------------------------------------------
    # PRIVATE HELPER — guard
    # ------------------------------------------------------------------

    async def _require_profile_exists(self, guide_id: UUID) -> None:
        """Raise 404 if the guide profile does not exist (soft-delete aware)."""
        profile = await self._profile_repo.get_by_id(guide_id)
        if not profile:
            raise NotFoundException(
                f"Guide profile {guide_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )

    async def _require_guide_owner(
        self,
        guide_id: UUID,
        current_user_id: UUID,
    ) -> None:
        """Raise 404 if the profile doesn't exist; 403 if caller is not owner."""
        profile = await self._profile_repo.get_by_id(guide_id)
        if not profile:
            raise NotFoundException(
                f"Guide profile {guide_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )
        if profile.user_id != current_user_id:
            raise ForbiddenException(
                "Only the guide owner can update availability.",
                error_code="NOT_PROFILE_OWNER",
            )

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_availability(
        self,
        guide_id: UUID,
    ) -> GuideAvailabilityResponse:
        """Return the availability record for a guide (public).

        If no record has been set, returns a synthetic default
        (AVAILABLE, no note) to avoid surprising 404 responses
        on newly-created profiles.
        """
        await self._require_profile_exists(guide_id)

        availability = await self._availability_repo.get_by_guide_id(guide_id)
        if not availability:
            # Return a synthetic default without persisting it
            # The record will be created on the first PUT.
            import uuid as _uuid
            from datetime import datetime, timezone
            from app.models.guide_availability import GuideAvailability
            synthetic = GuideAvailability(
                id=_uuid.uuid4(),
                guide_id=guide_id,
                status=AvailabilityStatus.AVAILABLE,
                note=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            return GuideAvailabilityResponse.model_validate(synthetic)

        return GuideAvailabilityResponse.model_validate(availability)

    # ------------------------------------------------------------------
    # UPSERT
    # ------------------------------------------------------------------

    async def set_availability(
        self,
        guide_id: UUID,
        payload: GuideAvailabilityUpdate,
        current_user_id: UUID,
    ) -> GuideAvailabilityResponse:
        """Create or update the availability record for a guide.

        Uses repository upsert: inserts on first call, updates on
        subsequent calls for the same guide_id.

        Raises 403 if caller is not the guide owner.
        """
        await self._require_guide_owner(guide_id, current_user_id)

        availability = await self._availability_repo.upsert(
            guide_id,
            status=payload.status,
            note=payload.note,
        )
        return GuideAvailabilityResponse.model_validate(availability)
