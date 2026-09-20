"""
Unit tests for JoinRequestService.

Covers: submit, cancel, list, approve, reject — all without a live database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from shared import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.models.expedition import ExpeditionStatus, ExpeditionVisibility
from app.models.join_request import JoinRequestStatus
from app.models.participant import ParticipantRole, ParticipantStatus
from app.services.join_request_service import JoinRequestService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_expedition(
    status: ExpeditionStatus = ExpeditionStatus.PUBLISHED,
    visibility: ExpeditionVisibility = ExpeditionVisibility.PRIVATE,
    max_participants: int = 10,
) -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    e.status = status
    e.visibility = visibility
    e.max_participants = max_participants
    e.created_at = datetime.now(timezone.utc)
    e.updated_at = datetime.now(timezone.utc)
    return e


def _make_join_request(
    expedition_id: UUID,
    user_id: UUID,
    status: JoinRequestStatus = JoinRequestStatus.PENDING,
) -> MagicMock:
    r = MagicMock()
    r.id = uuid.uuid4()
    r.expedition_id = expedition_id
    r.user_id = user_id
    r.status = status
    r.message = None
    r.rejection_reason = None
    r.reviewed_by = None
    r.created_at = datetime.now(timezone.utc)
    r.updated_at = datetime.now(timezone.utc)
    return r


def _make_participant(
    expedition_id: UUID,
    user_id: UUID,
    role: ParticipantRole = ParticipantRole.ORGANIZER,
) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.expedition_id = expedition_id
    p.user_id = user_id
    p.role = role
    p.status = ParticipantStatus.ACTIVE
    p.created_at = datetime.now(timezone.utc)
    p.updated_at = datetime.now(timezone.utc)
    return p


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def expedition_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def join_request_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def participant_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(expedition_repo, join_request_repo, participant_repo) -> JoinRequestService:
    return JoinRequestService(expedition_repo, join_request_repo, participant_repo)


@pytest.fixture
def organiser_id() -> UUID:
    return uuid.uuid4()


@pytest.fixture
def applicant_id() -> UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# submit_request
# ---------------------------------------------------------------------------

class TestSubmitRequest:

    async def test_raises_404_when_expedition_not_found(
        self, service, expedition_repo, applicant_id
    ):
        expedition_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await service.submit_request(uuid.uuid4(), applicant_id)

        assert exc_info.value.error_code == "EXPEDITION_NOT_FOUND"

    async def test_raises_422_on_public_expedition(
        self, service, expedition_repo, applicant_id
    ):
        expedition = _make_expedition(visibility=ExpeditionVisibility.PUBLIC)
        expedition_repo.get_by_id.return_value = expedition

        with pytest.raises(ValidationException) as exc_info:
            await service.submit_request(expedition.id, applicant_id)

        assert exc_info.value.error_code == "USE_DIRECT_JOIN"

    async def test_raises_422_when_expedition_not_joinable(
        self, service, expedition_repo, applicant_id
    ):
        expedition = _make_expedition(
            visibility=ExpeditionVisibility.PRIVATE,
            status=ExpeditionStatus.DRAFT,
        )
        expedition_repo.get_by_id.return_value = expedition

        with pytest.raises(ValidationException) as exc_info:
            await service.submit_request(expedition.id, applicant_id)

        assert exc_info.value.error_code == "EXPEDITION_NOT_JOINABLE"

    async def test_raises_409_when_already_participant(
        self, service, expedition_repo, participant_repo, applicant_id
    ):
        expedition = _make_expedition()
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.is_participant.return_value = True

        with pytest.raises(ConflictException) as exc_info:
            await service.submit_request(expedition.id, applicant_id)

        assert exc_info.value.error_code == "ALREADY_PARTICIPANT"

    async def test_raises_409_on_duplicate_pending_request(
        self, service, expedition_repo, participant_repo, join_request_repo, applicant_id
    ):
        expedition = _make_expedition()
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.is_participant.return_value = False
        join_request_repo.has_pending_request.return_value = True

        with pytest.raises(ConflictException) as exc_info:
            await service.submit_request(expedition.id, applicant_id)

        assert exc_info.value.error_code == "DUPLICATE_JOIN_REQUEST"

    async def test_creates_request_successfully(
        self, service, expedition_repo, participant_repo, join_request_repo, applicant_id
    ):
        expedition = _make_expedition()
        join_req = _make_join_request(expedition.id, applicant_id)
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.is_participant.return_value = False
        join_request_repo.has_pending_request.return_value = False
        join_request_repo.create.return_value = join_req

        result = await service.submit_request(expedition.id, applicant_id, "Please let me join")

        assert result.status == JoinRequestStatus.PENDING
        join_request_repo.create.assert_awaited_once()


# ---------------------------------------------------------------------------
# cancel_request
# ---------------------------------------------------------------------------

class TestCancelRequest:

    async def test_raises_404_when_no_pending_request(
        self, service, join_request_repo, applicant_id
    ):
        join_request_repo.get_by_expedition_and_user.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await service.cancel_request(uuid.uuid4(), applicant_id)

        assert exc_info.value.error_code == "JOIN_REQUEST_NOT_FOUND"

    async def test_cancels_pending_request(
        self, service, join_request_repo, applicant_id
    ):
        expedition_id = uuid.uuid4()
        join_req = _make_join_request(expedition_id, applicant_id)
        join_request_repo.get_by_expedition_and_user.return_value = join_req

        await service.cancel_request(expedition_id, applicant_id)

        join_request_repo.update_status.assert_awaited_once_with(
            join_req.id, JoinRequestStatus.CANCELLED
        )


# ---------------------------------------------------------------------------
# approve_request
# ---------------------------------------------------------------------------

class TestApproveRequest:

    async def test_raises_404_when_expedition_not_found(
        self, service, expedition_repo, organiser_id, applicant_id
    ):
        expedition_repo.exists.return_value = False

        with pytest.raises(NotFoundException):
            await service.approve_request(uuid.uuid4(), applicant_id, organiser_id)

    async def test_raises_403_when_not_organiser_or_co(
        self, service, expedition_repo, participant_repo, organiser_id, applicant_id
    ):
        expedition_id = uuid.uuid4()
        expedition_repo.exists.return_value = True
        participant_repo.get_by_expedition_and_user.return_value = None

        with pytest.raises(ForbiddenException):
            await service.approve_request(expedition_id, applicant_id, organiser_id)

    async def test_raises_404_when_no_pending_request(
        self, service, expedition_repo, participant_repo, join_request_repo,
        organiser_id, applicant_id
    ):
        expedition_id = uuid.uuid4()
        expedition_repo.exists.return_value = True
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition_id, organiser_id, role=ParticipantRole.ORGANIZER
        )
        join_request_repo.get_by_expedition_and_user.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await service.approve_request(expedition_id, applicant_id, organiser_id)

        assert exc_info.value.error_code == "JOIN_REQUEST_NOT_FOUND"

    async def test_raises_422_when_expedition_full(
        self, service, expedition_repo, participant_repo, join_request_repo,
        organiser_id, applicant_id
    ):
        expedition = _make_expedition(max_participants=5)
        expedition_repo.exists.return_value = True
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, organiser_id, role=ParticipantRole.ORGANIZER
        )
        join_request_repo.get_by_expedition_and_user.return_value = _make_join_request(
            expedition.id, applicant_id
        )
        participant_repo.count_active.return_value = 5  # at max

        with pytest.raises(ValidationException) as exc_info:
            await service.approve_request(expedition.id, applicant_id, organiser_id)

        assert exc_info.value.error_code == "EXPEDITION_FULL"

    async def test_approves_and_creates_participant(
        self, service, expedition_repo, participant_repo, join_request_repo,
        organiser_id, applicant_id
    ):
        expedition = _make_expedition(max_participants=10)
        join_req = _make_join_request(expedition.id, applicant_id)
        approved_req = _make_join_request(
            expedition.id, applicant_id, status=JoinRequestStatus.APPROVED
        )
        expedition_repo.exists.return_value = True
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, organiser_id, role=ParticipantRole.ORGANIZER
        )
        join_request_repo.get_by_expedition_and_user.return_value = join_req
        participant_repo.count_active.return_value = 3
        join_request_repo.update_status.return_value = approved_req

        result = await service.approve_request(expedition.id, applicant_id, organiser_id)

        assert result.status == JoinRequestStatus.APPROVED
        participant_repo.add.assert_awaited_once()


# ---------------------------------------------------------------------------
# reject_request
# ---------------------------------------------------------------------------

class TestRejectRequest:

    async def test_rejects_with_reason(
        self, service, expedition_repo, participant_repo, join_request_repo,
        organiser_id, applicant_id
    ):
        expedition_id = uuid.uuid4()
        expedition_repo.exists.return_value = True
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition_id, organiser_id, role=ParticipantRole.ORGANIZER
        )
        join_req = _make_join_request(expedition_id, applicant_id)
        rejected_req = _make_join_request(
            expedition_id, applicant_id, status=JoinRequestStatus.REJECTED
        )
        join_request_repo.get_by_expedition_and_user.return_value = join_req
        join_request_repo.update_status.return_value = rejected_req

        result = await service.reject_request(
            expedition_id, applicant_id, organiser_id, "Not enough experience"
        )

        assert result.status == JoinRequestStatus.REJECTED
        join_request_repo.update_status.assert_awaited_once_with(
            join_req.id,
            JoinRequestStatus.REJECTED,
            reviewed_by=organiser_id,
            rejection_reason="Not enough experience",
        )
