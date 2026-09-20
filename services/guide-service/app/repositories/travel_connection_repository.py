"""
TravelConnectionRepository — persistence layer for TravelConnection.

Responsibilities:
  - Create and fetch guide–traveler connections
  - Increment interaction counters
  - Toggle the bookmark flag
  - List a traveler's connections (My Guides view)

Connections are created by the service layer in response to events
(e.g. EXPEDITION_COMPLETED). There is no direct user-facing create endpoint.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.travel_connection import TravelConnection


class TravelConnectionRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # DUPLICATE CHECK
    # ------------------------------------------------------------------

    async def get_by_guide_and_traveler(
        self,
        guide_id: UUID,
        traveler_id: UUID,
    ) -> Optional[TravelConnection]:
        """Fetch the connection record for a guide–traveler pair.

        Returns None if no connection exists yet.
        Used to check existence before creating, and to retrieve for
        counter increments.
        """
        stmt = (
            select(TravelConnection)
            .where(TravelConnection.guide_id == guide_id)
            .where(TravelConnection.traveler_id == traveler_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        guide_id: UUID,
        traveler_id: UUID,
        first_met: Optional[datetime] = None,
    ) -> TravelConnection:
        """Insert a new travel connection record.

        Counters start at 0; they are incremented separately.
        """
        now = datetime.now(timezone.utc)
        connection = TravelConnection(
            id=uuid.uuid4(),
            guide_id=guide_id,
            traveler_id=traveler_id,
            first_met=first_met or now,
            last_interaction=first_met or now,
            expeditions_together=0,
            conversation_count=0,
            photos_shared=0,
            bookmarked=False,
        )
        self._session.add(connection)
        await self._session.flush()
        await self._session.refresh(connection)
        return connection

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_by_id(self, connection_id: UUID) -> Optional[TravelConnection]:
        """Fetch a single connection record by primary key."""
        stmt = select(TravelConnection).where(TravelConnection.id == connection_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_traveler(
        self,
        traveler_id: UUID,
        *,
        bookmarked_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[TravelConnection], int]:
        """Return a paginated list of connections for a traveler (My Guides).

        Returns (items, total_count).
        """
        base_stmt = (
            select(TravelConnection)
            .where(TravelConnection.traveler_id == traveler_id)
        )
        if bookmarked_only:
            base_stmt = base_stmt.where(TravelConnection.bookmarked.is_(True))

        total: int = (
            await self._session.execute(
                select(func.count()).select_from(base_stmt.subquery())
            )
        ).scalar_one()

        offset = (page - 1) * page_size
        page_stmt = (
            base_stmt
            .order_by(
                TravelConnection.bookmarked.desc(),
                TravelConnection.last_interaction.desc().nulls_last(),
            )
            .offset(offset)
            .limit(page_size)
        )
        result = await self._session.execute(page_stmt)
        return result.scalars().all(), total

    async def list_by_guide(
        self,
        guide_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[TravelConnection], int]:
        """Return a paginated list of connections for a guide."""
        base_stmt = (
            select(TravelConnection)
            .where(TravelConnection.guide_id == guide_id)
        )
        total: int = (
            await self._session.execute(
                select(func.count()).select_from(base_stmt.subquery())
            )
        ).scalar_one()

        offset = (page - 1) * page_size
        page_stmt = (
            base_stmt
            .order_by(TravelConnection.last_interaction.desc().nulls_last())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._session.execute(page_stmt)
        return result.scalars().all(), total

    # ------------------------------------------------------------------
    # UPDATE — counter increments
    # ------------------------------------------------------------------

    async def increment_expedition_count(
        self,
        guide_id: UUID,
        traveler_id: UUID,
    ) -> Optional[TravelConnection]:
        """Increment expeditions_together by 1 and update last_interaction."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(TravelConnection)
            .where(TravelConnection.guide_id == guide_id)
            .where(TravelConnection.traveler_id == traveler_id)
            .values(
                expeditions_together=TravelConnection.expeditions_together + 1,
                last_interaction=now,
                updated_at=now,
            )
            .returning(TravelConnection)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_conversation_count(
        self,
        guide_id: UUID,
        traveler_id: UUID,
    ) -> Optional[TravelConnection]:
        """Increment conversation_count by 1 and update last_interaction."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(TravelConnection)
            .where(TravelConnection.guide_id == guide_id)
            .where(TravelConnection.traveler_id == traveler_id)
            .values(
                conversation_count=TravelConnection.conversation_count + 1,
                last_interaction=now,
                updated_at=now,
            )
            .returning(TravelConnection)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_photos_shared(
        self,
        guide_id: UUID,
        traveler_id: UUID,
        count: int = 1,
    ) -> Optional[TravelConnection]:
        """Increment photos_shared by count (default 1)."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(TravelConnection)
            .where(TravelConnection.guide_id == guide_id)
            .where(TravelConnection.traveler_id == traveler_id)
            .values(
                photos_shared=TravelConnection.photos_shared + count,
                updated_at=now,
            )
            .returning(TravelConnection)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # UPDATE — bookmark toggle
    # ------------------------------------------------------------------

    async def set_bookmark(
        self,
        guide_id: UUID,
        traveler_id: UUID,
        bookmarked: bool,
    ) -> Optional[TravelConnection]:
        """Set the bookmarked flag to True or False."""
        stmt = (
            update(TravelConnection)
            .where(TravelConnection.guide_id == guide_id)
            .where(TravelConnection.traveler_id == traveler_id)
            .values(
                bookmarked=bookmarked,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(TravelConnection)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
