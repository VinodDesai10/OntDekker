"""
GuideLanguageRepository — persistence layer for GuideLanguage.

Responsibilities:
  - Add / list / delete spoken languages for a guide
  - Pre-insert duplicate check on (guide_id, language)
"""

from __future__ import annotations

import uuid
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guide_language import GuideLanguage


class GuideLanguageRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # DUPLICATE CHECK
    # ------------------------------------------------------------------

    async def get_by_guide_and_language(
        self,
        guide_id: UUID,
        language: str,
    ) -> GuideLanguage | None:
        """Check if a guide already has this language listed.

        Used before insert to give a clean 409 rather than a DB
        IntegrityError on uq_guide_language_guide_language.
        """
        stmt = (
            select(GuideLanguage)
            .where(GuideLanguage.guide_id == guide_id)
            .where(GuideLanguage.language == language)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def add(self, *, guide_id: UUID, language: str) -> GuideLanguage:
        """Insert a new language entry for a guide."""
        lang = GuideLanguage(
            id=uuid.uuid4(),
            guide_id=guide_id,
            language=language,
        )
        self._session.add(lang)
        await self._session.flush()
        await self._session.refresh(lang)
        return lang

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_by_id(self, language_id: UUID) -> GuideLanguage | None:
        """Fetch a single language entry by primary key."""
        stmt = select(GuideLanguage).where(GuideLanguage.id == language_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_guide(self, guide_id: UUID) -> Sequence[GuideLanguage]:
        """Return all language entries for a guide, ordered alphabetically."""
        stmt = (
            select(GuideLanguage)
            .where(GuideLanguage.guide_id == guide_id)
            .order_by(GuideLanguage.language.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    async def delete(self, language_id: UUID) -> bool:
        """Hard-delete a language entry. Returns True if found and deleted."""
        lang = await self.get_by_id(language_id)
        if lang is None:
            return False
        await self._session.delete(lang)
        await self._session.flush()
        return True

    async def delete_all_for_guide(self, guide_id: UUID) -> int:
        """Hard-delete all language entries for a guide.

        Used when replacing the entire language list in a bulk update.
        """
        languages = await self.list_by_guide(guide_id)
        count = len(languages)
        for lang in languages:
            await self._session.delete(lang)
        if count:
            await self._session.flush()
        return count

    # ------------------------------------------------------------------
    # COUNT
    # ------------------------------------------------------------------

    async def count_by_guide(self, guide_id: UUID) -> int:
        """Return the number of languages listed for a guide."""
        stmt = (
            select(func.count())
            .select_from(GuideLanguage)
            .where(GuideLanguage.guide_id == guide_id)
        )
        return (await self._session.execute(stmt)).scalar_one()
