"""
GuideLocationService — business logic for managing a guide's
geographic coverage areas (guide_locations table).

Rules:
  - Only the guide owner (user_id matches JWT sub) may add or remove locations.
  - Duplicate locations (same guide_id + country + region + city) surface a
    clean 409 rather than a DB IntegrityError.
  - A guide may cover at most 20 locations (soft cap to prevent abuse).
  - Locations are hard-deleted (no soft delete — not a root aggregate).
"""

from __future__ import annotations

from typing import List
from uuid import UUID

from shared import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from shared.logging import setup_logging

from app.repositories.guide_location_repository import GuideLocationRepository
from app.repositories.guide_profile_repository import GuideProfileRepository
from app.schemas.guide_location import GuideLocationCreate, GuideLocationResponse

logger = setup_logging(service_name="guide-service", log_level="INFO")

_MAX_LOCATIONS_PER_GUIDE = 20


class GuideLocationService:
    """Coordinates business logic for guide location management."""

    def __init__(
        self,
        profile_repo: GuideProfileRepository,
        location_repo: GuideLocationRepository,
    ) -> None:
        self._profile_repo = profile_repo
        self._location_repo = location_repo

    # ------------------------------------------------------------------
    # PRIVATE HELPER — ownership guard
    # ------------------------------------------------------------------

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
                "Only the guide owner can manage locations.",
                error_code="NOT_PROFILE_OWNER",
            )

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def list_locations(
        self,
        guide_id: UUID,
    ) -> List[GuideLocationResponse]:
        """Return all locations for a guide profile."""
        # Confirm the profile exists (public read — no ownership check needed)
        profile = await self._profile_repo.get_by_id(guide_id)
        if not profile:
            raise NotFoundException(
                f"Guide profile {guide_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )
        locations = await self._location_repo.list_by_guide(guide_id)
        return [GuideLocationResponse.model_validate(loc) for loc in locations]

    # ------------------------------------------------------------------
    # ADD
    # ------------------------------------------------------------------

    async def add_location(
        self,
        guide_id: UUID,
        payload: GuideLocationCreate,
        current_user_id: UUID,
    ) -> GuideLocationResponse:
        """Add a new geographic coverage area to a guide profile.

        Raises 403 if caller is not the guide owner.
        Raises 409 if the location already exists.
        Raises 422 if the guide already has 20 locations.
        """
        await self._require_guide_owner(guide_id, current_user_id)

        # Duplicate check
        existing = await self._location_repo.get_by_guide_and_location(
            guide_id,
            payload.country,
            payload.region,
            payload.city,
        )
        if existing:
            raise ConflictException(
                "This location is already listed for the guide.",
                error_code="LOCATION_ALREADY_EXISTS",
            )

        # Soft cap
        count = await self._location_repo.count_by_guide(guide_id)
        if count >= _MAX_LOCATIONS_PER_GUIDE:
            raise ValidationException(
                f"A guide may not have more than {_MAX_LOCATIONS_PER_GUIDE} coverage areas.",
                error_code="LOCATION_LIMIT_EXCEEDED",
            )

        location = await self._location_repo.add(
            guide_id=guide_id,
            country=payload.country,
            region=payload.region,
            city=payload.city,
        )
        return GuideLocationResponse.model_validate(location)

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    async def delete_location(
        self,
        guide_id: UUID,
        location_id: UUID,
        current_user_id: UUID,
    ) -> None:
        """Remove a location entry from a guide profile.

        Raises 403 if caller is not the guide owner.
        Raises 404 if the location does not exist.
        """
        await self._require_guide_owner(guide_id, current_user_id)

        location = await self._location_repo.get_by_id(location_id)
        if not location or location.guide_id != guide_id:
            raise NotFoundException(
                f"Location {location_id} not found for guide {guide_id}.",
                error_code="LOCATION_NOT_FOUND",
            )

        deleted = await self._location_repo.delete(location_id)
        if not deleted:
            raise NotFoundException(
                f"Location {location_id} not found.",
                error_code="LOCATION_NOT_FOUND",
            )
