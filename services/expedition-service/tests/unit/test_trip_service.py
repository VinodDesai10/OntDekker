"""
Unit tests for TripService.

Covers CP-TRIP-2B-2 requirements:
  - Organizer is auto-created on trip creation with role=ORGANIZER, status=ACTIVE
  - Participant count starts at 1 after creation (not 0)
  - join_trip raises ConflictException (ALREADY_MEMBER) for duplicate registration
  - join_trip raises ValidationException (TRIP_FULL) when at capacity
  - leave_trip raises ValidationException (HOST_CANNOT_LEAVE) for organizer
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import UUID

import pytest

from shared import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.models.expedition import ExpeditionStatus, ExpeditionVisibility
from app.models.participant import ParticipantRole, ParticipantStatus
from app.schemas.trip import TripCreate
from app.services.trip_service import TripService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_expedition(
    organizer_id: UUID,
    max_participants: int = 13,
    status: ExpeditionStatus = ExpeditionStatus.PUBLISHED,
    visibility: ExpeditionVisibility = ExpeditionVisibility.PUBLIC,
) -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    e.organizer_id = organizer_id
    e.community_id = None
    e.title = "Test Trip"
    e.destination = "Test Destination"
    e.description = None
    e.cover_image_url = None
    e.start_date = None
    e.end_date = None
    e.budget = None
    e.max_participants = max_participants
    e.visibility = visibility
    e.status = status
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
    p.joined_at = datetime.now(timezone.utc)
    p.created_at = datetime.now(timezone.utc)
    p.updated_at = datetime.now(timezone.utc)
    return p


def _make_create_payload(max_participants: int = 13) -> TripCreate:
    return TripCreate(
        title="Test Trip",
        destination="Test Destination",
        max_participants=max_participants,
        visibility=ExpeditionVisibility.PUBLIC,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def trip_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def participant_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(trip_repo, participant_repo) -> TripService:
    return TripService(trip_repo, participant_repo)


@pytest.fixture
def organizer_id() -> UUID:
    return uuid.uuid4()


@pytest.fixture
def member_id() -> UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# create_trip — organizer auto-creation
# ---------------------------------------------------------------------------

class TestCreateTrip:

    async def test_organizer_participant_is_created_on_trip_creation(
        self, service, trip_repo, participant_repo, organizer_id
    ):
        """After creating a trip, participant_repo.add must be called with ORGANIZER role."""
        expedition = _make_expedition(organizer_id)
        trip_repo.create.return_value = expedition

        organizer_participant = _make_participant(
            expedition.id, organizer_id, role=ParticipantRole.ORGANIZER
        )
        participant_repo.add.return_value = organizer_participant

        payload = _make_create_payload()
        result = await service.create_trip(payload, organizer_id)

        # Participant repo must have been called with ORGANIZER role
        participant_repo.add.assert_awaited_once_with(
            expedition_id=expedition.id,
            user_id=organizer_id,
            role=ParticipantRole.ORGANIZER,
        )

    async def test_create_trip_returns_count_of_1(
        self, service, trip_repo, participant_repo, organizer_id
    ):
        """Immediately after creation, current_participants_count must be 1."""
        expedition = _make_expedition(organizer_id)
        trip_repo.create.return_value = expedition
        participant_repo.add.return_value = _make_participant(
            expedition.id, organizer_id, role=ParticipantRole.ORGANIZER
        )

        payload = _make_create_payload()
        result = await service.create_trip(payload, organizer_id)

        assert result.current_participants_count == 1

    async def test_create_trip_sets_host_id_to_organizer(
        self, service, trip_repo, participant_repo, organizer_id
    ):
        """The returned TripResponse.host_id must equal the creator's user_id."""
        expedition = _make_expedition(organizer_id)
        trip_repo.create.return_value = expedition
        participant_repo.add.return_value = _make_participant(
            expedition.id, organizer_id, role=ParticipantRole.ORGANIZER
        )

        payload = _make_create_payload()
        result = await service.create_trip(payload, organizer_id)

        assert result.host_id == organizer_id


# ---------------------------------------------------------------------------
# join_trip — duplicate registration prevention
# ---------------------------------------------------------------------------

class TestJoinTrip:

    async def test_raises_conflict_when_user_already_member(
        self, service, trip_repo, participant_repo, organizer_id, member_id
    ):
        """Joining a trip you already joined raises ALREADY_MEMBER."""
        expedition = _make_expedition(organizer_id)
        trip_repo.get_by_id.return_value = expedition
        # Simulate existing ACTIVE participant record
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, member_id, role=ParticipantRole.PARTICIPANT
        )

        with pytest.raises(ConflictException) as exc_info:
            await service.join_trip(expedition.id, member_id)

        assert exc_info.value.error_code == "ALREADY_MEMBER"
        # Ensure no new participant row is created
        participant_repo.add.assert_not_awaited()

    async def test_organizer_cannot_rejoin_their_own_trip(
        self, service, trip_repo, participant_repo, organizer_id
    ):
        """The organizer is already a participant — rejoin must raise ALREADY_MEMBER."""
        expedition = _make_expedition(organizer_id)
        trip_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, organizer_id, role=ParticipantRole.ORGANIZER
        )

        with pytest.raises(ConflictException) as exc_info:
            await service.join_trip(expedition.id, organizer_id)

        assert exc_info.value.error_code == "ALREADY_MEMBER"

    async def test_raises_trip_full_when_at_capacity(
        self, service, trip_repo, participant_repo, organizer_id, member_id
    ):
        """Joining a full trip raises TRIP_FULL."""
        expedition = _make_expedition(organizer_id, max_participants=1)
        trip_repo.get_by_id.return_value = expedition
        # Not already a member
        participant_repo.get_by_expedition_and_user.return_value = None
        # Already at max
        trip_repo.count_active_participants.return_value = 1

        with pytest.raises(ValidationException) as exc_info:
            await service.join_trip(expedition.id, member_id)

        assert exc_info.value.error_code == "TRIP_FULL"
        participant_repo.add.assert_not_awaited()

    async def test_new_user_can_join_open_trip(
        self, service, trip_repo, participant_repo, organizer_id, member_id
    ):
        """A non-member can join a public trip with available capacity."""
        expedition = _make_expedition(organizer_id, max_participants=13)
        trip_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = None
        trip_repo.count_active_participants.return_value = 1  # organizer already in

        await service.join_trip(expedition.id, member_id)

        participant_repo.add.assert_awaited_once_with(
            expedition_id=expedition.id,
            user_id=member_id,
            role=ParticipantRole.PARTICIPANT,
        )

    async def test_cannot_join_private_trip_directly(
        self, service, trip_repo, participant_repo, organizer_id, member_id
    ):
        """Direct join on a PRIVATE trip raises TRIP_PRIVATE."""
        expedition = _make_expedition(
            organizer_id, visibility=ExpeditionVisibility.PRIVATE
        )
        trip_repo.get_by_id.return_value = expedition

        with pytest.raises(ValidationException) as exc_info:
            await service.join_trip(expedition.id, member_id)

        assert exc_info.value.error_code == "TRIP_PRIVATE"


# ---------------------------------------------------------------------------
# leave_trip
# ---------------------------------------------------------------------------

class TestLeaveTrip:

    async def test_organizer_cannot_leave(
        self, service, trip_repo, participant_repo, organizer_id
    ):
        """The trip host (ORGANIZER) cannot leave their own trip."""
        expedition = _make_expedition(organizer_id)
        trip_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, organizer_id, role=ParticipantRole.ORGANIZER
        )

        with pytest.raises(ValidationException) as exc_info:
            await service.leave_trip(expedition.id, organizer_id)

        assert exc_info.value.error_code == "HOST_CANNOT_LEAVE"

    async def test_participant_can_leave(
        self, service, trip_repo, participant_repo, organizer_id, member_id
    ):
        """A regular participant can leave a trip."""
        expedition = _make_expedition(organizer_id)
        trip_repo.get_by_id.return_value = expedition
        participant_repo.get_by_expedition_and_user.return_value = _make_participant(
            expedition.id, member_id, role=ParticipantRole.PARTICIPANT
        )

        await service.leave_trip(expedition.id, member_id)

        participant_repo.update_status.assert_awaited_once_with(
            expedition.id, member_id, ParticipantStatus.LEFT
        )


# ---------------------------------------------------------------------------
# delete_trip — organizer authorization + soft delete behavior
# ---------------------------------------------------------------------------

class TestDeleteTrip:

    async def test_organizer_can_delete_own_trip(
        self, service, trip_repo, participant_repo, organizer_id
    ):
        """The trip organizer can successfully delete (soft-delete) their trip."""
        expedition = _make_expedition(organizer_id)
        trip_repo.get_by_id.return_value = expedition
        trip_repo.soft_delete.return_value = True

        await service.delete_trip(expedition.id, organizer_id)

        trip_repo.soft_delete.assert_awaited_once_with(
            expedition.id, deleted_by=organizer_id
        )

    async def test_non_organizer_cannot_delete_trip(
        self, service, trip_repo, participant_repo, organizer_id, member_id
    ):
        """A non-organizer attempting DELETE must receive ForbiddenException (NOT_HOST)."""
        expedition = _make_expedition(organizer_id)
        trip_repo.get_by_id.return_value = expedition

        with pytest.raises(ForbiddenException) as exc_info:
            await service.delete_trip(expedition.id, member_id)

        assert exc_info.value.error_code == "NOT_HOST"
        # soft_delete must NOT be called
        trip_repo.soft_delete.assert_not_awaited()

    async def test_delete_nonexistent_trip_raises_not_found(
        self, service, trip_repo, participant_repo, organizer_id
    ):
        """Deleting a non-existent trip raises NotFoundException (TRIP_NOT_FOUND)."""
        trip_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await service.delete_trip(uuid.uuid4(), organizer_id)

        assert exc_info.value.error_code == "TRIP_NOT_FOUND"
        trip_repo.soft_delete.assert_not_awaited()

    async def test_deleted_trip_is_not_retrievable(
        self, service, trip_repo, participant_repo, organizer_id
    ):
        """After deletion, get_trip raises NotFoundException because get_by_id returns None."""
        expedition_id = uuid.uuid4()
        # After soft-delete, get_by_id returns None (is_deleted=True excluded by repo query)
        trip_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await service.get_trip(expedition_id)

        assert exc_info.value.error_code == "TRIP_NOT_FOUND"

    async def test_second_user_cannot_delete_trip_created_by_first(
        self, service, trip_repo, participant_repo, organizer_id
    ):
        """
        Test 2 from the spec: User B cannot delete User A's trip.

        User A creates Trip Y. User B (a participant) calls DELETE.
        Backend must return ForbiddenException regardless of UI hiding.
        """
        user_a_id = organizer_id
        user_b_id = uuid.uuid4()

        expedition = _make_expedition(user_a_id)
        trip_repo.get_by_id.return_value = expedition

        with pytest.raises(ForbiddenException) as exc_info:
            await service.delete_trip(expedition.id, user_b_id)

        assert exc_info.value.error_code == "NOT_HOST"
        trip_repo.soft_delete.assert_not_awaited()

        # Verify User A CAN still delete it
        trip_repo.soft_delete.return_value = True
        await service.delete_trip(expedition.id, user_a_id)
        trip_repo.soft_delete.assert_awaited_once_with(
            expedition.id, deleted_by=user_a_id
        )
