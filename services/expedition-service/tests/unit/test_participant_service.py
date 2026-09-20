"""
Unit tests for ParticipantService.

Covers: list, leave, remove, update_role — all without a live database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from shared import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.models.expedition import ExpeditionStatus, ExpeditionVisibility
from app.models.participant import ParticipantRole, ParticipantStatus
from app.services.participant_service import ParticipantService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_expedition(
    status: ExpeditionStatus = ExpeditionStatus.PUBLISHED,
    visibility: ExpeditionVisibility = ExpeditionVisibility.PUBLIC,
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


def _make_participant(
    expedition_id: UUID,
    user_id: UUID,
    role: ParticipantRole = ParticipantRole.PARTICIPANT,
    status: ParticipantStatus = ParticipantStatus.ACTIVE,
) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.expedition_id = expedition_id
    p.user_id = user_id
    p.role = role
    p.status = status
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
def participant_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(expedition_repo, participant_repo) -> ParticipantService:
    return ParticipantService(expedition_repo, participant_repo)


@pytest.fixture
def organiser_id() -> UUID:
    return uuid.uuid4()


@pytest.fixture
def member_id() -> UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# list_participants
# ---------------------------------------------------------------------------

class TestListParticipants:

    async def test_raises_404_when_expedition_not_found(
        self, service, expedition_repo
    ):
        expedition_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await service.list_participants(uuid.uuid4())

        assert exc_info.value.error_code == "EXPEDITION_NOT_FOUND"

    async def test_returns_participants_list(
        self, service, expedition_repo, participant_repo, organiser_id, member_id
    ):
        expedition = _make_expedition()
        expedition_repo.get_by_id.return_value = expedition
        participants = [
            _make_participant(expedition.id, organiser_id, role=ParticipantRole.ORGANIZER),
            _make_participant(expedition.id, member_id),
        ]
        participant_repo.list_by_expedition.return_value = participants

        result = await service.list_participants(expedition.id)

        assert len(result) == 2


# ---------------------------------------------------------------------------
# leave_expedition
# ---------------------------------------------------------------------------

class TestLeaveExpedition:

    async def test_raises_404_when_not_participant(
        self, service, expedition_repo, participant_repo, member_id
    ):
        expedition = _make_expedition()
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await service.leave_expedition(expedition.id, member_id)

        assert exc_info.value.error_code == "NOT_PARTICIPANT"

    async def test_organiser_cannot_leave(
        self, service, expedition_repo, participant_repo, organiser_id
    ):
        expedition = _make_expedition()
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, organiser_id, role=ParticipantRole.ORGANIZER
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.leave_expedition(expedition.id, organiser_id)

        assert exc_info.value.error_code == "ORGANISER_CANNOT_LEAVE"

    async def test_member_can_leave(
        self, service, expedition_repo, participant_repo, member_id
    ):
        expedition = _make_expedition()
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, member_id, role=ParticipantRole.PARTICIPANT
        )

        await service.leave_expedition(expedition.id, member_id)

        participant_repo.update_status.assert_awaited_once_with(
            expedition.id, member_id, ParticipantStatus.LEFT
        )


# ---------------------------------------------------------------------------
# remove_participant
# ---------------------------------------------------------------------------

class TestRemoveParticipant:

    async def test_raises_403_when_not_organiser_or_co(
        self, service, expedition_repo, participant_repo, member_id
    ):
        expedition = _make_expedition()
        expedition_repo.get_by_id.return_value = expedition
        # caller is just a PARTICIPANT
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, member_id, role=ParticipantRole.PARTICIPANT
        )

        with pytest.raises(ForbiddenException) as exc_info:
            await service.remove_participant(expedition.id, uuid.uuid4(), member_id)

        assert exc_info.value.error_code == "NOT_ORGANISER_OR_CO"

    async def test_cannot_remove_organiser(
        self, service, expedition_repo, participant_repo, organiser_id, member_id
    ):
        expedition = _make_expedition()
        expedition_repo.get_by_id.return_value = expedition
        # caller is organiser
        organiser_participant = _make_participant(
            expedition.id, organiser_id, role=ParticipantRole.ORGANIZER
        )
        # target is also organiser
        target_organiser = _make_participant(
            expedition.id, member_id, role=ParticipantRole.ORGANIZER
        )
        participant_repo.get_by_expedition_and_user.side_effect = [
            organiser_participant,  # first call: caller check
            target_organiser,       # second call: target lookup
        ]

        with pytest.raises(ValidationException) as exc_info:
            await service.remove_participant(expedition.id, member_id, organiser_id)

        assert exc_info.value.error_code == "CANNOT_REMOVE_ORGANISER"

    async def test_removes_participant_successfully(
        self, service, expedition_repo, participant_repo, organiser_id, member_id
    ):
        expedition = _make_expedition()
        expedition_repo.get_by_id.return_value = expedition
        organiser_participant = _make_participant(
            expedition.id, organiser_id, role=ParticipantRole.ORGANIZER
        )
        target_participant = _make_participant(
            expedition.id, member_id, role=ParticipantRole.PARTICIPANT
        )
        participant_repo.get_by_expedition_and_user.side_effect = [
            organiser_participant,
            target_participant,
        ]

        await service.remove_participant(expedition.id, member_id, organiser_id)

        participant_repo.update_status.assert_awaited_once_with(
            expedition.id, member_id, ParticipantStatus.REMOVED
        )


# ---------------------------------------------------------------------------
# update_role
# ---------------------------------------------------------------------------

class TestUpdateRole:

    async def test_raises_403_when_not_organiser(
        self, service, expedition_repo, participant_repo, member_id
    ):
        expedition = _make_expedition()
        expedition_repo.get_by_id.return_value = expedition
        # caller is CO_ORGANIZER, not ORGANIZER — only organiser can change roles
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, member_id, role=ParticipantRole.CO_ORGANIZER
        )

        with pytest.raises(ForbiddenException) as exc_info:
            await service.update_role(
                expedition.id, uuid.uuid4(), ParticipantRole.CO_ORGANIZER, member_id
            )

        assert exc_info.value.error_code == "NOT_ORGANISER"

    async def test_promotes_to_co_organiser(
        self, service, expedition_repo, participant_repo, organiser_id, member_id
    ):
        expedition = _make_expedition()
        expedition_repo.get_by_id.return_value = expedition
        organiser_participant = _make_participant(
            expedition.id, organiser_id, role=ParticipantRole.ORGANIZER
        )
        target = _make_participant(
            expedition.id, member_id, role=ParticipantRole.PARTICIPANT
        )
        promoted = _make_participant(
            expedition.id, member_id, role=ParticipantRole.CO_ORGANIZER
        )
        participant_repo.get_by_expedition_and_user.side_effect = [
            organiser_participant,  # caller check
            target,                 # target lookup
        ]
        participant_repo.update_role.return_value = promoted

        result = await service.update_role(
            expedition.id, member_id, ParticipantRole.CO_ORGANIZER, organiser_id
        )

        assert result.role == ParticipantRole.CO_ORGANIZER
