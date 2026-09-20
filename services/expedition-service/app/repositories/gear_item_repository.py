"""
GearItemRepository — persistence layer for GearItem (Pack Weight Optimizer).

Includes the raw weight aggregation query that the service layer uses
to build PackWeightSummary without pulling all rows into Python memory.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gear_item import GearCategory, GearItem


class GearItemRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def add(
        self,
        *,
        expedition_id: UUID,
        added_by: UUID,
        name: str,
        category: GearCategory = GearCategory.BASE_PACK,
        weight_grams: int = 0,
        quantity: int = 1,
        is_packed: bool = False,
    ) -> GearItem:
        """Insert a new gear item."""
        item = GearItem(
            id=uuid.uuid4(),
            expedition_id=expedition_id,
            added_by=added_by,
            name=name,
            category=category,
            weight_grams=weight_grams,
            quantity=quantity,
            is_packed=is_packed,
        )
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_by_id(self, item_id: UUID) -> Optional[GearItem]:
        """Fetch a single gear item by PK."""
        stmt = select(GearItem).where(GearItem.id == item_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_expedition(
        self,
        expedition_id: UUID,
        *,
        category: Optional[GearCategory] = None,
    ) -> Sequence[GearItem]:
        """Return all gear items for an expedition.

        Optionally filter by category (for per-category weight breakdown).
        """
        stmt = (
            select(GearItem)
            .where(GearItem.expedition_id == expedition_id)
        )
        if category is not None:
            stmt = stmt.where(GearItem.category == category)
        stmt = stmt.order_by(GearItem.category.asc(), GearItem.name.asc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_weight_totals_by_category(
        self, expedition_id: UUID
    ) -> dict[GearCategory, int]:
        """Return total effective weight per category using a DB aggregate.

        Effective weight = weight_grams * quantity for each item.
        Returns a dict: { GearCategory: total_grams }

        Running this in SQL avoids fetching every item row just to sum
        them in Python — important for expeditions with many gear items.
        """
        stmt = (
            select(
                GearItem.category,
                func.sum(GearItem.weight_grams * GearItem.quantity).label("total"),
            )
            .where(GearItem.expedition_id == expedition_id)
            .group_by(GearItem.category)
        )
        rows = (await self._session.execute(stmt)).all()
        return {row.category: int(row.total or 0) for row in rows}

    async def count_packed(self, expedition_id: UUID) -> int:
        """Count items with is_packed = True."""
        stmt = (
            select(func.count())
            .select_from(GearItem)
            .where(GearItem.expedition_id == expedition_id)
            .where(GearItem.is_packed.is_(True))
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def count_total(self, expedition_id: UUID) -> int:
        """Count all gear items for an expedition."""
        stmt = (
            select(func.count())
            .select_from(GearItem)
            .where(GearItem.expedition_id == expedition_id)
        )
        return (await self._session.execute(stmt)).scalar_one()

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    async def update(
        self,
        item_id: UUID,
        **fields,
    ) -> Optional[GearItem]:
        """Partially update a gear item. Only non-None fields are written."""
        updates = {k: v for k, v in fields.items() if v is not None}
        if not updates:
            return await self.get_by_id(item_id)

        updates["updated_at"] = datetime.now(timezone.utc)
        stmt = (
            update(GearItem)
            .where(GearItem.id == item_id)
            .values(**updates)
            .returning(GearItem)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def toggle_packed(
        self, item_id: UUID, is_packed: bool
    ) -> Optional[GearItem]:
        """Toggle the packed/unpacked state of a single item."""
        stmt = (
            update(GearItem)
            .where(GearItem.id == item_id)
            .values(
                is_packed=is_packed,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(GearItem)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    async def delete(self, item_id: UUID) -> bool:
        """Hard-delete a gear item. Returns True if deleted."""
        stmt = delete(GearItem).where(GearItem.id == item_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def delete_all_for_expedition(self, expedition_id: UUID) -> int:
        """Delete all gear items for an expedition. Returns count deleted."""
        stmt = delete(GearItem).where(GearItem.expedition_id == expedition_id)
        result = await self._session.execute(stmt)
        return result.rowcount
