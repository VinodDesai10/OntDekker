"""
Unit tests for DiscussionService.

Covers CP-TRIP-3A requirements (12 test cases):
  1.  Authenticated member can fetch discussion (list_messages succeeds)
  2.  Organizer can fetch discussion (list_messages succeeds)
  3.  Authenticated member can create a message
  4.  Organizer can create a message
  5.  author_id comes from JWT (current_user_id), not from request body
  6.  Non-member cannot create a message (ForbiddenException)
  7.  Non-member can still fetch discussion (GET requires auth, not membership)
  8.  Empty content rejected (ValidationException from schema + service)
  9.  Excessive content rejected (max 2000 chars)
  10. Messages are returned in oldest-first (ascending created_at) order
  11. Created message is persisted and returned
  12. Non-existent expedition returns NotFoundException
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from shared import ForbiddenException, NotFoundException, ValidationException
from app.schemas.discussion import DiscussionMessageCreate, DISCUSSION_CONTENT_MAX_LENGTH
from app.services.discussion_service import DiscussionService


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------

# Spec classes used so MagicMock raises AttributeError for unknown attributes
# (e.g. camelCase aliases like `expeditionId`). This causes Pydantic's
# from_attributes validation to fall back to the snake_case field name
# instead of picking up the auto-generated MagicMock for the alias.

class _ExpeditionSpec:
    id: UUID
    title: str
    organizer_id: UUID
    created_at: datetime
    updated_at: datetime


class _MessageSpec:
    id: UUID
    expedition_id: UUID
    author_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime


def _make_expedition(expedition_id: UUID | None = None) -> MagicMock:
    e = MagicMock(spec=_ExpeditionSpec)
    e.id = expedition_id or uuid.uuid4()
    e.title = "Alpine Trek"
    e.organizer_id = uuid.uuid4()
    e.created_at = datetime.now(timezone.utc)
    e.updated_at = datetime.now(timezone.utc)
    return e


def _make_message(
    expedition_id: UUID,
    author_id: UUID,
    content: str = "Hello, team!",
    created_at: datetime | None = None,
) -> MagicMock:
    m = MagicMock(spec=_MessageSpec)
    m.id = uuid.uuid4()
    m.expedition_id = expedition_id
    m.author_id = author_id
    m.content = content
    m.created_at = created_at or datetime.now(timezone.utc)
    m.updated_at = m.created_at
    return m


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def expedition_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def discussion_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def participant_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(expedition_repo, discussion_repo, participant_repo) -> DiscussionService:
    return DiscussionService(expedition_repo, discussion_repo, participant_repo)


@pytest.fixture
def expedition_id() -> UUID:
    return uuid.uuid4()


@pytest.fixture
def member_id() -> UUID:
    return uuid.uuid4()


@pytest.fixture
def organizer_id() -> UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# TEST 1 — Authenticated member can fetch discussion
# ---------------------------------------------------------------------------

class TestListMessages:

    async def test_member_can_list_messages(
        self, service, expedition_repo, discussion_repo, expedition_id, member_id
    ):
        """Any authenticated user can fetch discussion; no membership check on GET."""
        expedition_repo.get_by_id.return_value = _make_expedition(expedition_id)
        discussion_repo.count_by_expedition.return_value = 2
        msg1 = _make_message(expedition_id, member_id, "First message")
        msg2 = _make_message(expedition_id, member_id, "Second message")
        discussion_repo.list_by_expedition.return_value = [msg1, msg2]

        result = await service.list_messages(expedition_id)

        assert result.pagination.total_items == 2
        assert len(result.items) == 2
        expedition_repo.get_by_id.assert_awaited_once_with(expedition_id)

    # TEST 2 — Organizer can fetch discussion
    async def test_organizer_can_list_messages(
        self, service, expedition_repo, discussion_repo, expedition_id, organizer_id
    ):
        """Organizer is just another authenticated user for the GET endpoint."""
        expedition_repo.get_by_id.return_value = _make_expedition(expedition_id)
        discussion_repo.count_by_expedition.return_value = 0
        discussion_repo.list_by_expedition.return_value = []

        result = await service.list_messages(expedition_id)

        assert result.pagination.total_items == 0
        assert result.items == []

    # TEST 7 — Non-member can still GET (no membership check on list)
    async def test_non_member_can_list_messages(
        self, service, expedition_repo, discussion_repo, expedition_id
    ):
        """GET has no membership restriction — matches trip detail page behavior."""
        expedition_repo.get_by_id.return_value = _make_expedition(expedition_id)
        discussion_repo.count_by_expedition.return_value = 0
        discussion_repo.list_by_expedition.return_value = []

        # Should not raise
        result = await service.list_messages(expedition_id)
        assert result.pagination.total_items == 0

    # TEST 10 — Messages are returned in oldest-first order
    async def test_messages_ordered_oldest_first(
        self, service, expedition_repo, discussion_repo, expedition_id, member_id
    ):
        """Repository orders by created_at asc; service preserves that order."""
        t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        older = _make_message(expedition_id, member_id, "older", created_at=t1)
        middle = _make_message(expedition_id, member_id, "middle", created_at=t2)
        newest = _make_message(expedition_id, member_id, "newest", created_at=t3)

        expedition_repo.get_by_id.return_value = _make_expedition(expedition_id)
        discussion_repo.count_by_expedition.return_value = 3
        discussion_repo.list_by_expedition.return_value = [older, middle, newest]

        result = await service.list_messages(expedition_id)

        assert [m.created_at for m in result.items] == [t1, t2, t3]

    # TEST 12 — Non-existent expedition returns NotFoundException
    async def test_nonexistent_expedition_raises_not_found(
        self, service, expedition_repo, expedition_id
    ):
        expedition_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await service.list_messages(expedition_id)

        assert exc_info.value.error_code == "TRIP_NOT_FOUND"


# ---------------------------------------------------------------------------
# TEST 3, 4, 5, 6, 8, 9, 11 — create_message
# ---------------------------------------------------------------------------

class TestCreateMessage:

    # TEST 3 — Authenticated member can create a message
    async def test_member_can_post_message(
        self, service, expedition_repo, discussion_repo, participant_repo,
        expedition_id, member_id
    ):
        expedition_repo.get_by_id.return_value = _make_expedition(expedition_id)
        participant_repo.is_participant.return_value = True
        created = _make_message(expedition_id, member_id, "See you all there!")
        discussion_repo.create.return_value = created

        payload = DiscussionMessageCreate(content="See you all there!")
        result = await service.create_message(expedition_id, payload, member_id)

        assert result.author_id == member_id
        assert result.expedition_id == expedition_id
        assert result.content == "See you all there!"

    # TEST 4 — Organizer can create a message
    async def test_organizer_can_post_message(
        self, service, expedition_repo, discussion_repo, participant_repo,
        expedition_id, organizer_id
    ):
        expedition_repo.get_by_id.return_value = _make_expedition(expedition_id)
        participant_repo.is_participant.return_value = True  # organizer is a participant
        created = _make_message(expedition_id, organizer_id, "Welcome everyone!")
        discussion_repo.create.return_value = created

        payload = DiscussionMessageCreate(content="Welcome everyone!")
        result = await service.create_message(expedition_id, payload, organizer_id)

        assert result.author_id == organizer_id

    # TEST 5 — author_id comes from current_user_id (JWT), not from payload
    async def test_author_id_comes_from_jwt_not_payload(
        self, service, expedition_repo, discussion_repo, participant_repo,
        expedition_id, member_id
    ):
        """The service always passes current_user_id as author_id to the repo,
        regardless of anything in the payload (payload has no author_id field)."""
        expedition_repo.get_by_id.return_value = _make_expedition(expedition_id)
        participant_repo.is_participant.return_value = True
        created = _make_message(expedition_id, member_id, "My message")
        discussion_repo.create.return_value = created

        payload = DiscussionMessageCreate(content="My message")
        await service.create_message(expedition_id, payload, member_id)

        # Verify repo was called with the JWT user's ID as author_id
        discussion_repo.create.assert_awaited_once_with(
            expedition_id=expedition_id,
            author_id=member_id,
            content="My message",
        )

    # TEST 6 — Non-member cannot create a message
    async def test_non_member_cannot_post_message(
        self, service, expedition_repo, participant_repo,
        expedition_id
    ):
        outsider_id = uuid.uuid4()
        expedition_repo.get_by_id.return_value = _make_expedition(expedition_id)
        participant_repo.is_participant.return_value = False  # outsider not a member

        payload = DiscussionMessageCreate(content="Can I sneak in?")
        with pytest.raises(ForbiddenException) as exc_info:
            await service.create_message(expedition_id, payload, outsider_id)

        assert exc_info.value.error_code == "NOT_EXPEDITION_MEMBER"

    # TEST 8 — Empty content is rejected
    async def test_empty_content_rejected_by_schema(self):
        """Schema validator rejects empty/whitespace-only content before service."""
        with pytest.raises(Exception):  # pydantic ValidationError
            DiscussionMessageCreate(content="")

    async def test_whitespace_only_content_rejected_by_service(
        self, service, expedition_repo, participant_repo,
        expedition_id, member_id
    ):
        """Service-level whitespace guard (belt-and-suspenders)."""
        expedition_repo.get_by_id.return_value = _make_expedition(expedition_id)
        participant_repo.is_participant.return_value = True

        # Bypass schema by constructing payload and mutating content directly
        payload = DiscussionMessageCreate(content="valid")
        payload.content = "   "  # mutate after construction

        with pytest.raises(ValidationException) as exc_info:
            await service.create_message(expedition_id, payload, member_id)

        assert exc_info.value.error_code == "CONTENT_EMPTY"

    # TEST 9 — Excessive content rejected
    async def test_excessive_content_rejected_by_schema(self):
        """Schema max_length=2000 catches oversized content."""
        with pytest.raises(Exception):  # pydantic ValidationError
            DiscussionMessageCreate(content="x" * (DISCUSSION_CONTENT_MAX_LENGTH + 1))

    async def test_excessive_content_rejected_by_service(
        self, service, expedition_repo, participant_repo,
        expedition_id, member_id
    ):
        """Service-level length guard (belt-and-suspenders)."""
        expedition_repo.get_by_id.return_value = _make_expedition(expedition_id)
        participant_repo.is_participant.return_value = True

        payload = DiscussionMessageCreate(content="valid")
        payload.content = "x" * (DISCUSSION_CONTENT_MAX_LENGTH + 1)  # mutate

        with pytest.raises(ValidationException) as exc_info:
            await service.create_message(expedition_id, payload, member_id)

        assert exc_info.value.error_code == "CONTENT_TOO_LONG"

    # TEST 11 — Created message is persisted (repo.create called with correct args)
    async def test_created_message_is_persisted(
        self, service, expedition_repo, discussion_repo, participant_repo,
        expedition_id, member_id
    ):
        expedition_repo.get_by_id.return_value = _make_expedition(expedition_id)
        participant_repo.is_participant.return_value = True
        persisted = _make_message(expedition_id, member_id, "Pack your bags!")
        discussion_repo.create.return_value = persisted

        payload = DiscussionMessageCreate(content="Pack your bags!")
        result = await service.create_message(expedition_id, payload, member_id)

        # Repo was called exactly once with the right params
        discussion_repo.create.assert_awaited_once_with(
            expedition_id=expedition_id,
            author_id=member_id,
            content="Pack your bags!",
        )
        # Returned message ID matches what the repo returned
        assert result.id == persisted.id

    # TEST 12 (POST) — Non-existent expedition returns NotFoundException
    async def test_post_to_nonexistent_expedition_raises_not_found(
        self, service, expedition_repo, expedition_id, member_id
    ):
        expedition_repo.get_by_id.return_value = None

        payload = DiscussionMessageCreate(content="Hello?")
        with pytest.raises(NotFoundException) as exc_info:
            await service.create_message(expedition_id, payload, member_id)

        assert exc_info.value.error_code == "TRIP_NOT_FOUND"
