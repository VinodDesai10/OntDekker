"""
DiscussionRepository — persistence layer for ExpeditionDiscussionMessage.

Responsibilities:
  - Create a new discussion message
  - Paginate messages for an expedition (oldest → newest)
  - Count total messages for an expedition (for pagination metadata)
"""

from __future__ import annotations

import uuid
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discussion import ExpeditionDiscussionMessage


class DiscussionRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        expedition_id: UUID,
        author_id: UUID,
        content: str,
    ) -> ExpeditionDiscussionMessage:
        """Persist a new discussion message and return it with DB-assigned fields."""
        message = ExpeditionDiscussionMessage(
            id=uuid.uuid4(),
            expedition_id=expedition_id,
            author_id=author_id,
            content=content,
        )
        self._session.add(message)
        await self._session.flush()
        await self._session.refresh(message)
        return message

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def list_by_expedition(
        self,
        expedition_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> Sequence[ExpeditionDiscussionMessage]:
        """Return a page of messages for an expedition, ordered oldest → newest.

        page      — 1-indexed.
        page_size — number of messages per page (default 50, max 100).
        """
        offset = (page - 1) * page_size
        stmt = (
            select(ExpeditionDiscussionMessage)
            .where(ExpeditionDiscussionMessage.expedition_id == expedition_id)
            .order_by(ExpeditionDiscussionMessage.created_at.asc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_by_expedition(self, expedition_id: UUID) -> int:
        """Return the total number of messages for an expedition."""
        stmt = (
            select(func.count())
            .select_from(ExpeditionDiscussionMessage)
            .where(ExpeditionDiscussionMessage.expedition_id == expedition_id)
        )
        return (await self._session.execute(stmt)).scalar_one()
