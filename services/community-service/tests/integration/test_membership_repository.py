"""
CP-16E.2 — MembershipRepository Integration Tests

Validates repository-level behaviour for MembershipRepository.
All tests use an in-memory SQLite database via the db_session fixture.

CommunityMember and JoinRequest writes use session.flush() (no commit),
so tests may need await db_session.commit() before re-querying via the
repository when the session is shared within the same test.
"""

import uuid
import pytest

from app.repositories.membership_repository import MembershipRepository
from shared.constants.status import (
    MemberRole,
    MembershipStatus,
    JoinRequestStatus,
)
from tests.conftest import TEST_USER_ID, TEST_OTHER_USER_ID
from tests.utils import create_test_community, create_test_member


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo(session) -> MembershipRepository:
    return MembershipRepository(session)


# ===========================================================================
# get_member
# ===========================================================================

@pytest.mark.integration
async def test_get_member_returns_active_member(db_session):
    """get_member() returns the membership record for an active member."""
    community = await create_test_community(db_session)
    await db_session.commit()
    await create_test_member(db_session, community_id=community.id, user_id=TEST_USER_ID)
    await db_session.commit()

    repo = _repo(db_session)
    member = await repo.get_member(community.id, TEST_USER_ID)

    assert member is not None
    assert member.user_id == TEST_USER_ID
    assert member.community_id == community.id


@pytest.mark.integration
async def test_get_member_returns_member_regardless_of_status(db_session):
    """get_member() returns membership records for any status (not just ACTIVE)."""
    community = await create_test_community(db_session)
    await db_session.commit()
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_USER_ID,
        status=MembershipStatus.LEFT,
    )
    await db_session.commit()

    repo = _repo(db_session)
    member = await repo.get_member(community.id, TEST_USER_ID)

    assert member is not None
    assert member.status == MembershipStatus.LEFT


@pytest.mark.integration
async def test_get_member_returns_none_when_not_a_member(db_session):
    """get_member() returns None when the user is not a member of the community."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    result = await repo.get_member(community.id, TEST_USER_ID)

    assert result is None


@pytest.mark.integration
async def test_get_member_returns_none_for_wrong_community(db_session):
    """get_member() returns None when community_id does not match."""
    community = await create_test_community(db_session)
    other_community = await create_test_community(db_session, name="Other")
    await db_session.commit()
    await create_test_member(db_session, community_id=community.id, user_id=TEST_USER_ID)
    await db_session.commit()

    repo = _repo(db_session)
    result = await repo.get_member(other_community.id, TEST_USER_ID)

    assert result is None


# ===========================================================================
# get_active_member
# ===========================================================================

@pytest.mark.integration
async def test_get_active_member_returns_active_member(db_session):
    """get_active_member() returns the record when status=ACTIVE."""
    community = await create_test_community(db_session)
    await db_session.commit()
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_USER_ID,
        status=MembershipStatus.ACTIVE,
    )
    await db_session.commit()

    repo = _repo(db_session)
    member = await repo.get_active_member(community.id, TEST_USER_ID)

    assert member is not None
    assert member.status == MembershipStatus.ACTIVE


@pytest.mark.integration
async def test_get_active_member_returns_none_for_left_member(db_session):
    """get_active_member() returns None when member status is LEFT."""
    community = await create_test_community(db_session)
    await db_session.commit()
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_USER_ID,
        status=MembershipStatus.LEFT,
    )
    await db_session.commit()

    repo = _repo(db_session)
    result = await repo.get_active_member(community.id, TEST_USER_ID)

    assert result is None


@pytest.mark.integration
async def test_get_active_member_returns_none_for_banned_member(db_session):
    """get_active_member() returns None when member status is BANNED."""
    community = await create_test_community(db_session)
    await db_session.commit()
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_USER_ID,
        status=MembershipStatus.BANNED,
    )
    await db_session.commit()

    repo = _repo(db_session)
    result = await repo.get_active_member(community.id, TEST_USER_ID)

    assert result is None


@pytest.mark.integration
async def test_get_active_member_returns_none_when_not_a_member(db_session):
    """get_active_member() returns None when user has no membership record."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    result = await repo.get_active_member(community.id, uuid.uuid4())

    assert result is None


# ===========================================================================
# list_members
# ===========================================================================

@pytest.mark.integration
async def test_list_members_returns_active_members(db_session):
    """list_members() returns only ACTIVE members."""
    community = await create_test_community(db_session)
    await db_session.commit()
    await create_test_member(db_session, community_id=community.id, user_id=uuid.uuid4())
    await create_test_member(db_session, community_id=community.id, user_id=uuid.uuid4())
    await db_session.commit()

    repo = _repo(db_session)
    members, total = await repo.list_members(community.id)

    assert total == 2
    assert all(m.status == MembershipStatus.ACTIVE for m in members)


@pytest.mark.integration
async def test_list_members_excludes_non_active_members(db_session):
    """list_members() excludes LEFT, REMOVED, and BANNED members."""
    community = await create_test_community(db_session)
    await db_session.commit()
    active_user = uuid.uuid4()
    await create_test_member(
        db_session, community_id=community.id, user_id=active_user, status=MembershipStatus.ACTIVE
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=uuid.uuid4(), status=MembershipStatus.LEFT
    )
    await db_session.commit()

    repo = _repo(db_session)
    members, total = await repo.list_members(community.id)

    assert total == 1
    assert members[0].user_id == active_user


@pytest.mark.integration
async def test_list_members_filter_by_role(db_session):
    """list_members() with role filter returns only members with that role."""
    community = await create_test_community(db_session)
    await db_session.commit()
    mod_user = uuid.uuid4()
    await create_test_member(
        db_session, community_id=community.id, user_id=mod_user, role=MemberRole.MODERATOR
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=uuid.uuid4(), role=MemberRole.MEMBER
    )
    await db_session.commit()

    repo = _repo(db_session)
    members, total = await repo.list_members(community.id, role=MemberRole.MODERATOR)

    assert total == 1
    assert members[0].user_id == mod_user
    assert members[0].role == MemberRole.MODERATOR


@pytest.mark.integration
async def test_list_members_respects_limit(db_session):
    """list_members() respects the limit parameter."""
    community = await create_test_community(db_session)
    await db_session.commit()
    for _ in range(5):
        await create_test_member(db_session, community_id=community.id, user_id=uuid.uuid4())
    await db_session.commit()

    repo = _repo(db_session)
    members, total = await repo.list_members(community.id, limit=2, offset=0)

    assert len(members) == 2
    assert total == 5


@pytest.mark.integration
async def test_list_members_respects_offset(db_session):
    """list_members() with offset skips earlier results."""
    community = await create_test_community(db_session)
    await db_session.commit()
    for _ in range(4):
        await create_test_member(db_session, community_id=community.id, user_id=uuid.uuid4())
    await db_session.commit()

    repo = _repo(db_session)
    all_members, _ = await repo.list_members(community.id, limit=100, offset=0)
    paged_members, _ = await repo.list_members(community.id, limit=100, offset=2)

    assert len(paged_members) == len(all_members) - 2


@pytest.mark.integration
async def test_list_members_returns_empty_for_community_with_no_members(db_session):
    """list_members() returns empty list and total=0 for a community with no members."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    members, total = await repo.list_members(community.id)

    assert members == [] or list(members) == []
    assert total == 0


@pytest.mark.integration
async def test_list_members_ordered_by_created_at(db_session):
    """list_members() returns members ordered by created_at ascending."""
    community = await create_test_community(db_session)
    await db_session.commit()
    u1 = uuid.uuid4()
    u2 = uuid.uuid4()
    await create_test_member(db_session, community_id=community.id, user_id=u1)
    await db_session.commit()
    await create_test_member(db_session, community_id=community.id, user_id=u2)
    await db_session.commit()

    repo = _repo(db_session)
    members, _ = await repo.list_members(community.id, limit=10)

    user_ids = [m.user_id for m in members]
    assert user_ids.index(u1) < user_ids.index(u2)


# ===========================================================================
# add_member
# ===========================================================================

@pytest.mark.integration
async def test_add_member_returns_member_with_id(db_session):
    """add_member() creates and returns a CommunityMember with a UUID id."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    member = await repo.add_member(community.id, TEST_USER_ID)

    assert member is not None
    assert member.id is not None
    assert isinstance(member.id, uuid.UUID)


@pytest.mark.integration
async def test_add_member_stores_community_and_user(db_session):
    """add_member() persists community_id and user_id."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    member = await repo.add_member(community.id, TEST_USER_ID)

    assert member.community_id == community.id
    assert member.user_id == TEST_USER_ID


@pytest.mark.integration
async def test_add_member_default_role_is_member(db_session):
    """add_member() defaults to MemberRole.MEMBER."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    member = await repo.add_member(community.id, TEST_USER_ID)

    assert member.role == MemberRole.MEMBER


@pytest.mark.integration
async def test_add_member_default_status_is_active(db_session):
    """add_member() defaults to MembershipStatus.ACTIVE."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    member = await repo.add_member(community.id, TEST_USER_ID)

    assert member.status == MembershipStatus.ACTIVE


@pytest.mark.integration
async def test_add_member_with_explicit_role(db_session):
    """add_member() persists the explicitly specified role."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    member = await repo.add_member(community.id, TEST_USER_ID, role=MemberRole.MODERATOR)

    assert member.role == MemberRole.MODERATOR


@pytest.mark.integration
async def test_add_member_with_explicit_status(db_session):
    """add_member() persists the explicitly specified status."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    member = await repo.add_member(
        community.id, TEST_USER_ID, status=MembershipStatus.BANNED
    )

    assert member.status == MembershipStatus.BANNED


# ===========================================================================
# update_member_role
# ===========================================================================

@pytest.mark.integration
async def test_update_member_role_changes_role(db_session):
    """update_member_role() persists the new role and returns the updated member."""
    community = await create_test_community(db_session)
    await db_session.commit()
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.MEMBER
    )
    await db_session.commit()

    repo = _repo(db_session)
    updated = await repo.update_member_role(community.id, TEST_USER_ID, MemberRole.MODERATOR)

    assert updated is not None
    assert updated.role == MemberRole.MODERATOR


@pytest.mark.integration
async def test_update_member_role_returns_none_for_non_member(db_session):
    """update_member_role() returns a record only if the member exists; None user means no row."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    # No member row for this user — get_member will return None
    result = await repo.update_member_role(community.id, uuid.uuid4(), MemberRole.MODERATOR)

    assert result is None


# ===========================================================================
# update_member_status
# ===========================================================================

@pytest.mark.integration
async def test_update_member_status_changes_status(db_session):
    """update_member_status() persists the new status and returns the updated member."""
    community = await create_test_community(db_session)
    await db_session.commit()
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, status=MembershipStatus.ACTIVE
    )
    await db_session.commit()

    repo = _repo(db_session)
    updated = await repo.update_member_status(community.id, TEST_USER_ID, MembershipStatus.LEFT)

    assert updated is not None
    assert updated.status == MembershipStatus.LEFT


@pytest.mark.integration
async def test_update_member_status_can_also_change_role(db_session):
    """update_member_status() with role kwarg updates both status and role."""
    community = await create_test_community(db_session)
    await db_session.commit()
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.MEMBER
    )
    await db_session.commit()

    repo = _repo(db_session)
    updated = await repo.update_member_status(
        community.id, TEST_USER_ID, MembershipStatus.BANNED, role=MemberRole.BANNED
    )

    assert updated.status == MembershipStatus.BANNED
    assert updated.role == MemberRole.BANNED


@pytest.mark.integration
async def test_update_member_status_returns_none_for_non_member(db_session):
    """update_member_status() returns None when the user is not a member."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    result = await repo.update_member_status(
        community.id, uuid.uuid4(), MembershipStatus.LEFT
    )

    assert result is None


# ===========================================================================
# create_join_request
# ===========================================================================

@pytest.mark.integration
async def test_create_join_request_returns_request_with_id(db_session):
    """create_join_request() persists and returns a JoinRequest with a UUID id."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    req = await repo.create_join_request(community.id, TEST_USER_ID)

    assert req is not None
    assert req.id is not None
    assert isinstance(req.id, uuid.UUID)


@pytest.mark.integration
async def test_create_join_request_stores_community_and_requester(db_session):
    """create_join_request() persists community_id and requester_id."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    req = await repo.create_join_request(community.id, TEST_USER_ID)

    assert req.community_id == community.id
    assert req.requester_id == TEST_USER_ID


@pytest.mark.integration
async def test_create_join_request_default_status_is_pending(db_session):
    """create_join_request() defaults to status=PENDING."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    req = await repo.create_join_request(community.id, TEST_USER_ID)

    assert req.status == JoinRequestStatus.PENDING


@pytest.mark.integration
async def test_create_join_request_stores_optional_message(db_session):
    """create_join_request() persists the optional message."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    req = await repo.create_join_request(
        community.id, TEST_USER_ID, message="I love slow travel!"
    )

    assert req.message == "I love slow travel!"


@pytest.mark.integration
async def test_create_join_request_null_message_when_not_provided(db_session):
    """create_join_request() with no message stores None."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    req = await repo.create_join_request(community.id, TEST_USER_ID)

    assert req.message is None


# ===========================================================================
# get_pending_join_request
# ===========================================================================

@pytest.mark.integration
async def test_get_pending_join_request_returns_pending_request(db_session):
    """get_pending_join_request() returns the PENDING request for the user."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.create_join_request(community.id, TEST_USER_ID)
    await db_session.commit()

    found = await repo.get_pending_join_request(community.id, TEST_USER_ID)

    assert found is not None
    assert found.requester_id == TEST_USER_ID
    assert found.status == JoinRequestStatus.PENDING


@pytest.mark.integration
async def test_get_pending_join_request_returns_none_when_no_request(db_session):
    """get_pending_join_request() returns None when no PENDING request exists."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    result = await repo.get_pending_join_request(community.id, TEST_USER_ID)

    assert result is None


@pytest.mark.integration
async def test_get_pending_join_request_returns_none_after_approval(db_session):
    """get_pending_join_request() returns None after the request is approved."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    req = await repo.create_join_request(community.id, TEST_USER_ID)
    await db_session.commit()
    await repo.update_join_request_status(req.id, JoinRequestStatus.APPROVED)
    await db_session.commit()

    result = await repo.get_pending_join_request(community.id, TEST_USER_ID)

    assert result is None


# ===========================================================================
# get_join_request_by_id
# ===========================================================================

@pytest.mark.integration
async def test_get_join_request_by_id_returns_existing_request(db_session):
    """get_join_request_by_id() returns the request when it exists."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    req = await repo.create_join_request(community.id, TEST_USER_ID)
    await db_session.commit()

    found = await repo.get_join_request_by_id(req.id)

    assert found is not None
    assert found.id == req.id


@pytest.mark.integration
async def test_get_join_request_by_id_returns_none_for_missing_id(db_session):
    """get_join_request_by_id() returns None when the ID does not exist."""
    repo = _repo(db_session)

    result = await repo.get_join_request_by_id(uuid.uuid4())

    assert result is None


# ===========================================================================
# list_join_requests
# ===========================================================================

@pytest.mark.integration
async def test_list_join_requests_defaults_to_pending(db_session):
    """list_join_requests() returns PENDING requests by default."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.create_join_request(community.id, uuid.uuid4())
    await repo.create_join_request(community.id, uuid.uuid4())
    await db_session.commit()

    requests, total = await repo.list_join_requests(community.id)

    assert total == 2
    assert all(r.status == JoinRequestStatus.PENDING for r in requests)


@pytest.mark.integration
async def test_list_join_requests_filter_by_status(db_session):
    """list_join_requests() with status=APPROVED returns approved requests."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    req1 = await repo.create_join_request(community.id, uuid.uuid4())
    await repo.create_join_request(community.id, uuid.uuid4())
    await db_session.commit()
    await repo.update_join_request_status(req1.id, JoinRequestStatus.APPROVED)
    await db_session.commit()

    requests, total = await repo.list_join_requests(
        community.id, status=JoinRequestStatus.APPROVED
    )

    assert total == 1
    assert requests[0].status == JoinRequestStatus.APPROVED


@pytest.mark.integration
async def test_list_join_requests_respects_limit(db_session):
    """list_join_requests() respects the limit parameter."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    for _ in range(5):
        await repo.create_join_request(community.id, uuid.uuid4())
    await db_session.commit()

    requests, total = await repo.list_join_requests(community.id, limit=2, offset=0)

    assert len(requests) == 2
    assert total == 5


@pytest.mark.integration
async def test_list_join_requests_respects_offset(db_session):
    """list_join_requests() with offset skips earlier results."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    for _ in range(4):
        await repo.create_join_request(community.id, uuid.uuid4())
    await db_session.commit()

    all_reqs, _ = await repo.list_join_requests(community.id, limit=100, offset=0)
    paged_reqs, _ = await repo.list_join_requests(community.id, limit=100, offset=2)

    assert len(paged_reqs) == len(all_reqs) - 2


@pytest.mark.integration
async def test_list_join_requests_returns_empty_when_none(db_session):
    """list_join_requests() returns empty list and total=0 when no requests exist."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    requests, total = await repo.list_join_requests(community.id)

    assert requests == [] or list(requests) == []
    assert total == 0


# ===========================================================================
# update_join_request_status
# ===========================================================================

@pytest.mark.integration
async def test_update_join_request_status_changes_to_approved(db_session):
    """update_join_request_status() sets status=APPROVED."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    req = await repo.create_join_request(community.id, TEST_USER_ID)
    await db_session.commit()

    updated = await repo.update_join_request_status(req.id, JoinRequestStatus.APPROVED)

    assert updated is not None
    assert updated.status == JoinRequestStatus.APPROVED


@pytest.mark.integration
async def test_update_join_request_status_changes_to_rejected(db_session):
    """update_join_request_status() sets status=REJECTED."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    req = await repo.create_join_request(community.id, TEST_USER_ID)
    await db_session.commit()

    updated = await repo.update_join_request_status(req.id, JoinRequestStatus.REJECTED)

    assert updated.status == JoinRequestStatus.REJECTED


@pytest.mark.integration
async def test_update_join_request_status_changes_to_cancelled(db_session):
    """update_join_request_status() sets status=CANCELLED."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    req = await repo.create_join_request(community.id, TEST_USER_ID)
    await db_session.commit()

    updated = await repo.update_join_request_status(req.id, JoinRequestStatus.CANCELLED)

    assert updated.status == JoinRequestStatus.CANCELLED


@pytest.mark.integration
async def test_update_join_request_status_stores_reviewed_by(db_session):
    """update_join_request_status() persists the reviewed_by user ID."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    req = await repo.create_join_request(community.id, TEST_USER_ID)
    await db_session.commit()

    updated = await repo.update_join_request_status(
        req.id, JoinRequestStatus.APPROVED, reviewed_by=TEST_OTHER_USER_ID
    )

    assert updated.reviewed_by == TEST_OTHER_USER_ID


@pytest.mark.integration
async def test_update_join_request_status_returns_none_for_missing_id(db_session):
    """update_join_request_status() returns None when the request ID does not exist."""
    repo = _repo(db_session)

    result = await repo.update_join_request_status(uuid.uuid4(), JoinRequestStatus.APPROVED)

    assert result is None
