"""
GuideAvailabilityRepository — persistence layer for GuideAvailability.

One-to-one with GuideProfile. Uses upsert-style logic: if no row exists
for the guide, a new row is inserted; otherwise the existing row is updated.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guide_availability import GuideAvailability, AvailabilityStatus


class GuideAvailabilityRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_by_guide_id(self, guide_id: UUID) -> Optional[GuideAvailability]:
        """Fetch the availability record for a guide (None if not set yet)."""
        stmt = (
            select(GuideAvailability)
            .where(GuideAvailability.guide_id == guide_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # UPSERT — create if absent, update if present
    # ------------------------------------------------------------------

    async def upsert(
        self,
        guide_id: UUID,
        *,
        status: Optional[AvailabilityStatus] = None,
        note: Optional[str] = None,
    ) -> GuideAvailability:
        """Create or update the availability record for a guide.

        If no row exists, a new one is inserted with the provided values
        (defaulting status to AVAILABLE if not specified).
        If a row already exists, only the provided non-None values are updated.
        """
        existing = await self.get_by_guide_id(guide_id)

        if existing is None:
            # INSERT path
            avail = GuideAvailability(
                id=uuid.uuid4(),
                guide_id=guide_id,
                status=status if status is not None else AvailabilityStatus.AVAILABLE,
                note=note,
            )
            self._session.add(avail)
            await self._session.flush()
            await self._session.refresh(avail)
            return avail

        # UPDATE path — only write provided fields
        updates: dict = {"updated_at": datetime.now(timezone.utc)}
        if status is not None:
            updates["status"] = status
        if note is not None:
            updates["note"] = note

        stmt = (
            update(GuideAvailability)
            .where(GuideAvailability.guide_id == guide_id)
            .values(**updates)
            .returning(GuideAvailability)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
