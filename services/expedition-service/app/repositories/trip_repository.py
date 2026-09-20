"""
TripRepository — persistence for the /api/v1/trips surface.

Wraps queries against the expeditions + expedition_participants tables.
Returns raw ORM objects; the service layer builds Pydantic responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expedition import Expedition, ExpeditionStatus, ExpeditionVisibility
from app.models.participant import ExpeditionParticipant, ParticipantStatus
from app.schemas.trip import TripFilter


class TripRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        organizer_id: UUID,
        title: str,
        destination: str,
        community_id: Optional[UUID] = None,
        description: Optional[str] = None,
        cover_image_url: Optional[str] = None,
        start_date=None,
        end_date=None,
        budget=None,
        max_participants: int = 1,
        visibility: ExpeditionVisibility = ExpeditionVisibility.PUBLIC,
        created_by: Optional[UUID] = None,
    ) -> Expedition:
        expedition = Expedition(
            id=uuid.uuid4(),
            community_id=community_id,
            organizer_id=organizer_id,
            title=title,
            destination=destination,
            description=description,
            cover_image_url=cover_image_url,
            start_date=start_date,
            end_date=end_date,
            max_participants=max_participants,
            budget=budget,
            visibility=visibility,
            status=ExpeditionStatus.PUBLISHED,   # trips start PUBLISHED, not DRAFT
            created_by=created_by,
            updated_by=created_by,
        )
        self._session.add(expedition)
        await self._session.flush()
        await self._session.refresh(expedition)
        return expedition

    # ------------------------------------------------------------------
    # READ — single
    # ------------------------------------------------------------------

    async def get_by_id(self, trip_id: UUID) -> Optional[Expedition]:
        stmt = (
            select(Expedition)
            .where(Expedition.id == trip_id)
            .where(Expedition.is_deleted.is_(False))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # READ — paginated list with search / filter
    # ------------------------------------------------------------------

    async def list_trips(
        self, filters: TripFilter
    ) -> tuple[Sequence[Expedition], int]:
        base = (
            select(Expedition)
            .where(Expedition.is_deleted.is_(False))
            .where(Expedition.visibility == ExpeditionVisibility.PUBLIC)
        )

        if filters.search:
            term = f"%{filters.search}%"
            base = base.where(
                or_(
                    Expedition.title.ilike(term),
                    Expedition.destination.ilike(term),
                )
            )
        if filters.community_id is not None:
            base = base.where(Expedition.community_id == filters.community_id)
        if filters.personal_only:
            base = base.where(Expedition.community_id.is_(None))
        if filters.status is not None:
            base = base.where(Expedition.status == filters.status)

        count_stmt = select(func.count()).select_from(base.subquery())
        total: int = (await self._session.execute(count_stmt)).scalar_one()

        offset = (filters.page - 1) * filters.page_size
        page_stmt = (
            base.order_by(Expedition.created_at.desc())
            .offset(offset)
            .limit(filters.page_size)
        )
        result = await self._session.execute(page_stmt)
        return result.scalars().all(), total

    # ------------------------------------------------------------------
    # READ — trips where user is a participant (My Trips)
    # ------------------------------------------------------------------

    async def list_my_trips(
        self,
        user_id: UUID,
        status: Optional[ExpeditionStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Expedition], int]:
        base = (
            select(Expedition)
            .join(
                ExpeditionParticipant,
                ExpeditionParticipant.expedition_id == Expedition.id,
            )
            .where(ExpeditionParticipant.user_id == user_id)
            .where(ExpeditionParticipant.status == ParticipantStatus.ACTIVE)
            .where(Expedition.is_deleted.is_(False))
        )
        if status is not None:
            base = base.where(Expedition.status == status)

        count_stmt = select(func.count()).select_from(base.subquery())
        total: int = (await self._session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        page_stmt = (
            base.order_by(Expedition.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._session.execute(page_stmt)
        return result.scalars().all(), total

    # ------------------------------------------------------------------
    # PARTICIPANT COUNT (lightweight, avoids loading the full relationship)
    # ------------------------------------------------------------------

    async def count_active_participants(self, trip_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ExpeditionParticipant)
            .where(ExpeditionParticipant.expedition_id == trip_id)
            .where(ExpeditionParticipant.status == ParticipantStatus.ACTIVE)
        )
        return (await self._session.execute(stmt)).scalar_one()

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    async def update(
        self,
        trip_id: UUID,
        *,
        updated_by: Optional[UUID] = None,
        **fields,
    ) -> Optional[Expedition]:
        updates = {k: v for k, v in fields.items() if v is not None}
        if not updates:
            return await self.get_by_id(trip_id)

        updates["updated_by"] = updated_by
        updates["updated_at"] = datetime.now(timezone.utc)

        stmt = (
            update(Expedition)
            .where(Expedition.id == trip_id)
            .where(Expedition.is_deleted.is_(False))
            .values(**updates)
            .returning(Expedition)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # SOFT DELETE
    # ------------------------------------------------------------------

    async def soft_delete(self, trip_id: UUID, *, deleted_by: Optional[UUID] = None) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Expedition)
            .where(Expedition.id == trip_id)
            .where(Expedition.is_deleted.is_(False))
            .values(is_deleted=True, deleted_at=now, deleted_by=deleted_by, updated_at=now)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0
