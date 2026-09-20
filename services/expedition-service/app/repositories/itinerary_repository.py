"""
ItineraryRepository — persistence layer for ExpeditionItinerary.

Supports both single-day operations and the bulk-replace pattern
(PUT /itinerary replaces the whole set atomically).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Sequence
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.itinerary import ExpeditionItinerary
from app.schemas.itinerary import ItineraryDayCreate


class ItineraryRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CREATE — single day
    # ------------------------------------------------------------------

    async def add_day(
        self,
        expedition_id: UUID,
        day_data: ItineraryDayCreate,
    ) -> ExpeditionItinerary:
        """Insert a single itinerary day."""
        day = ExpeditionItinerary(
            id=uuid.uuid4(),
            expedition_id=expedition_id,
            day_number=day_data.day_number,
            title=day_data.title,
            description=day_data.description,
            location=day_data.location,
            activity_time=day_data.activity_time,
            notes=day_data.notes,
        )
        self._session.add(day)
        await self._session.flush()
        await self._session.refresh(day)
        return day

    # ------------------------------------------------------------------
    # CREATE — bulk replace (used by PUT /itinerary)
    # ------------------------------------------------------------------

    async def replace_all(
        self,
        expedition_id: UUID,
        days: List[ItineraryDayCreate],
    ) -> Sequence[ExpeditionItinerary]:
        """Delete all existing days and insert the new set atomically.

        This is a single-transaction operation — the service layer
        ensures the session is committed only after both steps succeed.
        """
        # Delete all existing days for this expedition
        await self._session.execute(
            delete(ExpeditionItinerary).where(
                ExpeditionItinerary.expedition_id == expedition_id
            )
        )

        # Insert the new set ordered by day_number
        new_days: list[ExpeditionItinerary] = []
        for day_data in sorted(days, key=lambda d: d.day_number):
            day = ExpeditionItinerary(
                id=uuid.uuid4(),
                expedition_id=expedition_id,
                day_number=day_data.day_number,
                title=day_data.title,
                description=day_data.description,
                location=day_data.location,
                activity_time=day_data.activity_time,
                notes=day_data.notes,
            )
            self._session.add(day)
            new_days.append(day)

        await self._session.flush()
        for day in new_days:
            await self._session.refresh(day)
        return new_days

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_by_expedition(
        self, expedition_id: UUID
    ) -> Sequence[ExpeditionItinerary]:
        """Return all itinerary days for an expedition, ordered by day_number."""
        stmt = (
            select(ExpeditionItinerary)
            .where(ExpeditionItinerary.expedition_id == expedition_id)
            .order_by(ExpeditionItinerary.day_number.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_day(
        self, expedition_id: UUID, day_number: int
    ) -> Optional[ExpeditionItinerary]:
        """Fetch a single itinerary day by expedition + day_number."""
        stmt = (
            select(ExpeditionItinerary)
            .where(ExpeditionItinerary.expedition_id == expedition_id)
            .where(ExpeditionItinerary.day_number == day_number)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # UPDATE — single day
    # ------------------------------------------------------------------

    async def update_day(
        self,
        expedition_id: UUID,
        day_number: int,
        **fields,
    ) -> Optional[ExpeditionItinerary]:
        """Partially update a single itinerary day."""
        updates = {k: v for k, v in fields.items() if v is not None}
        if not updates:
            return await self.get_day(expedition_id, day_number)

        updates["updated_at"] = datetime.now(timezone.utc)
        stmt = (
            update(ExpeditionItinerary)
            .where(ExpeditionItinerary.expedition_id == expedition_id)
            .where(ExpeditionItinerary.day_number == day_number)
            .values(**updates)
            .returning(ExpeditionItinerary)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # DELETE — single day
    # ------------------------------------------------------------------

    async def delete_day(
        self, expedition_id: UUID, day_number: int
    ) -> bool:
        """Delete a single itinerary day. Returns True if a row was deleted."""
        stmt = (
            delete(ExpeditionItinerary)
            .where(ExpeditionItinerary.expedition_id == expedition_id)
            .where(ExpeditionItinerary.day_number == day_number)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0
