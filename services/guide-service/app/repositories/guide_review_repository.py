"""
GuideReviewRepository — persistence layer for GuideReview.

Includes SQL aggregate queries for rating summary computation
to avoid loading all review rows into Python memory.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import Boolean, Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guide_review import GuideReview


class GuideReviewRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # DUPLICATE CHECK
    # ------------------------------------------------------------------

    async def get_by_guide_and_reviewer(
        self,
        guide_id: UUID,
        reviewer_id: UUID,
    ) -> Optional[GuideReview]:
        """Check if a review already exists for this guide/reviewer pair.

        Used before insert to surface a clean 409 rather than a DB
        IntegrityError on uq_guide_review_guide_reviewer.
        """
        stmt = (
            select(GuideReview)
            .where(GuideReview.guide_id == guide_id)
            .where(GuideReview.reviewer_id == reviewer_id)
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
        reviewer_id: UUID,
        expedition_id: Optional[UUID] = None,
        rating_overall: int,
        rating_knowledge: int,
        rating_friendliness: int,
        rating_communication: int,
        rating_safety: int,
        rating_professionalism: int,
        would_recommend: bool,
        comment: Optional[str] = None,
    ) -> GuideReview:
        """Insert a new guide review."""
        review = GuideReview(
            id=uuid.uuid4(),
            guide_id=guide_id,
            reviewer_id=reviewer_id,
            expedition_id=expedition_id,
            rating_overall=rating_overall,
            rating_knowledge=rating_knowledge,
            rating_friendliness=rating_friendliness,
            rating_communication=rating_communication,
            rating_safety=rating_safety,
            rating_professionalism=rating_professionalism,
            would_recommend=would_recommend,
            comment=comment,
        )
        self._session.add(review)
        await self._session.flush()
        await self._session.refresh(review)
        return review

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_by_id(self, review_id: UUID) -> Optional[GuideReview]:
        """Fetch a single review by primary key."""
        stmt = select(GuideReview).where(GuideReview.id == review_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_guide(
        self,
        guide_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[GuideReview], int]:
        """Return a paginated list of reviews for a guide.

        Returns (items, total_count).
        """
        base_stmt = (
            select(GuideReview)
            .where(GuideReview.guide_id == guide_id)
        )
        total: int = (
            await self._session.execute(
                select(func.count()).select_from(base_stmt.subquery())
            )
        ).scalar_one()

        offset = (page - 1) * page_size
        page_stmt = (
            base_stmt
            .order_by(GuideReview.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._session.execute(page_stmt)
        return result.scalars().all(), total

    # ------------------------------------------------------------------
    # AGGREGATE — rating summary (computed in SQL, not Python)
    # ------------------------------------------------------------------

    async def get_rating_aggregates(self, guide_id: UUID) -> Optional[dict]:
        """Compute average ratings for a guide across all reviews.

        Returns a dict of averages, or None if no reviews exist.
        Used by the service layer to update the denormalised rating column
        on guide_profiles after each new review.
        """
        stmt = (
            select(
                func.count().label("review_count"),
                func.avg(GuideReview.rating_overall).label("avg_overall"),
                func.avg(GuideReview.rating_knowledge).label("avg_knowledge"),
                func.avg(GuideReview.rating_friendliness).label("avg_friendliness"),
                func.avg(GuideReview.rating_communication).label("avg_communication"),
                func.avg(GuideReview.rating_safety).label("avg_safety"),
                func.avg(GuideReview.rating_professionalism).label("avg_professionalism"),
                func.sum(
                    cast(GuideReview.would_recommend, Integer)
                ).label("would_recommend_count"),
            )
            .where(GuideReview.guide_id == guide_id)
        )
        row = (await self._session.execute(stmt)).one()

        if not row.review_count:
            return None

        return {
            "review_count": row.review_count,
            "avg_overall": Decimal(str(row.avg_overall or 0)).quantize(Decimal("0.01")),
            "avg_knowledge": float(row.avg_knowledge or 0),
            "avg_friendliness": float(row.avg_friendliness or 0),
            "avg_communication": float(row.avg_communication or 0),
            "avg_safety": float(row.avg_safety or 0),
            "avg_professionalism": float(row.avg_professionalism or 0),
            "would_recommend_count": int(row.would_recommend_count or 0),
            "would_recommend_percentage": (
                round(int(row.would_recommend_count or 0) / row.review_count * 100, 1)
            ),
        }
