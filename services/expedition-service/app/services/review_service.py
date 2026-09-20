"""
ReviewService — business logic for post-expedition peer reviews.

Rules enforced:
  - Reviews can only be submitted after expedition is COMPLETED
  - Reviewer must have been an active participant
  - Reviewee must have been a participant (active, left, or removed)
  - A user cannot review themselves
  - Only one review per reviewer-reviewee pair per expedition
"""

from __future__ import annotations

import math
from uuid import UUID

from shared import ConflictException, ForbiddenException, NotFoundException, ValidationException

from app.models.expedition import ExpeditionStatus
from app.models.participant import ParticipantStatus
from app.repositories.expedition_repository import ExpeditionRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.review_repository import ReviewRepository
from app.schemas.common import PaginationMeta
from app.schemas.review import (
    ReviewCreate,
    ReviewListResponse,
    ReviewResponse,
    ReviewSummary,
)


class ReviewService:

    def __init__(
        self,
        expedition_repo: ExpeditionRepository,
        review_repo: ReviewRepository,
        participant_repo: ParticipantRepository,
    ) -> None:
        self._expedition_repo = expedition_repo
        self._review_repo = review_repo
        self._participant_repo = participant_repo

    async def submit_review(
        self,
        expedition_id: UUID,
        payload: ReviewCreate,
        current_user_id: UUID,
    ) -> ReviewResponse:
        """Submit a post-expedition review."""
        expedition = await self._expedition_repo.get_by_id(expedition_id)
        if not expedition:
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )

        if expedition.status != ExpeditionStatus.COMPLETED:
            raise ValidationException(
                "Reviews can only be submitted after the expedition is COMPLETED.",
                error_code="EXPEDITION_NOT_COMPLETED",
            )

        # Self-review guard (also enforced in DB and schema)
        if current_user_id == payload.reviewee_id:
            raise ValidationException(
                "You cannot review yourself.",
                error_code="SELF_REVIEW_FORBIDDEN",
            )

        # Reviewer must have been an active participant at some point
        reviewer_participation = await self._participant_repo.get_by_expedition_and_user(
            expedition_id, current_user_id
        )
        if not reviewer_participation:
            raise ForbiddenException(
                "Only expedition participants can submit reviews.",
                error_code="NOT_PARTICIPANT",
            )

        # Reviewee must also have participated
        reviewee_participation = await self._participant_repo.get_by_expedition_and_user(
            expedition_id, payload.reviewee_id
        )
        if not reviewee_participation:
            raise NotFoundException(
                "The user you are reviewing was not a participant in this expedition.",
                error_code="REVIEWEE_NOT_PARTICIPANT",
            )

        # Duplicate review check
        existing = await self._review_repo.get_by_expedition_reviewer_reviewee(
            expedition_id, current_user_id, payload.reviewee_id
        )
        if existing:
            raise ConflictException(
                "You have already reviewed this participant for this expedition.",
                error_code="DUPLICATE_REVIEW",
            )

        review = await self._review_repo.create(
            expedition_id=expedition_id,
            reviewer_id=current_user_id,
            reviewee_id=payload.reviewee_id,
            rating_overall=payload.rating_overall,
            rating_communication=payload.rating_communication,
            rating_safety=payload.rating_safety,
            rating_punctuality=payload.rating_punctuality,
            rating_organisation=payload.rating_organisation,
            rating_friendliness=payload.rating_friendliness,
            would_travel_again=payload.would_travel_again,
            comment=payload.comment,
        )
        return ReviewResponse.model_validate(review)

    async def list_reviews(
        self,
        expedition_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> ReviewListResponse:
        """Return paginated reviews for an expedition."""
        if not await self._expedition_repo.exists(expedition_id):
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )
        reviews, total = await self._review_repo.list_by_expedition(
            expedition_id, page=page, page_size=page_size
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
        return ReviewListResponse(
            expedition_id=expedition_id,
            reviews=[ReviewResponse.model_validate(r) for r in reviews],
            pagination=pagination,
        )

    async def get_review_summary(
        self, expedition_id: UUID, reviewee_id: UUID
    ) -> ReviewSummary:
        """Return aggregated rating summary for a reviewee in this expedition."""
        if not await self._expedition_repo.exists(expedition_id):
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )
        aggregates = await self._review_repo.get_average_ratings(
            expedition_id, reviewee_id
        )
        yes_count, total = await self._review_repo.count_would_travel_again(
            expedition_id, reviewee_id
        )

        avg_overall = aggregates["avg_overall"] if aggregates else None
        would_pct = (yes_count / total * 100.0) if total > 0 else None
        count = aggregates["review_count"] if aggregates else 0

        return ReviewSummary(
            reviewee_id=reviewee_id,
            expedition_id=expedition_id,
            review_count=count,
            average_overall=round(avg_overall, 2) if avg_overall else None,
            would_travel_again_percentage=round(would_pct, 1) if would_pct else None,
        )
