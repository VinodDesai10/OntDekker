"""
GuideApplicationRepository — persistence layer for GuideApplication.

Responsibilities:
  - Create and fetch guide applications
  - Status transition writes (SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED)
  - Pre-insert duplicate check on user_id → clean 409

Rules:
  - No business logic
  - Never calls commit()
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guide_application import GuideApplication, ApplicationStatus


class GuideApplicationRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        user_id: UUID,
        biography: Optional[str] = None,
        areas_covered: Optional[str] = None,
        languages: Optional[str] = None,
        experience_years: Optional[int] = None,
        certifications: Optional[str] = None,
        identity_document_url: Optional[str] = None,
    ) -> GuideApplication:
        """Insert a new guide application in DRAFT status."""
        application = GuideApplication(
            id=uuid.uuid4(),
            user_id=user_id,
            biography=biography,
            areas_covered=areas_covered,
            languages=languages,
            experience_years=experience_years,
            certifications=certifications,
            identity_document_url=identity_document_url,
            status=ApplicationStatus.DRAFT,
        )
        self._session.add(application)
        await self._session.flush()
        await self._session.refresh(application)
        return application

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_by_id(self, application_id: UUID) -> Optional[GuideApplication]:
        """Fetch a single application by primary key."""
        stmt = select(GuideApplication).where(GuideApplication.id == application_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: UUID) -> Optional[GuideApplication]:
        """Fetch the application for a specific user.

        Used to check for duplicates before allowing a new application
        (gives a clean 409 rather than a DB IntegrityError on the
        uq_guide_application_user constraint).
        """
        stmt = (
            select(GuideApplication)
            .where(GuideApplication.user_id == user_id)
            .order_by(GuideApplication.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_status(
        self,
        status: ApplicationStatus,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[GuideApplication], int]:
        """Return a paginated list of applications filtered by status.

        Used by the admin review queue.
        Returns (items, total_count).
        """
        base_stmt = (
            select(GuideApplication)
            .where(GuideApplication.status == status)
        )
        total: int = (
            await self._session.execute(
                select(func.count()).select_from(base_stmt.subquery())
            )
        ).scalar_one()

        offset = (page - 1) * page_size
        page_stmt = (
            base_stmt
            .order_by(GuideApplication.submitted_at.asc().nulls_last())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._session.execute(page_stmt)
        return result.scalars().all(), total

    # ------------------------------------------------------------------
    # UPDATE — partial field update (for DRAFT edits)
    # ------------------------------------------------------------------

    async def update(
        self,
        application_id: UUID,
        **fields,
    ) -> Optional[GuideApplication]:
        """Update specific fields on an application row.

        Only non-None keyword arguments are written.
        """
        updates = {k: v for k, v in fields.items() if v is not None}
        if not updates:
            return await self.get_by_id(application_id)

        updates["updated_at"] = datetime.now(timezone.utc)

        stmt = (
            update(GuideApplication)
            .where(GuideApplication.id == application_id)
            .values(**updates)
            .returning(GuideApplication)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # UPDATE — status transition
    # ------------------------------------------------------------------

    async def update_status(
        self,
        application_id: UUID,
        status: ApplicationStatus,
        *,
        reviewed_by: Optional[UUID] = None,
        review_notes: Optional[str] = None,
    ) -> Optional[GuideApplication]:
        """Write a new status to an application.

        Sets submitted_at when transitioning to SUBMITTED.
        Sets reviewed_at and reviewed_by when transitioning to
        APPROVED, REJECTED, or UNDER_REVIEW.
        """
        now = datetime.now(timezone.utc)
        values: dict = {
            "status": status,
            "updated_at": now,
        }

        if status == ApplicationStatus.SUBMITTED:
            values["submitted_at"] = now
        elif status in (
            ApplicationStatus.APPROVED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.UNDER_REVIEW,
        ):
            values["reviewed_at"] = now
            if reviewed_by is not None:
                values["reviewed_by"] = reviewed_by
            if review_notes is not None:
                values["review_notes"] = review_notes

        stmt = (
            update(GuideApplication)
            .where(GuideApplication.id == application_id)
            .values(**values)
            .returning(GuideApplication)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
