"""
GuideReviewService — business logic for guide reviews.

Responsibilities:
  - Submit a review for a guide (one review per reviewer per guide).
  - List all reviews for a guide (paginated).
  - Compute the aggregate rating summary for a guide's public profile.
  - Update the denormalised rating + review_count on guide_profiles
    after every new review (keeps the summary fast for directory listing).

Rules:
  - A traveler may submit only one review per guide
    (unique constraint: guide_id + reviewer_id).
  - A guide cannot review themselves (enforced at schema + service + DB).
  - reviewer_id is always resolved from the JWT — never from the request body.
  - The guide must be VERIFIED to be reviewable (prevents reviews on pending/
    suspended profiles from affecting the directory listing).
"""

from __future__ import annotations

import math
from decimal import Decimal
from uuid import UUID

from shared import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from shared.logging import setup_logging

from app.models.guide_profile import VerificationStatus
from app.repositories.guide_profile_repository import GuideProfileRepository
from app.repositories.guide_review_repository import GuideReviewRepository
from app.schemas.common import PaginationMeta
from app.schemas.guide_review import (
    GuideRatingSummary,
    GuideReviewCreate,
    GuideReviewListResponse,
    GuideReviewResponse,
)

logger = setup_logging(service_name="guide-service", log_level="INFO")


class GuideReviewService:
    """Coordinates business logic for guide review submissions and retrieval."""

    def __init__(
        self,
        profile_repo: GuideProfileRepository,
        review_repo: GuideReviewRepository,
    ) -> None:
        self._profile_repo = profile_repo
        self._review_repo = review_repo

    # ------------------------------------------------------------------
    # SUBMIT
    # ------------------------------------------------------------------

    async def submit_review(
        self,
        guide_id: UUID,
        payload: GuideReviewCreate,
        reviewer_id: UUID,
    ) -> GuideReviewResponse:
        """Submit a review for a guide.

        Raises 404 if the guide profile does not exist.
        Raises 403 if the reviewer is the same as the guide owner (self-review).
        Raises 422 if the guide is not VERIFIED.
        Raises 409 if the reviewer has already reviewed this guide.
        """
        profile = await self._profile_repo.get_by_id(guide_id)
        if not profile:
            raise NotFoundException(
                f"Guide profile {guide_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )

        # Self-review prevention (defence in depth; DB CHECK also enforces this)
        if profile.user_id == reviewer_id:
            raise ForbiddenException(
                "A guide cannot review themselves.",
                error_code="SELF_REVIEW_NOT_ALLOWED",
            )

        # Only verified guides may be reviewed
        if profile.verification_status != VerificationStatus.VERIFIED:
            raise ValidationException(
                "Reviews can only be submitted for VERIFIED guides.",
                error_code="GUIDE_NOT_VERIFIED",
            )

        # Duplicate check
        existing = await self._review_repo.get_by_guide_and_reviewer(
            guide_id, reviewer_id
        )
        if existing:
            raise ConflictException(
                "You have already submitted a review for this guide.",
                error_code="REVIEW_ALREADY_EXISTS",
            )

        review = await self._review_repo.create(
            guide_id=guide_id,
            reviewer_id=reviewer_id,
            expedition_id=payload.expedition_id,
            rating_overall=payload.rating_overall,
            rating_knowledge=payload.rating_knowledge,
            rating_friendliness=payload.rating_friendliness,
            rating_communication=payload.rating_communication,
            rating_safety=payload.rating_safety,
            rating_professionalism=payload.rating_professionalism,
            would_recommend=payload.would_recommend,
            comment=payload.comment,
        )

        # Update denormalised rating on guide_profiles
        await self._refresh_guide_rating(guide_id)

        return GuideReviewResponse.model_validate(review)

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    async def list_reviews(
        self,
        guide_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> GuideReviewListResponse:
        """Return a paginated list of reviews for a guide."""
        profile = await self._profile_repo.get_by_id(guide_id)
        if not profile:
            raise NotFoundException(
                f"Guide profile {guide_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )

        reviews, total = await self._review_repo.list_by_guide(
            guide_id, page=page, page_size=page_size
        )
        total_pages = max(1, math.ceil(total / page_size))
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )
        return GuideReviewListResponse(
            guide_id=guide_id,
            items=[GuideReviewResponse.model_validate(r) for r in reviews],
            pagination=pagination,
        )

    # ------------------------------------------------------------------
    # RATING SUMMARY
    # ------------------------------------------------------------------

    async def get_rating_summary(
        self,
        guide_id: UUID,
    ) -> GuideRatingSummary:
        """Compute and return the aggregated rating summary for a guide.

        Reads aggregates directly from the database via a SQL AVG query;
        does not load individual review rows into Python memory.
        """
        profile = await self._profile_repo.get_by_id(guide_id)
        if not profile:
            raise NotFoundException(
                f"Guide profile {guide_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )

        aggregates = await self._review_repo.get_rating_aggregates(guide_id)

        if not aggregates:
            return GuideRatingSummary(
                guide_id=guide_id,
                review_count=0,
                average_overall=None,
                average_knowledge=None,
                average_friendliness=None,
                average_communication=None,
                average_safety=None,
                average_professionalism=None,
                would_recommend_percentage=None,
            )

        return GuideRatingSummary(
            guide_id=guide_id,
            review_count=aggregates["review_count"],
            average_overall=aggregates["avg_overall"],
            average_knowledge=Decimal(str(aggregates["avg_knowledge"])).quantize(Decimal("0.01")),
            average_friendliness=Decimal(str(aggregates["avg_friendliness"])).quantize(Decimal("0.01")),
            average_communication=Decimal(str(aggregates["avg_communication"])).quantize(Decimal("0.01")),
            average_safety=Decimal(str(aggregates["avg_safety"])).quantize(Decimal("0.01")),
            average_professionalism=Decimal(str(aggregates["avg_professionalism"])).quantize(Decimal("0.01")),
            would_recommend_percentage=aggregates["would_recommend_percentage"],
        )

    # ------------------------------------------------------------------
    # PRIVATE HELPER — update denormalised rating on guide_profiles
    # ------------------------------------------------------------------

    async def _refresh_guide_rating(self, guide_id: UUID) -> None:
        """Recompute and persist the denormalised rating + review_count.

        Called immediately after every new review insert so the directory
        listing always reflects current aggregate data without a JOIN.
        """
        aggregates = await self._review_repo.get_rating_aggregates(guide_id)
        if not aggregates:
            return

        await self._profile_repo.update_rating(
            guide_id,
            new_rating=aggregates["avg_overall"],
            new_review_count=aggregates["review_count"],
        )
        logger.info(
            "Updated denormalised rating for guide %s: %.2f (%d reviews).",
            guide_id,
            aggregates["avg_overall"],
            aggregates["review_count"],
        )
