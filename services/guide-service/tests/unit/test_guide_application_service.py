"""
Unit tests for GuideApplicationService.

Covers: create (409 conflicts), get, update (403/422), submit (403/422),
admin transitions (state machine + auto-profile creation on APPROVED).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call
from uuid import UUID

import pytest

from shared import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.models.guide_application import ApplicationStatus
from app.schemas.guide_application import GuideApplicationCreate, GuideApplicationUpdate
from app.services.guide_application_service import GuideApplicationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_application(
    user_id: UUID | None = None,
    status: ApplicationStatus = ApplicationStatus.DRAFT,
) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.user_id = user_id or uuid.uuid4()
    a.biography = "I love guiding travelers through the mountains."
    a.areas_covered = "Himachal Pradesh, India"
    a.languages = "English, Hindi"
    a.experience_years = 8
    a.certifications = None
    a.identity_document_url = None
    a.status = status
    a.submitted_at = None
    a.reviewed_at = None
    a.reviewed_by = None
    a.review_notes = None
    a.created_at = datetime.now(timezone.utc)
    a.updated_at = datetime.now(timezone.utc)
    return a


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def application_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def profile_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(application_repo, profile_repo) -> GuideApplicationService:
    return GuideApplicationService(application_repo, profile_repo)


@pytest.fixture
def user_id() -> UUID:
    return uuid.uuid4()


@pytest.fixture
def admin_id() -> UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# create_application
# ---------------------------------------------------------------------------

class TestCreateApplication:

    async def test_raises_409_when_application_already_exists(
        self, service, application_repo, profile_repo, user_id
    ):
        application_repo.get_by_user_id.return_value = _make_application(user_id=user_id)

        payload = GuideApplicationCreate(biography="A" * 100)
        with pytest.raises(ConflictException) as exc_info:
            await service.create_application(payload, user_id)

        assert exc_info.value.error_code == "APPLICATION_ALREADY_EXISTS"

    async def test_raises_409_when_profile_already_exists(
        self, service, application_repo, profile_repo, user_id
    ):
        application_repo.get_by_user_id.return_value = None
        profile_repo.exists_for_user.return_value = True

        payload = GuideApplicationCreate(biography="A" * 100)
        with pytest.raises(ConflictException) as exc_info:
            await service.create_application(payload, user_id)

        assert exc_info.value.error_code == "GUIDE_PROFILE_ALREADY_EXISTS"

    async def test_creates_draft_application(
        self, service, application_repo, profile_repo, user_id
    ):
        application_repo.get_by_user_id.return_value = None
        profile_repo.exists_for_user.return_value = False
        new_app = _make_application(user_id=user_id)
        application_repo.create.return_value = new_app

        payload = GuideApplicationCreate(biography="A" * 100)
        result = await service.create_application(payload, user_id)

        assert result.status == ApplicationStatus.DRAFT
        application_repo.create.assert_awaited_once()


# ---------------------------------------------------------------------------
# get_my_application
# ---------------------------------------------------------------------------

class TestGetMyApplication:

    async def test_raises_404_when_none_exists(
        self, service, application_repo, user_id
    ):
        application_repo.get_by_user_id.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await service.get_my_application(user_id)

        assert exc_info.value.error_code == "APPLICATION_NOT_FOUND"

    async def test_returns_own_application(
        self, service, application_repo, user_id
    ):
        app = _make_application(user_id=user_id)
        application_repo.get_by_user_id.return_value = app

        result = await service.get_my_application(user_id)

        assert result.user_id == user_id


# ---------------------------------------------------------------------------
# update_application
# ---------------------------------------------------------------------------

class TestUpdateApplication:

    async def test_raises_404_when_not_found(
        self, service, application_repo, user_id
    ):
        application_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException):
            await service.update_application(uuid.uuid4(), GuideApplicationUpdate(), user_id)

    async def test_raises_403_when_not_owner(
        self, service, application_repo, user_id
    ):
        app = _make_application(user_id=uuid.uuid4())  # different owner
        application_repo.get_by_id.return_value = app

        with pytest.raises(ForbiddenException) as exc_info:
            await service.update_application(app.id, GuideApplicationUpdate(), user_id)

        assert exc_info.value.error_code == "NOT_APPLICATION_OWNER"

    @pytest.mark.parametrize("non_draft_status", [
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.APPROVED,
        ApplicationStatus.REJECTED,
    ])
    async def test_raises_422_when_not_draft(
        self, service, application_repo, user_id, non_draft_status
    ):
        app = _make_application(user_id=user_id, status=non_draft_status)
        application_repo.get_by_id.return_value = app

        with pytest.raises(ValidationException) as exc_info:
            await service.update_application(app.id, GuideApplicationUpdate(), user_id)

        assert exc_info.value.error_code == "APPLICATION_NOT_EDITABLE"

    async def test_updates_draft_successfully(
        self, service, application_repo, user_id
    ):
        app = _make_application(user_id=user_id, status=ApplicationStatus.DRAFT)
        updated = _make_application(user_id=user_id, status=ApplicationStatus.DRAFT)
        updated.biography = "Updated bio " + "x" * 95
        application_repo.get_by_id.return_value = app
        application_repo.update.return_value = updated

        result = await service.update_application(
            app.id, GuideApplicationUpdate(biography="Updated bio " + "x" * 95), user_id
        )

        assert result.status == ApplicationStatus.DRAFT


# ---------------------------------------------------------------------------
# submit_application
# ---------------------------------------------------------------------------

class TestSubmitApplication:

    async def test_raises_403_when_not_owner(
        self, service, application_repo, user_id
    ):
        app = _make_application(user_id=uuid.uuid4())
        application_repo.get_by_id.return_value = app

        with pytest.raises(ForbiddenException) as exc_info:
            await service.submit_application(app.id, user_id)

        assert exc_info.value.error_code == "NOT_APPLICATION_OWNER"

    async def test_raises_422_when_already_submitted(
        self, service, application_repo, user_id
    ):
        app = _make_application(user_id=user_id, status=ApplicationStatus.SUBMITTED)
        application_repo.get_by_id.return_value = app

        with pytest.raises(ValidationException) as exc_info:
            await service.submit_application(app.id, user_id)

        assert exc_info.value.error_code == "INVALID_STATUS_TRANSITION"

    async def test_submits_draft_successfully(
        self, service, application_repo, user_id
    ):
        app = _make_application(user_id=user_id, status=ApplicationStatus.DRAFT)
        submitted = _make_application(user_id=user_id, status=ApplicationStatus.SUBMITTED)
        application_repo.get_by_id.return_value = app
        application_repo.update_status.return_value = submitted

        result = await service.submit_application(app.id, user_id)

        assert result.status == ApplicationStatus.SUBMITTED
        application_repo.update_status.assert_awaited_once_with(
            app.id, ApplicationStatus.SUBMITTED
        )


# ---------------------------------------------------------------------------
# admin_transition_status
# ---------------------------------------------------------------------------

class TestAdminTransitionStatus:

    async def test_raises_404_when_not_found(
        self, service, application_repo, admin_id
    ):
        application_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException):
            await service.admin_transition_status(
                uuid.uuid4(), ApplicationStatus.UNDER_REVIEW, admin_id
            )

    @pytest.mark.parametrize("current,target", [
        (ApplicationStatus.DRAFT, ApplicationStatus.UNDER_REVIEW),     # skip SUBMITTED
        (ApplicationStatus.APPROVED, ApplicationStatus.UNDER_REVIEW),  # from terminal
        (ApplicationStatus.REJECTED, ApplicationStatus.APPROVED),      # from terminal
    ])
    async def test_raises_422_on_invalid_transition(
        self, service, application_repo, admin_id, current, target
    ):
        app = _make_application(status=current)
        application_repo.get_by_id.return_value = app

        with pytest.raises(ValidationException) as exc_info:
            await service.admin_transition_status(app.id, target, admin_id)

        assert exc_info.value.error_code == "INVALID_STATUS_TRANSITION"

    async def test_creates_guide_profile_on_approved(
        self, service, application_repo, profile_repo, admin_id
    ):
        from unittest.mock import patch, MagicMock
        app = _make_application(status=ApplicationStatus.UNDER_REVIEW)
        approved_app = _make_application(
            user_id=app.user_id, status=ApplicationStatus.APPROVED
        )
        application_repo.get_by_id.return_value = app
        application_repo.update_status.return_value = approved_app
        profile_repo.exists_for_user.return_value = False  # no profile yet

        with patch("app.services.guide_application_service.logger", MagicMock()):
            await service.admin_transition_status(
                app.id, ApplicationStatus.APPROVED, admin_id
            )

        profile_repo.create.assert_awaited_once()
        create_call_kwargs = profile_repo.create.call_args.kwargs
        assert create_call_kwargs["user_id"] == app.user_id

    async def test_does_not_duplicate_profile_if_already_exists(
        self, service, application_repo, profile_repo, admin_id
    ):
        app = _make_application(status=ApplicationStatus.UNDER_REVIEW)
        approved_app = _make_application(
            user_id=app.user_id, status=ApplicationStatus.APPROVED
        )
        application_repo.get_by_id.return_value = app
        application_repo.update_status.return_value = approved_app
        profile_repo.exists_for_user.return_value = True  # profile already exists

        await service.admin_transition_status(
            app.id, ApplicationStatus.APPROVED, admin_id
        )

        profile_repo.create.assert_not_awaited()

    @pytest.mark.parametrize("current,target", [
        (ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW),
        (ApplicationStatus.SUBMITTED, ApplicationStatus.REJECTED),
        (ApplicationStatus.UNDER_REVIEW, ApplicationStatus.APPROVED),
        (ApplicationStatus.UNDER_REVIEW, ApplicationStatus.REJECTED),
    ])
    async def test_valid_admin_transitions_succeed(
        self, service, application_repo, profile_repo, admin_id, current, target
    ):
        app = _make_application(status=current)
        transitioned = _make_application(status=target)
        application_repo.get_by_id.return_value = app
        application_repo.update_status.return_value = transitioned
        profile_repo.exists_for_user.return_value = True  # avoid profile creation branch

        result = await service.admin_transition_status(app.id, target, admin_id)

        assert result.status == target
