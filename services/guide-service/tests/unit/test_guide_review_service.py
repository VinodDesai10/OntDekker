"""
Unit tests for GuideReviewService.

Covers: submit (404/self-review/not-verified/duplicate/success + rating refresh),
list (404/pagination), rating summary (no reviews / with reviews).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from shared import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.models.guide_profile import VerificationStatus
from app.schemas.guide_review import GuideReviewCreate
from app.services.guide_review_service import GuideReviewService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_profile(
    user_id: UUID | None = None,
    verification_status: VerificationStatus = VerificationStatus.VERIFIED,
) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.user_id = user_id or uuid.uuid4()
    p.verification_status = verification_status
    p.rating = Decimal("4.50")
    p.review_count = 3
    p.locations = []
    p.languages = []
    p.availability = None
    p.specializations = []
    p.bio = None
    p.profile_image_url = None
    p.cover_image_url = None
    p.years_experience = None
    p.price_per_day = None
    p.is_deleted = False
    p.created_at = datetime.now(timezone.utc)
    p.updated_at = datetime.now(timezone.utc)
    p.created_by = uuid.uuid4()
    p.updated_by = None
    return p


def _make_review(guide_id: UUID, reviewer_id: UUID) -> MagicMock:
    r = MagicMock()
    r.id = uuid.uuid4()
    r.guide_id = guide_id
    r.reviewer_id = reviewer_id
    r.expedition_id = None
    r.rating_overall = 5
    r.rating_knowledge = 5
    r.rating_friendliness = 5
    r.rating_communication = 5
    r.rating_safety = 5
    r.rating_professionalism = 5
    r.would_recommend = True
    r.comment = "Excellent guide!"
    r.created_at = datetime.now(timezone.utc)
    r.updated_at = datetime.now(timezone.utc)
    return r


def _make_review_payload() -> GuideReviewCreate:
    return GuideReviewCreate(
        rating_overall=5,
        rating_knowledge=5,
        rating_friendliness=5,
        rating_communication=5,
        rating_safety=5,
        rating_professionalism=5,
        would_recommend=True,
        comment="Great guide!",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def review_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(profile_repo, review_repo) -> GuideReviewService:
    return GuideReviewService(profile_repo, review_repo)


@pytest.fixture
def reviewer_id() -> UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# submit_review
# ---------------------------------------------------------------------------

class TestSubmitReview:

    async def test_raises_404_when_guide_not_found(
        self, service, profile_repo, reviewer_id
    ):
        profile_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await service.submit_review(uuid.uuid4(), _make_review_payload(), reviewer_id)

        assert exc_info.value.error_code == "GUIDE_PROFILE_NOT_FOUND"

    async def test_raises_403_on_self_review(
        self, service, profile_repo, reviewer_id
    ):
        # Profile user_id == reviewer_id
        profile = _make_profile(user_id=reviewer_id)
        profile_repo.get_by_id.return_value = profile

        with pytest.raises(ForbiddenException) as exc_info:
            await service.submit_review(profile.id, _make_review_payload(), reviewer_id)

        assert exc_info.value.error_code == "SELF_REVIEW_NOT_ALLOWED"

    @pytest.mark.parametrize("non_verified_status", [
        VerificationStatus.PENDING,
        VerificationStatus.SUSPENDED,
        VerificationStatus.REVOKED,
    ])
    async def test_raises_422_when_guide_not_verified(
        self, service, profile_repo, reviewer_id, non_verified_status
    ):
        profile = _make_profile(verification_status=non_verified_status)
        profile_repo.get_by_id.return_value = profile

        with pytest.raises(ValidationException) as exc_info:
            await service.submit_review(profile.id, _make_review_payload(), reviewer_id)

        assert exc_info.value.error_code == "GUIDE_NOT_VERIFIED"

    async def test_raises_409_on_duplicate_review(
        self, service, profile_repo, review_repo, reviewer_id
    ):
        profile = _make_profile()
        profile_repo.get_by_id.return_value = profile
        review_repo.get_by_guide_and_reviewer.return_value = _make_review(
            profile.id, reviewer_id
        )

        with pytest.raises(ConflictException) as exc_info:
            await service.submit_review(profile.id, _make_review_payload(), reviewer_id)

        assert exc_info.value.error_code == "REVIEW_ALREADY_EXISTS"

    async def test_submits_review_and_refreshes_rating(
        self, service, profile_repo, review_repo, reviewer_id
    ):
        from unittest.mock import patch, MagicMock
        profile = _make_profile()
        review = _make_review(profile.id, reviewer_id)
        profile_repo.get_by_id.return_value = profile
        review_repo.get_by_guide_and_reviewer.return_value = None
        review_repo.create.return_value = review
        review_repo.get_rating_aggregates.return_value = {
            "review_count": 4,
            "avg_overall": Decimal("4.75"),
            "avg_knowledge": 4.5,
            "avg_friendliness": 5.0,
            "avg_communication": 4.75,
            "avg_safety": 5.0,
            "avg_professionalism": 4.5,
            "would_recommend_count": 4,
            "would_recommend_percentage": 100.0,
        }

        with patch("app.services.guide_review_service.logger", MagicMock()):
            result = await service.submit_review(profile.id, _make_review_payload(), reviewer_id)

        assert result.id == review.id
        # Rating refresh was called after insert
        review_repo.get_rating_aggregates.assert_awaited_once_with(profile.id)
        profile_repo.update_rating.assert_awaited_once()


# ---------------------------------------------------------------------------
# list_reviews
# ---------------------------------------------------------------------------

class TestListReviews:

    async def test_raises_404_when_guide_not_found(self, service, profile_repo):
        profile_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException):
            await service.list_reviews(uuid.uuid4())

    async def test_returns_paginated_reviews(
        self, service, profile_repo, review_repo, reviewer_id
    ):
        profile = _make_profile()
        reviews = [_make_review(profile.id, reviewer_id) for _ in range(3)]
        profile_repo.get_by_id.return_value = profile
        review_repo.list_by_guide.return_value = (reviews, 3)

        result = await service.list_reviews(profile.id, page=1, page_size=20)

        assert result.pagination.total_items == 3
        assert len(result.items) == 3
        assert result.guide_id == profile.id


# ---------------------------------------------------------------------------
# get_rating_summary
# ---------------------------------------------------------------------------

class TestGetRatingSummary:

    async def test_raises_404_when_guide_not_found(self, service, profile_repo):
        profile_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException):
            await service.get_rating_summary(uuid.uuid4())

    async def test_returns_empty_summary_when_no_reviews(
        self, service, profile_repo, review_repo
    ):
        profile = _make_profile()
        profile_repo.get_by_id.return_value = profile
        review_repo.get_rating_aggregates.return_value = None

        result = await service.get_rating_summary(profile.id)

        assert result.review_count == 0
        assert result.average_overall is None
        assert result.would_recommend_percentage is None

    async def test_returns_computed_summary(
        self, service, profile_repo, review_repo
    ):
        profile = _make_profile()
        profile_repo.get_by_id.return_value = profile
        review_repo.get_rating_aggregates.return_value = {
            "review_count": 10,
            "avg_overall": Decimal("4.60"),
            "avg_knowledge": 4.7,
            "avg_friendliness": 4.8,
            "avg_communication": 4.5,
            "avg_safety": 4.9,
            "avg_professionalism": 4.6,
            "would_recommend_count": 9,
            "would_recommend_percentage": 90.0,
        }

        result = await service.get_rating_summary(profile.id)

        assert result.review_count == 10
        assert result.average_overall == Decimal("4.60")
        assert result.would_recommend_percentage == 90.0
