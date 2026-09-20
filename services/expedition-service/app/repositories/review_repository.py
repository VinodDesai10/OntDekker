"""
ReviewRepository — persistence layer for ExpeditionReview.

Includes aggregate queries for computing ReviewSummary
(average rating, would_travel_again percentage) without
loading all review rows into Python memory.
"""

from __future__ import annotations

import uuid
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import ExpeditionReview


class ReviewRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        expedition_id: UUID,
        reviewer_id: UUID,
        reviewee_id: UUID,
        rating_overall: int,
        rating_communication: int,
        rating_safety: int,
        rating_punctuality: int,
        rating_organisation: int,
        rating_friendliness: int,
        would_travel_again: bool,
        comment: Optional[str] = None,
    ) -> ExpeditionReview:
        """Insert a new review."""
        review = ExpeditionReview(
            id=uuid.uuid4(),
            expedition_id=expedition_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            rating_overall=rating_overall,
            rating_communication=rating_communication,
            rating_safety=rating_safety,
            rating_punctuality=rating_punctuality,
            rating_organisation=rating_organisation,
            rating_friendliness=rating_friendliness,
            would_travel_again=would_travel_again,
            comment=comment,
        )
        self._session.add(review)
        await self._session.flush()
        await self._session.refresh(review)
        return review

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_by_id(self, review_id: UUID) -> Optional[ExpeditionReview]:
        """Fetch a single review by PK."""
        stmt = select(ExpeditionReview).where(ExpeditionReview.id == review_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_expedition_reviewer_reviewee(
        self,
        expedition_id: UUID,
        reviewer_id: UUID,
        reviewee_id: UUID,
    ) -> Optional[ExpeditionReview]:
        """Check if a review already exists for this reviewer/reviewee pair.

        Used to enforce the UniqueConstraint before attempting an insert,
        giving a clean 409 Conflict rather than a DB IntegrityError.
        """
        stmt = (
            select(ExpeditionReview)
            .where(ExpeditionReview.expedition_id == expedition_id)
            .where(ExpeditionReview.reviewer_id == reviewer_id)
            .where(ExpeditionReview.reviewee_id == reviewee_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_expedition(
        self,
        expedition_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[ExpeditionReview], int]:
        """Return a paginated list of reviews for an expedition.

        Returns (items, total_count).
        """
        base_stmt = (
            select(ExpeditionReview)
            .where(ExpeditionReview.expedition_id == expedition_id)
        )
        total: int = (
            await self._session.execute(
                select(func.count()).select_from(base_stmt.subquery())
            )
        ).scalar_one()

        offset = (page - 1) * page_size
        page_stmt = (
            base_stmt
            .order_by(ExpeditionReview.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._session.execute(page_stmt)
        return result.scalars().all(), total

    async def list_by_reviewee(
        self,
        reviewee_id: UUID,
    ) -> Sequence[ExpeditionReview]:
        """Return all reviews received by a specific user.

        Used to build reputation data for the User Service via
        Kafka REVIEW_SUBMITTED events (Phase 2).
        """
        stmt = (
            select(ExpeditionReview)
            .where(ExpeditionReview.reviewee_id == reviewee_id)
            .order_by(ExpeditionReview.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    # ------------------------------------------------------------------
    # AGGREGATES (for ReviewSummary)
    # ------------------------------------------------------------------

    async def get_average_ratings(
        self, expedition_id: UUID, reviewee_id: UUID
    ) -> Optional[dict]:
        """Return average of each rating dimension for a reviewee.

        Computes averages in SQL to avoid fetching all rows.
        Returns None if there are no reviews yet.
        """
        stmt = (
            select(
                func.count().label("review_count"),
                func.avg(ExpeditionReview.rating_overall).label("avg_overall"),
                func.avg(ExpeditionReview.rating_communication).label("avg_comm"),
                func.avg(ExpeditionReview.rating_safety).label("avg_safety"),
                func.avg(ExpeditionReview.rating_punctuality).label("avg_punct"),
                func.avg(ExpeditionReview.rating_organisation).label("avg_org"),
                func.avg(ExpeditionReview.rating_friendliness).label("avg_friendly"),
                func.sum(
                    func.cast(ExpeditionReview.would_travel_again, func.Integer if False
                              else ExpeditionReview.would_travel_again.__class__)
                ).label("would_travel_count"),
            )
            .where(ExpeditionReview.expedition_id == expedition_id)
            .where(ExpeditionReview.reviewee_id == reviewee_id)
        )
        row = (await self._session.execute(stmt)).one()
        if not row.review_count:
            return None
        return {
            "review_count": row.review_count,
            "avg_overall": float(row.avg_overall or 0),
            "avg_communication": float(row.avg_comm or 0),
            "avg_safety": float(row.avg_safety or 0),
            "avg_punctuality": float(row.avg_punct or 0),
            "avg_organisation": float(row.avg_org or 0),
            "avg_friendliness": float(row.avg_friendly or 0),
        }

    async def count_would_travel_again(
        self, expedition_id: UUID, reviewee_id: UUID
    ) -> tuple[int, int]:
        """Return (yes_count, total_count) for would_travel_again.

        Used by the service layer to compute the percentage.
        """
        stmt = (
            select(
                func.count().label("total"),
                func.sum(
                    func.cast(ExpeditionReview.would_travel_again, func.Integer.__class__)
                ).label("yes_count"),
            )
            .where(ExpeditionReview.expedition_id == expedition_id)
            .where(ExpeditionReview.reviewee_id == reviewee_id)
        )
        row = (await self._session.execute(stmt)).one()
        return int(row.yes_count or 0), int(row.total or 0)
