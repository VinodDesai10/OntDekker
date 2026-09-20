"""
GuideLocationRepository — persistence layer for GuideLocation.

Responsibilities:
  - Add / list / delete geographic coverage areas for a guide
  - Pre-insert duplicate check on (guide_id, country, region, city)
"""

from __future__ import annotations

import uuid
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guide_location import GuideLocation


class GuideLocationRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # DUPLICATE CHECK
    # ------------------------------------------------------------------

    async def get_by_guide_and_location(
        self,
        guide_id: UUID,
        country: str,
        region: Optional[str],
        city: Optional[str],
    ) -> Optional[GuideLocation]:
        """Check if an identical location entry already exists.

        Used before insert to surface a clean 409 Conflict rather than
        a DB IntegrityError on uq_guide_location_guide_country_region_city.
        """
        stmt = (
            select(GuideLocation)
            .where(GuideLocation.guide_id == guide_id)
            .where(GuideLocation.country == country)
        )
        if region is not None:
            stmt = stmt.where(GuideLocation.region == region)
        else:
            stmt = stmt.where(GuideLocation.region.is_(None))

        if city is not None:
            stmt = stmt.where(GuideLocation.city == city)
        else:
            stmt = stmt.where(GuideLocation.city.is_(None))

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def add(
        self,
        *,
        guide_id: UUID,
        country: str,
        region: Optional[str] = None,
        city: Optional[str] = None,
    ) -> GuideLocation:
        """Insert a new location entry for a guide."""
        location = GuideLocation(
            id=uuid.uuid4(),
            guide_id=guide_id,
            country=country,
            region=region,
            city=city,
        )
        self._session.add(location)
        await self._session.flush()
        await self._session.refresh(location)
        return location

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_by_id(self, location_id: UUID) -> Optional[GuideLocation]:
        """Fetch a single location by primary key."""
        stmt = select(GuideLocation).where(GuideLocation.id == location_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_guide(self, guide_id: UUID) -> Sequence[GuideLocation]:
        """Return all location entries for a guide."""
        stmt = (
            select(GuideLocation)
            .where(GuideLocation.guide_id == guide_id)
            .order_by(GuideLocation.country.asc(), GuideLocation.region.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    async def delete(self, location_id: UUID) -> bool:
        """Hard-delete a location entry. Returns True if found and deleted."""
        location = await self.get_by_id(location_id)
        if location is None:
            return False
        await self._session.delete(location)
        await self._session.flush()
        return True

    async def delete_all_for_guide(self, guide_id: UUID) -> int:
        """Hard-delete all locations for a guide. Returns count deleted.

        Used when replacing the entire location list in a bulk update.
        """
        locations = await self.list_by_guide(guide_id)
        count = len(locations)
        for loc in locations:
            await self._session.delete(loc)
        if count:
            await self._session.flush()
        return count

    # ------------------------------------------------------------------
    # COUNT
    # ------------------------------------------------------------------

    async def count_by_guide(self, guide_id: UUID) -> int:
        """Return the number of locations for a guide."""
        stmt = (
            select(func.count())
            .select_from(GuideLocation)
            .where(GuideLocation.guide_id == guide_id)
        )
        return (await self._session.execute(stmt)).scalar_one()
