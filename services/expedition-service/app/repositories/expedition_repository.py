"""
ExpeditionRepository — persistence layer for the Expedition aggregate.

Responsibilities:
  - CRUD operations on the `expeditions` table
  - Filtered, paginated listing
  - Soft-delete support
  - Status transition writes

Rules enforced here:
  - Never contains business logic (that belongs in the service layer)
  - Never calls other repositories or external services
  - All queries use async SQLAlchemy 2.0 style (select / scalars / execute)
  - Soft-deleted rows are excluded from reads unless explicitly requested
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expedition import Expedition, ExpeditionStatus, ExpeditionVisibility
from app.schemas.common import ExpeditionFilter


class ExpeditionRepository:
    """Data-access object for the Expedition model.

    Instantiated once per request via FastAPI dependency injection:
        session: AsyncSession = Depends(get_db)
        repo = ExpeditionRepository(session)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        community_id: UUID,
        organizer_id: UUID,
        title: str,
        destination: str,
        description: Optional[str] = None,
        meeting_point: Optional[str] = None,
        start_date=None,
        end_date=None,
        max_participants: int = 10,
        budget=None,
        visibility: ExpeditionVisibility = ExpeditionVisibility.PUBLIC,
        cover_image_url: Optional[str] = None,
        created_by: Optional[UUID] = None,
    ) -> Expedition:
        """Insert a new expedition row and return the persisted object.

        Status is always initialised to DRAFT — the service layer
        transitions it to PUBLISHED via a separate call.
        """
        expedition = Expedition(
            id=uuid.uuid4(),
            community_id=community_id,
            organizer_id=organizer_id,
            title=title,
            destination=destination,
            description=description,
            meeting_point=meeting_point,
            start_date=start_date,
            end_date=end_date,
            max_participants=max_participants,
            budget=budget,
            visibility=visibility,
            status=ExpeditionStatus.DRAFT,
            cover_image_url=cover_image_url,
            created_by=created_by,
            updated_by=created_by,
        )
        self._session.add(expedition)
        await self._session.flush()  # get DB-generated defaults without committing
        await self._session.refresh(expedition)
        return expedition

    # ------------------------------------------------------------------
    # READ — single
    # ------------------------------------------------------------------

    async def get_by_id(
        self,
        expedition_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[Expedition]:
        """Fetch a single expedition by primary key.

        Returns None if not found or soft-deleted (unless include_deleted=True).
        """
        stmt = select(Expedition).where(Expedition.id == expedition_id)
        if not include_deleted:
            stmt = stmt.where(Expedition.is_deleted.is_(False))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # READ — list with filtering and pagination
    # ------------------------------------------------------------------

    async def list_expeditions(
        self,
        filters: ExpeditionFilter,
    ) -> tuple[Sequence[Expedition], int]:
        """Return a page of expeditions matching the given filters.

        Returns a tuple of (items, total_count).
        total_count is the count of ALL matching rows (ignoring pagination),
        used by the service layer to build PaginationMeta.
        """
        base_stmt = (
            select(Expedition)
            .where(Expedition.is_deleted.is_(False))
        )

        # Apply optional filters
        if filters.community_id is not None:
            base_stmt = base_stmt.where(
                Expedition.community_id == filters.community_id
            )
        if filters.organizer_id is not None:
            base_stmt = base_stmt.where(
                Expedition.organizer_id == filters.organizer_id
            )
        if filters.status is not None:
            base_stmt = base_stmt.where(Expedition.status == filters.status)
        if filters.visibility is not None:
            base_stmt = base_stmt.where(
                Expedition.visibility == filters.visibility
            )

        # Count total matching rows (without pagination)
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total: int = (await self._session.execute(count_stmt)).scalar_one()

        # Apply ordering and pagination
        offset = (filters.page - 1) * filters.page_size
        page_stmt = (
            base_stmt
            .order_by(Expedition.created_at.desc())
            .offset(offset)
            .limit(filters.page_size)
        )

        result = await self._session.execute(page_stmt)
        items = result.scalars().all()
        return items, total

    # ------------------------------------------------------------------
    # UPDATE — partial field update
    # ------------------------------------------------------------------

    async def update(
        self,
        expedition_id: UUID,
        *,
        updated_by: Optional[UUID] = None,
        **fields,
    ) -> Optional[Expedition]:
        """Update specific fields on an expedition row.

        Only non-None keyword arguments in **fields are written.
        Returns the updated expedition or None if not found / soft-deleted.
        """
        # Filter out None values — only update what was provided
        updates = {k: v for k, v in fields.items() if v is not None}
        if not updates:
            return await self.get_by_id(expedition_id)

        updates["updated_by"] = updated_by
        updates["updated_at"] = datetime.now(timezone.utc)

        stmt = (
            update(Expedition)
            .where(Expedition.id == expedition_id)
            .where(Expedition.is_deleted.is_(False))
            .values(**updates)
            .returning(Expedition)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # STATUS TRANSITION
    # ------------------------------------------------------------------

    async def update_status(
        self,
        expedition_id: UUID,
        status: ExpeditionStatus,
        *,
        updated_by: Optional[UUID] = None,
    ) -> Optional[Expedition]:
        """Write a new status value to an expedition row.

        The validity of the transition is enforced in the service layer.
        """
        stmt = (
            update(Expedition)
            .where(Expedition.id == expedition_id)
            .where(Expedition.is_deleted.is_(False))
            .values(
                status=status,
                updated_by=updated_by,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(Expedition)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # SOFT DELETE
    # ------------------------------------------------------------------

    async def soft_delete(
        self,
        expedition_id: UUID,
        *,
        deleted_by: Optional[UUID] = None,
    ) -> bool:
        """Mark an expedition as deleted without removing the row.

        Returns True if the row was found and marked, False if not found
        or already deleted.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(Expedition)
            .where(Expedition.id == expedition_id)
            .where(Expedition.is_deleted.is_(False))
            .values(
                is_deleted=True,
                deleted_at=now,
                deleted_by=deleted_by,
                updated_at=now,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # EXISTENCE CHECKS
    # ------------------------------------------------------------------

    async def exists(self, expedition_id: UUID) -> bool:
        """Return True if an active (non-deleted) expedition exists."""
        stmt = (
            select(func.count())
            .select_from(Expedition)
            .where(Expedition.id == expedition_id)
            .where(Expedition.is_deleted.is_(False))
        )
        count: int = (await self._session.execute(stmt)).scalar_one()
        return count > 0
