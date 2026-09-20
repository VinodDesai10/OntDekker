"""
GalleryRepository — persistence layer for ExpeditionGallery.

Binary images are never handled here — only MinIO object URLs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gallery import ExpeditionGallery


class GalleryRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def add_photo(
        self,
        *,
        expedition_id: UUID,
        uploaded_by: UUID,
        image_url: str,
        caption: Optional[str] = None,
        display_order: int = 0,
    ) -> ExpeditionGallery:
        """Register a newly uploaded photo URL."""
        photo = ExpeditionGallery(
            id=uuid.uuid4(),
            expedition_id=expedition_id,
            uploaded_by=uploaded_by,
            image_url=image_url,
            caption=caption,
            display_order=display_order,
        )
        self._session.add(photo)
        await self._session.flush()
        await self._session.refresh(photo)
        return photo

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_by_id(self, photo_id: UUID) -> Optional[ExpeditionGallery]:
        """Fetch a single gallery photo by PK."""
        stmt = select(ExpeditionGallery).where(ExpeditionGallery.id == photo_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_expedition(
        self, expedition_id: UUID
    ) -> Sequence[ExpeditionGallery]:
        """Return all photos for an expedition, ordered by display_order."""
        stmt = (
            select(ExpeditionGallery)
            .where(ExpeditionGallery.expedition_id == expedition_id)
            .order_by(
                ExpeditionGallery.display_order.asc(),
                ExpeditionGallery.created_at.asc(),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_by_expedition(self, expedition_id: UUID) -> int:
        """Return total photo count for an expedition."""
        stmt = (
            select(func.count())
            .select_from(ExpeditionGallery)
            .where(ExpeditionGallery.expedition_id == expedition_id)
        )
        return (await self._session.execute(stmt)).scalar_one()

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    async def update_photo(
        self,
        photo_id: UUID,
        *,
        caption: Optional[str] = None,
        display_order: Optional[int] = None,
    ) -> Optional[ExpeditionGallery]:
        """Update caption and/or display_order on a gallery photo."""
        updates: dict = {"updated_at": datetime.now(timezone.utc)}
        # Allow explicit None to clear the caption
        if caption is not None:
            updates["caption"] = caption
        if display_order is not None:
            updates["display_order"] = display_order

        stmt = (
            update(ExpeditionGallery)
            .where(ExpeditionGallery.id == photo_id)
            .values(**updates)
            .returning(ExpeditionGallery)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    async def delete_photo(self, photo_id: UUID) -> bool:
        """Hard-delete a gallery photo row. Returns True if deleted."""
        stmt = delete(ExpeditionGallery).where(ExpeditionGallery.id == photo_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0
