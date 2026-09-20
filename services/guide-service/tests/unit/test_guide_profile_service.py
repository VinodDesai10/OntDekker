"""
Unit tests for GuideProfileService.

Covers: get, list, update (ownership + 404), verification transitions
(valid/invalid state machine), soft delete (ownership).
No live database — repositories are AsyncMock.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from shared import ForbiddenException, NotFoundException, ValidationException
from app.models.guide_profile import VerificationStatus
from app.schemas.common import GuideFilter
from app.schemas.guide_profile import GuideProfileUpdate
from app.services.guide_profile_service import GuideProfileService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_profile(
    user_id: UUID | None = None,
    verification_status: VerificationStatus = VerificationStatus.PENDING,
) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.user_id = user_id or uuid.uuid4()
    p.display_name = None
    p.bio = "A great guide"
    p.profile_image_url = None
    p.cover_image_url = None
    p.years_experience = 5
    p.price_per_day = None
    p.rating = Decimal("4.50")
    p.review_count = 10
    p.verification_status = verification_status
    p.is_deleted = False
    p.deleted_at = None
    p.deleted_by = None
    p.created_at = datetime.now(timezone.utc)
    p.updated_at = datetime.now(timezone.utc)
    p.created_by = uuid.uuid4()
    p.updated_by = None
    p.locations = []
    p.languages = []
    p.availability = None
    p.specializations = []
    return p


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(profile_repo) -> GuideProfileService:
    return GuideProfileService(profile_repo)


@pytest.fixture
def owner_id() -> UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# get_profile
# ---------------------------------------------------------------------------

class TestGetProfile:

    async def test_returns_profile_when_found(self, service, profile_repo):
        profile = _make_profile()
        profile_repo.get_by_id.return_value = profile

        result = await service.get_profile(profile.id)

        assert result.id == profile.id

    async def test_raises_404_when_not_found(self, service, profile_repo):
        profile_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await service.get_profile(uuid.uuid4())

        assert exc_info.value.error_code == "GUIDE_PROFILE_NOT_FOUND"


# ---------------------------------------------------------------------------
# list_guides
# ---------------------------------------------------------------------------

class TestListGuides:

    async def test_returns_paginated_response(self, service, profile_repo):
        profiles = [_make_profile() for _ in range(5)]
        profile_repo.list_guides.return_value = (profiles, 5)

        result = await service.list_guides(GuideFilter(page=1, page_size=20))

        assert result.pagination.total_items == 5
        assert len(result.items) == 5

    async def test_empty_list(self, service, profile_repo):
        profile_repo.list_guides.return_value = ([], 0)

        result = await service.list_guides(GuideFilter(page=1, page_size=20))

        assert result.pagination.total_items == 0
        assert result.pagination.total_pages == 1


# ---------------------------------------------------------------------------
# update_profile
# ---------------------------------------------------------------------------

class TestUpdateProfile:

    async def test_raises_404_when_not_found(self, service, profile_repo):
        profile_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException):
            await service.update_profile(uuid.uuid4(), GuideProfileUpdate(bio="Hi"), uuid.uuid4())

    async def test_raises_403_when_not_owner(self, service, profile_repo, owner_id):
        profile = _make_profile(user_id=owner_id)
        profile_repo.get_by_id.return_value = profile

        with pytest.raises(ForbiddenException) as exc_info:
            await service.update_profile(profile.id, GuideProfileUpdate(bio="Hi"), uuid.uuid4())

        assert exc_info.value.error_code == "NOT_PROFILE_OWNER"

    async def test_updates_when_owner(self, service, profile_repo, owner_id):
        profile = _make_profile(user_id=owner_id)
        updated = _make_profile(user_id=owner_id)
        updated.bio = "Updated bio"
        profile_repo.get_by_id.return_value = profile
        profile_repo.update.return_value = updated

        result = await service.update_profile(
            profile.id, GuideProfileUpdate(bio="Updated bio"), owner_id
        )

        assert result.bio == "Updated bio"
        profile_repo.update.assert_awaited_once()


# ---------------------------------------------------------------------------
# transition_verification_status
# ---------------------------------------------------------------------------

class TestTransitionVerificationStatus:

    async def test_raises_404_when_not_found(self, service, profile_repo):
        profile_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException):
            await service.transition_verification_status(
                uuid.uuid4(), VerificationStatus.VERIFIED, uuid.uuid4()
            )

    @pytest.mark.parametrize("current,target", [
        (VerificationStatus.VERIFIED, VerificationStatus.PENDING),    # backwards
        (VerificationStatus.REVOKED, VerificationStatus.VERIFIED),    # from terminal
        (VerificationStatus.PENDING, VerificationStatus.SUSPENDED),   # invalid jump
    ])
    async def test_raises_422_on_invalid_transition(
        self, service, profile_repo, current, target
    ):
        profile = _make_profile(verification_status=current)
        profile_repo.get_by_id.return_value = profile

        with pytest.raises(ValidationException) as exc_info:
            await service.transition_verification_status(profile.id, target, uuid.uuid4())

        assert exc_info.value.error_code == "INVALID_VERIFICATION_TRANSITION"

    @pytest.mark.parametrize("current,target", [
        (VerificationStatus.PENDING, VerificationStatus.VERIFIED),
        (VerificationStatus.PENDING, VerificationStatus.REVOKED),
        (VerificationStatus.VERIFIED, VerificationStatus.SUSPENDED),
        (VerificationStatus.VERIFIED, VerificationStatus.REVOKED),
        (VerificationStatus.SUSPENDED, VerificationStatus.VERIFIED),
        (VerificationStatus.SUSPENDED, VerificationStatus.REVOKED),
    ])
    async def test_valid_transitions_succeed(
        self, service, profile_repo, current, target
    ):
        profile = _make_profile(verification_status=current)
        transitioned = _make_profile(verification_status=target)
        profile_repo.get_by_id.return_value = profile
        profile_repo.update_verification_status.return_value = transitioned

        result = await service.transition_verification_status(
            profile.id, target, uuid.uuid4()
        )

        assert result.verification_status == target


# ---------------------------------------------------------------------------
# delete_profile
# ---------------------------------------------------------------------------

class TestDeleteProfile:

    async def test_raises_404_when_not_found(self, service, profile_repo):
        profile_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException):
            await service.delete_profile(uuid.uuid4(), uuid.uuid4())

    async def test_raises_403_when_not_owner(self, service, profile_repo, owner_id):
        profile = _make_profile(user_id=owner_id)
        profile_repo.get_by_id.return_value = profile

        with pytest.raises(ForbiddenException) as exc_info:
            await service.delete_profile(profile.id, uuid.uuid4())

        assert exc_info.value.error_code == "NOT_PROFILE_OWNER"

    async def test_soft_deletes_when_owner(self, service, profile_repo, owner_id):
        profile = _make_profile(user_id=owner_id)
        profile_repo.get_by_id.return_value = profile
        profile_repo.soft_delete.return_value = True

        await service.delete_profile(profile.id, owner_id)

        profile_repo.soft_delete.assert_awaited_once_with(
            profile.id, deleted_by=owner_id
        )
