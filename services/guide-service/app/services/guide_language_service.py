"""
GuideLanguageService — business logic for managing a guide's
spoken languages (guide_languages table).

Rules:
  - Only the guide owner may add or remove languages.
  - Duplicate languages (same guide_id + language, case-insensitive normalised
    to title-case) surface a clean 409.
  - No hard cap on languages (reasonable limits at the Pydantic layer).
  - Languages are hard-deleted (not a root aggregate).
"""

from __future__ import annotations

from typing import List
from uuid import UUID

from shared import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from shared.logging import setup_logging

from app.repositories.guide_language_repository import GuideLanguageRepository
from app.repositories.guide_profile_repository import GuideProfileRepository
from app.schemas.guide_language import GuideLanguageCreate, GuideLanguageResponse

logger = setup_logging(service_name="guide-service", log_level="INFO")


class GuideLanguageService:
    """Coordinates business logic for guide language management."""

    def __init__(
        self,
        profile_repo: GuideProfileRepository,
        language_repo: GuideLanguageRepository,
    ) -> None:
        self._profile_repo = profile_repo
        self._language_repo = language_repo

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
                "Only the guide owner can manage languages.",
                error_code="NOT_PROFILE_OWNER",
            )

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def list_languages(
        self,
        guide_id: UUID,
    ) -> List[GuideLanguageResponse]:
        """Return all languages for a guide profile (public read)."""
        profile = await self._profile_repo.get_by_id(guide_id)
        if not profile:
            raise NotFoundException(
                f"Guide profile {guide_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )
        languages = await self._language_repo.list_by_guide(guide_id)
        return [GuideLanguageResponse.model_validate(lang) for lang in languages]

    # ------------------------------------------------------------------
    # ADD
    # ------------------------------------------------------------------

    async def add_language(
        self,
        guide_id: UUID,
        payload: GuideLanguageCreate,
        current_user_id: UUID,
    ) -> GuideLanguageResponse:
        """Add a spoken language to a guide profile.

        Language name is normalised to title-case before duplicate check
        and insertion (e.g. "hindi" → "Hindi").

        Raises 403 if caller is not the guide owner.
        Raises 409 if the language is already listed.
        """
        await self._require_guide_owner(guide_id, current_user_id)

        # Normalise to title-case for consistent storage and dedup
        normalised = payload.language.strip().title()

        existing = await self._language_repo.get_by_guide_and_language(
            guide_id, normalised
        )
        if existing:
            raise ConflictException(
                f"'{normalised}' is already listed for this guide.",
                error_code="LANGUAGE_ALREADY_EXISTS",
            )

        language = await self._language_repo.add(
            guide_id=guide_id,
            language=normalised,
        )
        return GuideLanguageResponse.model_validate(language)

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    async def delete_language(
        self,
        guide_id: UUID,
        language_id: UUID,
        current_user_id: UUID,
    ) -> None:
        """Remove a language entry from a guide profile.

        Raises 403 if caller is not the guide owner.
        Raises 404 if the language entry does not exist or belongs to another guide.
        """
        await self._require_guide_owner(guide_id, current_user_id)

        language = await self._language_repo.get_by_id(language_id)
        if not language or language.guide_id != guide_id:
            raise NotFoundException(
                f"Language entry {language_id} not found for guide {guide_id}.",
                error_code="LANGUAGE_NOT_FOUND",
            )

        deleted = await self._language_repo.delete(language_id)
        if not deleted:
            raise NotFoundException(
                f"Language entry {language_id} not found.",
                error_code="LANGUAGE_NOT_FOUND",
            )
