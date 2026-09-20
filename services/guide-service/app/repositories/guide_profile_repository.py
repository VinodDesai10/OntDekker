"""
GuideProfileRepository — persistence layer for GuideProfile.

Responsibilities:
  - CRUD on guide_profiles
  - Filtered, paginated directory listing
  - Soft-delete support
  - Denormalised rating update after a review is submitted
  - Verification status transition writes

Rules:
  - No business logic — that belongs in the service layer
  - Never calls commit()
  - All queries use async SQLAlchemy 2.0 style
  - Soft-deleted rows are excluded from reads by default
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guide_profile import GuideProfile, VerificationStatus
from app.schemas.common import GuideFilter


class GuideProfileRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        user_id: UUID,
        bio: Optional[str] = None,
        profile_image_url: Optional[str] = None,
        cover_image_url: Optional[str] = None,
        years_experience: Optional[int] = None,
        created_by: Optional[UUID] = None,
    ) -> GuideProfile:
        """Insert a new guide profile row.

        Called by the service layer when a GuideApplication is approved.
        verification_status defaults to PENDING (pending identity verification).
        """
        profile = GuideProfile(
            id=uuid.uuid4(),
            user_id=user_id,
            bio=bio,
            profile_image_url=profile_image_url,
            cover_image_url=cover_image_url,
            years_experience=years_experience,
            rating=None,
            review_count=0,
            verification_status=VerificationStatus.PENDING,
            created_by=created_by,
            updated_by=created_by,
        )
        self._session.add(profile)
        await self._session.flush()
        await self._session.refresh(profile)
        return profile

    # ------------------------------------------------------------------
    # READ — single
    # ------------------------------------------------------------------

    async def get_by_id(
        self,
        profile_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[GuideProfile]:
        """Fetch a single guide profile by primary key.

        Eagerly loads locations, languages, and availability so that
        GuideProfileResponse.model_validate() can access them outside
        the greenlet session context without raising MissingGreenlet.
        """
        stmt = (
            select(GuideProfile)
            .where(GuideProfile.id == profile_id)
            .options(
                selectinload(GuideProfile.locations),
                selectinload(GuideProfile.languages),
                selectinload(GuideProfile.availability),
                selectinload(GuideProfile.specializations),
            )
        )
        if not include_deleted:
            stmt = stmt.where(GuideProfile.is_deleted.is_(False))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self,
        user_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[GuideProfile]:
        """Fetch a guide profile by the owning user's UUID.

        Used to check if a user already has a guide profile before
        creating one (gives a clean 409 rather than a DB IntegrityError).
        """
        stmt = select(GuideProfile).where(GuideProfile.user_id == user_id)
        if not include_deleted:
            stmt = stmt.where(GuideProfile.is_deleted.is_(False))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # READ — paginated directory listing
    # ------------------------------------------------------------------

    async def list_guides(
        self,
        filters: GuideFilter,
    ) -> tuple[Sequence[GuideProfile], int]:
        """Return a page of guide profiles matching the given filters.

        Joins guide_locations and guide_languages for filtering but
        returns distinct GuideProfile rows (not duplicated by joins).
        Returns (items, total_count).
        """
        from app.models.guide_location import GuideLocation
        from app.models.guide_language import GuideLanguage
        from app.models.guide_availability import GuideAvailability

        base_stmt = (
            select(GuideProfile)
            .where(GuideProfile.is_deleted.is_(False))
            .options(
                selectinload(GuideProfile.locations),
                selectinload(GuideProfile.languages),
                selectinload(GuideProfile.availability),
                selectinload(GuideProfile.specializations),
            )
        )

        if filters.verification_status is not None:
            base_stmt = base_stmt.where(
                GuideProfile.verification_status == filters.verification_status
            )

        if filters.country is not None:
            base_stmt = base_stmt.join(
                GuideLocation,
                GuideLocation.guide_id == GuideProfile.id,
            ).where(GuideLocation.country == filters.country)

        if filters.language is not None:
            base_stmt = base_stmt.join(
                GuideLanguage,
                GuideLanguage.guide_id == GuideProfile.id,
            ).where(GuideLanguage.language == filters.language)

        if filters.availability is not None:
            base_stmt = base_stmt.join(
                GuideAvailability,
                GuideAvailability.guide_id == GuideProfile.id,
            ).where(GuideAvailability.status == filters.availability)

        if filters.specialization is not None:
            from app.models.guide_specialization import GuideSpecialization
            base_stmt = base_stmt.join(
                GuideSpecialization,
                GuideSpecialization.guide_id == GuideProfile.id,
            ).where(GuideSpecialization.category == filters.specialization)

        # Distinct to avoid duplicates from multi-value joins
        base_stmt = base_stmt.distinct()

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total: int = (await self._session.execute(count_stmt)).scalar_one()

        offset = (filters.page - 1) * filters.page_size
        page_stmt = (
            base_stmt
            .order_by(GuideProfile.rating.desc().nulls_last(),
                      GuideProfile.review_count.desc())
            .offset(offset)
            .limit(filters.page_size)
        )
        result = await self._session.execute(page_stmt)
        return result.scalars().all(), total

    # ------------------------------------------------------------------
    # UPDATE — partial field update
    # ------------------------------------------------------------------

    async def update(
        self,
        profile_id: UUID,
        *,
        updated_by: Optional[UUID] = None,
        **fields,
    ) -> Optional[GuideProfile]:
        """Update specific fields on a guide profile row.

        Only non-None keyword arguments are written.
        Returns the updated profile or None if not found / soft-deleted.
        """
        updates = {k: v for k, v in fields.items() if v is not None}
        if not updates:
            return await self.get_by_id(profile_id)

        updates["updated_by"] = updated_by
        updates["updated_at"] = datetime.now(timezone.utc)

        stmt = (
            update(GuideProfile)
            .where(GuideProfile.id == profile_id)
            .where(GuideProfile.is_deleted.is_(False))
            .values(**updates)
            .returning(GuideProfile)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # UPDATE — verification status transition
    # ------------------------------------------------------------------

    async def update_verification_status(
        self,
        profile_id: UUID,
        status: VerificationStatus,
        *,
        updated_by: Optional[UUID] = None,
    ) -> Optional[GuideProfile]:
        """Write a new verification status to a guide profile.

        The validity of the transition is enforced in the service layer.
        """
        stmt = (
            update(GuideProfile)
            .where(GuideProfile.id == profile_id)
            .where(GuideProfile.is_deleted.is_(False))
            .values(
                verification_status=status,
                updated_by=updated_by,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(GuideProfile)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # UPDATE — denormalised rating (called after each review insert)
    # ------------------------------------------------------------------

    async def update_rating(
        self,
        profile_id: UUID,
        new_rating: Decimal,
        new_review_count: int,
    ) -> Optional[GuideProfile]:
        """Overwrite the denormalised rating and review_count columns.

        The new values are computed by the service layer (or review
        repository aggregate query) before calling this method.
        """
        stmt = (
            update(GuideProfile)
            .where(GuideProfile.id == profile_id)
            .where(GuideProfile.is_deleted.is_(False))
            .values(
                rating=new_rating,
                review_count=new_review_count,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(GuideProfile)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # SOFT DELETE
    # ------------------------------------------------------------------

    async def soft_delete(
        self,
        profile_id: UUID,
        *,
        deleted_by: Optional[UUID] = None,
    ) -> bool:
        """Mark a guide profile as deleted. Returns True if found and marked."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(GuideProfile)
            .where(GuideProfile.id == profile_id)
            .where(GuideProfile.is_deleted.is_(False))
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
    # EXISTENCE CHECK
    # ------------------------------------------------------------------

    async def exists_for_user(self, user_id: UUID) -> bool:
        """Return True if an active guide profile exists for this user."""
        stmt = (
            select(func.count())
            .select_from(GuideProfile)
            .where(GuideProfile.user_id == user_id)
            .where(GuideProfile.is_deleted.is_(False))
        )
        return (await self._session.execute(stmt)).scalar_one() > 0
