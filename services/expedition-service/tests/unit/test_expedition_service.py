"""
Unit tests for ExpeditionService.

All repositories are replaced with AsyncMock so no database is required.
Tests verify business rules: 404 guards, state machine transitions,
ownership guards, terminal-state edit blocking, and soft-delete rules.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from shared import ForbiddenException, NotFoundException, ValidationException
from app.models.expedition import ExpeditionStatus, ExpeditionVisibility
from app.models.participant import ParticipantRole, ParticipantStatus
from app.schemas.expedition import ExpeditionCreate, ExpeditionUpdate
from app.schemas.common import ExpeditionFilter
from app.services.expedition_service import ExpeditionService


# ---------------------------------------------------------------------------
# Helpers — build fake ORM-like objects (SimpleNamespace works with
# model_validate because Pydantic v2 from_attributes reads __dict__)
# ---------------------------------------------------------------------------

def _make_expedition(
    status: ExpeditionStatus = ExpeditionStatus.DRAFT,
    visibility: ExpeditionVisibility = ExpeditionVisibility.PUBLIC,
    max_participants: int = 10,
) -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    e.community_id = uuid.uuid4()
    e.organizer_id = uuid.uuid4()
    e.title = "Test Expedition"
    e.destination = "Nepal"
    e.description = "A test expedition"
    e.meeting_point = None
    e.start_date = None
    e.end_date = None
    e.max_participants = max_participants
    e.budget = Decimal("1000.00")
    e.visibility = visibility
    e.status = status
    e.cover_image_url = None
    e.is_deleted = False
    e.deleted_at = None
    e.deleted_by = None
    e.created_at = datetime.now(timezone.utc)
    e.updated_at = datetime.now(timezone.utc)
    e.created_by = uuid.uuid4()
    e.updated_by = None
    return e


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
def participant_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(expedition_repo, participant_repo) -> ExpeditionService:
    return ExpeditionService(expedition_repo, participant_repo)


@pytest.fixture
def organiser_id() -> UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# get_expedition
# ---------------------------------------------------------------------------

class TestGetExpedition:

    async def test_returns_expedition_when_found(self, service, expedition_repo):
        expedition = _make_expedition()
        expedition_repo.get_by_id.return_value = expedition

        result = await service.get_expedition(expedition.id)

        assert result.id == expedition.id
        expedition_repo.get_by_id.assert_awaited_once_with(expedition.id)

    async def test_raises_404_when_not_found(self, service, expedition_repo):
        expedition_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await service.get_expedition(uuid.uuid4())

        assert exc_info.value.error_code == "EXPEDITION_NOT_FOUND"


# ---------------------------------------------------------------------------
# create_expedition
# ---------------------------------------------------------------------------

class TestCreateExpedition:

    async def test_creates_and_adds_organiser_participant(
        self, service, expedition_repo, participant_repo, organiser_id
    ):
        expedition = _make_expedition()
        expedition.organizer_id = organiser_id
        expedition_repo.create.return_value = expedition
        participant_repo.add.return_value = _make_participant(expedition.id, organiser_id)

        payload = ExpeditionCreate(
            community_id=uuid.uuid4(),
            title="Everest Trek",
            destination="Nepal",
            visibility=ExpeditionVisibility.PUBLIC,
            max_participants=10,
        )
        result = await service.create_expedition(payload, organiser_id)

        assert result.id == expedition.id
        # Organiser auto-added as participant
        participant_repo.add.assert_awaited_once()
        call_kwargs = participant_repo.add.call_args.kwargs
        assert call_kwargs["user_id"] == organiser_id
        assert call_kwargs["role"] == ParticipantRole.ORGANIZER


# ---------------------------------------------------------------------------
# update_expedition
# ---------------------------------------------------------------------------

class TestUpdateExpedition:

    async def test_raises_404_when_expedition_not_found(
        self, service, expedition_repo
    ):
        expedition_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException):
            await service.update_expedition(
                uuid.uuid4(), ExpeditionUpdate(title="New"), uuid.uuid4()
            )

    async def test_raises_403_when_not_organiser_or_co(
        self, service, expedition_repo, participant_repo
    ):
        expedition = _make_expedition(status=ExpeditionStatus.DRAFT)
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = None

        with pytest.raises(ForbiddenException) as exc_info:
            await service.update_expedition(
                expedition.id, ExpeditionUpdate(title="New"), uuid.uuid4()
            )

        assert exc_info.value.error_code == "NOT_ORGANISER_OR_CO"

    @pytest.mark.parametrize("terminal_status", [
        ExpeditionStatus.COMPLETED,
        ExpeditionStatus.CANCELLED,
        ExpeditionStatus.ARCHIVED,
    ])
    async def test_raises_422_on_terminal_status(
        self, service, expedition_repo, participant_repo, organiser_id, terminal_status
    ):
        expedition = _make_expedition(status=terminal_status)
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, organiser_id, role=ParticipantRole.ORGANIZER
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.update_expedition(
                expedition.id, ExpeditionUpdate(title="New"), organiser_id
            )

        assert exc_info.value.error_code == "EXPEDITION_NOT_EDITABLE"

    async def test_updates_successfully(
        self, service, expedition_repo, participant_repo, organiser_id
    ):
        expedition = _make_expedition(status=ExpeditionStatus.DRAFT)
        updated = _make_expedition(status=ExpeditionStatus.DRAFT)
        updated.title = "Updated Title"
        expedition_repo.get_by_id.return_value = expedition
        expedition_repo.update.return_value = updated
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, organiser_id, role=ParticipantRole.ORGANIZER
        )

        result = await service.update_expedition(
            expedition.id, ExpeditionUpdate(title="Updated Title"), organiser_id
        )

        assert result.title == "Updated Title"


# ---------------------------------------------------------------------------
# transition_status
# ---------------------------------------------------------------------------

class TestTransitionStatus:

    async def test_raises_404_when_not_found(self, service, expedition_repo):
        expedition_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException):
            await service.transition_status(
                uuid.uuid4(), ExpeditionStatus.PUBLISHED, uuid.uuid4()
            )

    async def test_raises_403_when_not_organiser(
        self, service, expedition_repo, participant_repo
    ):
        expedition = _make_expedition(status=ExpeditionStatus.DRAFT)
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = None

        with pytest.raises(ForbiddenException):
            await service.transition_status(
                expedition.id, ExpeditionStatus.PUBLISHED, uuid.uuid4()
            )

    @pytest.mark.parametrize("current,target", [
        (ExpeditionStatus.DRAFT, ExpeditionStatus.ACTIVE),      # skip PUBLISHED
        (ExpeditionStatus.COMPLETED, ExpeditionStatus.DRAFT),   # backwards
        (ExpeditionStatus.CANCELLED, ExpeditionStatus.DRAFT),   # from terminal
        (ExpeditionStatus.ARCHIVED, ExpeditionStatus.DRAFT),    # from terminal
    ])
    async def test_raises_422_on_invalid_transition(
        self, service, expedition_repo, participant_repo, organiser_id, current, target
    ):
        expedition = _make_expedition(status=current)
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, organiser_id, role=ParticipantRole.ORGANIZER
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.transition_status(expedition.id, target, organiser_id)

        assert exc_info.value.error_code == "INVALID_STATUS_TRANSITION"

    @pytest.mark.parametrize("current,target", [
        (ExpeditionStatus.DRAFT, ExpeditionStatus.PUBLISHED),
        (ExpeditionStatus.PUBLISHED, ExpeditionStatus.ACTIVE),
        (ExpeditionStatus.ACTIVE, ExpeditionStatus.COMPLETED),
        (ExpeditionStatus.COMPLETED, ExpeditionStatus.ARCHIVED),
        (ExpeditionStatus.DRAFT, ExpeditionStatus.CANCELLED),
        (ExpeditionStatus.PUBLISHED, ExpeditionStatus.CANCELLED),
        (ExpeditionStatus.ACTIVE, ExpeditionStatus.CANCELLED),
    ])
    async def test_valid_transitions_succeed(
        self, service, expedition_repo, participant_repo, organiser_id, current, target
    ):
        expedition = _make_expedition(status=current)
        transitioned = _make_expedition(status=target)
        expedition_repo.get_by_id.return_value = expedition
        expedition_repo.update_status.return_value = transitioned
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, organiser_id, role=ParticipantRole.ORGANIZER
        )

        result = await service.transition_status(expedition.id, target, organiser_id)

        assert result.status == target
        expedition_repo.update_status.assert_awaited_once()


# ---------------------------------------------------------------------------
# delete_expedition
# ---------------------------------------------------------------------------

class TestDeleteExpedition:

    async def test_raises_404_when_not_found(self, service, expedition_repo):
        expedition_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException):
            await service.delete_expedition(uuid.uuid4(), uuid.uuid4())

    async def test_raises_403_when_not_organiser(
        self, service, expedition_repo, participant_repo
    ):
        expedition = _make_expedition(status=ExpeditionStatus.DRAFT)
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = None

        with pytest.raises(ForbiddenException):
            await service.delete_expedition(expedition.id, uuid.uuid4())

    @pytest.mark.parametrize("non_deletable_status", [
        ExpeditionStatus.PUBLISHED,
        ExpeditionStatus.ACTIVE,
        ExpeditionStatus.COMPLETED,
    ])
    async def test_raises_422_on_non_deletable_status(
        self, service, expedition_repo, participant_repo, organiser_id, non_deletable_status
    ):
        expedition = _make_expedition(status=non_deletable_status)
        expedition_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, organiser_id, role=ParticipantRole.ORGANIZER
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.delete_expedition(expedition.id, organiser_id)

        assert exc_info.value.error_code == "EXPEDITION_NOT_DELETABLE"

    @pytest.mark.parametrize("deletable_status", [
        ExpeditionStatus.DRAFT,
        ExpeditionStatus.CANCELLED,
        ExpeditionStatus.ARCHIVED,
    ])
    async def test_soft_deletes_allowed_statuses(
        self, service, expedition_repo, participant_repo, organiser_id, deletable_status
    ):
        expedition = _make_expedition(status=deletable_status)
        expedition_repo.get_by_id.return_value = expedition
        expedition_repo.soft_delete.return_value = True
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, organiser_id, role=ParticipantRole.ORGANIZER
        )

        await service.delete_expedition(expedition.id, organiser_id)

        expedition_repo.soft_delete.assert_awaited_once_with(
            expedition.id, deleted_by=organiser_id
        )


# ---------------------------------------------------------------------------
# list_expeditions
# ---------------------------------------------------------------------------

class TestListExpeditions:

    async def test_returns_paginated_response(
        self, service, expedition_repo
    ):
        expeditions = [_make_expedition() for _ in range(3)]
        expedition_repo.list_expeditions.return_value = (expeditions, 3)

        filters = ExpeditionFilter(page=1, page_size=20)
        result = await service.list_expeditions(filters)

        assert result.pagination.total_items == 3
        assert len(result.items) == 3

    async def test_empty_list_returns_valid_response(
        self, service, expedition_repo
    ):
        expedition_repo.list_expeditions.return_value = ([], 0)

        filters = ExpeditionFilter(page=1, page_size=20)
        result = await service.list_expeditions(filters)

        assert result.pagination.total_items == 0
        assert result.pagination.total_pages == 1
        assert result.items == []
