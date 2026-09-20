"""
CP-16E.3 — MembershipService Integration Tests

Validates service-layer behaviour for MembershipService.
Tests exercise the full Service → Repository → SQLite stack.
No HTTP requests; no mocking of repository methods.

Public methods under test:
  - join_community
  - leave_community
  - list_members
  - remove_member
  - ban_member
  - update_member_role
  - list_join_requests
  - action_join_request
"""

import uuid
import pytest

from app.services.membership_service import MembershipService
from app.schemas.community import (
    JoinCommunityRequest,
    JoinRequestActionRequest,
    MemberRoleUpdateRequest,
    MemberListResponse,
    JoinRequestListResponse,
    MemberSchema,
    JoinRequestSchema,
)
from shared.constants.status import (
    CommunityVisibility,
    JoinRequestStatus,
    MemberRole,
    MembershipStatus,
)
from shared.exceptions import NotFoundError, ForbiddenError, ConflictError, ValidationError

from tests.conftest import TEST_USER_ID, TEST_OTHER_USER_ID
from tests.utils import create_test_community, create_test_member


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc(session) -> MembershipService:
    return MembershipService(session)


def _join_request(message: str = None) -> JoinCommunityRequest:
    return JoinCommunityRequest(message=message)


def _action_request(action: str) -> JoinRequestActionRequest:
    return JoinRequestActionRequest(action=action)


def _role_update(role: MemberRole) -> MemberRoleUpdateRequest:
    return MemberRoleUpdateRequest(role=role)


# A third user ID for multi-user tests
THIRD_USER_ID = uuid.UUID("c0000000-0000-0000-0000-000000000003")


# ===========================================================================
# join_community — public, no approval required
# ===========================================================================

@pytest.mark.integration
async def test_join_public_community_returns_joined(db_session):
    """join_community() on a PUBLIC non-approval community returns {'joined': True}."""
    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PUBLIC,
        requires_approval=False,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    result = await svc.join_community(community.id, _join_request(), TEST_OTHER_USER_ID)

    assert result == {"joined": True}


@pytest.mark.integration
async def test_join_public_community_increments_member_count(db_session):
    """join_community() increments the community member_count by 1."""
    from app.repositories.community_repository import CommunityRepository

    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PUBLIC,
        requires_approval=False,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    await svc.join_community(community.id, _join_request(), TEST_OTHER_USER_ID)

    repo = CommunityRepository(db_session)
    updated = await repo.get_by_id(community.id)
    assert updated.member_count == 2


@pytest.mark.integration
async def test_join_community_not_found_raises(db_session):
    """join_community() raises NotFoundError for an unknown community."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.join_community(uuid.uuid4(), _join_request(), TEST_USER_ID)


@pytest.mark.integration
async def test_join_community_duplicate_raises_conflict(db_session):
    """join_community() raises ConflictError if user is already an active member."""
    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PUBLIC,
        requires_approval=False,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(ConflictError):
        await svc.join_community(community.id, _join_request(), TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_join_community_banned_user_raises_forbidden(db_session):
    """join_community() raises ForbiddenError if user is banned."""
    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PUBLIC,
        requires_approval=False,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.BANNED,
        status=MembershipStatus.BANNED,
    )
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(ForbiddenError):
        await svc.join_community(community.id, _join_request(), TEST_OTHER_USER_ID)


# ===========================================================================
# join_community — private / requires_approval
# ===========================================================================

@pytest.mark.integration
async def test_join_private_community_returns_requested(db_session):
    """join_community() on a PRIVATE community returns {'requested': True, 'request_id': ...}."""
    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PRIVATE,
        requires_approval=False,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    result = await svc.join_community(community.id, _join_request(), TEST_OTHER_USER_ID)

    assert result.get("requested") is True
    assert "request_id" in result
    assert isinstance(result["request_id"], uuid.UUID)


@pytest.mark.integration
async def test_join_requires_approval_community_returns_requested(db_session):
    """join_community() on a PUBLIC+requires_approval community creates a join request."""
    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PUBLIC,
        requires_approval=True,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    result = await svc.join_community(community.id, _join_request("Please let me in"), TEST_OTHER_USER_ID)

    assert result.get("requested") is True


@pytest.mark.integration
async def test_join_private_duplicate_request_raises_conflict(db_session):
    """join_community() raises ConflictError if user already has a pending join request."""
    from app.models.membership import JoinRequest
    from shared.constants.status import JoinRequestStatus

    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PRIVATE,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    # Create an existing pending request
    pending = JoinRequest(
        community_id=community.id,
        requester_id=TEST_OTHER_USER_ID,
        status=JoinRequestStatus.PENDING,
    )
    db_session.add(pending)
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(ConflictError):
        await svc.join_community(community.id, _join_request(), TEST_OTHER_USER_ID)


# ===========================================================================
# leave_community
# ===========================================================================

@pytest.mark.integration
async def test_leave_community_returns_true(db_session):
    """leave_community() returns True for a valid active member."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    result = await svc.leave_community(community.id, TEST_OTHER_USER_ID)

    assert result is True


@pytest.mark.integration
async def test_leave_community_decrements_member_count(db_session):
    """leave_community() decrements the community member_count by 1."""
    from app.repositories.community_repository import CommunityRepository

    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    await svc.leave_community(community.id, TEST_OTHER_USER_ID)

    repo = CommunityRepository(db_session)
    updated = await repo.get_by_id(community.id)
    assert updated.member_count == 1


@pytest.mark.integration
async def test_leave_community_not_found_raises(db_session):
    """leave_community() raises NotFoundError for unknown community."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.leave_community(uuid.uuid4(), TEST_USER_ID)


@pytest.mark.integration
async def test_leave_community_non_member_raises(db_session):
    """leave_community() raises NotFoundError if user is not a member."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=1
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(NotFoundError):
        await svc.leave_community(community.id, TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_leave_community_owner_raises_validation_error(db_session):
    """leave_community() raises ValidationError if owner tries to leave."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=1
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(ValidationError):
        await svc.leave_community(community.id, TEST_USER_ID)


@pytest.mark.integration
async def test_leave_community_sets_status_left(db_session):
    """leave_community() persists MembershipStatus.LEFT for the leaving user."""
    from app.repositories.membership_repository import MembershipRepository

    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    await svc.leave_community(community.id, TEST_OTHER_USER_ID)

    repo = MembershipRepository(db_session)
    member = await repo.get_member(community.id, TEST_OTHER_USER_ID)
    assert member.status == MembershipStatus.LEFT


# ===========================================================================
# list_members
# ===========================================================================

@pytest.mark.integration
async def test_list_members_returns_response(db_session):
    """list_members() returns a MemberListResponse."""
    from app.schemas.community import MemberQueryParams

    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=1
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    result = await svc.list_members(
        community.id, MemberQueryParams(limit=50, offset=0), current_user_id=TEST_USER_ID
    )

    assert isinstance(result, MemberListResponse)
    assert result.total >= 1


@pytest.mark.integration
async def test_list_members_includes_active_members(db_session):
    """list_members() includes active members and their roles."""
    from app.schemas.community import MemberQueryParams

    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    result = await svc.list_members(
        community.id, MemberQueryParams(limit=50, offset=0), current_user_id=TEST_USER_ID
    )

    user_ids = [m.user_id for m in result.members]
    assert TEST_USER_ID in user_ids
    assert TEST_OTHER_USER_ID in user_ids


@pytest.mark.integration
async def test_list_members_community_not_found_raises(db_session):
    """list_members() raises NotFoundError for unknown community."""
    from app.schemas.community import MemberQueryParams

    svc = _svc(db_session)
    with pytest.raises(NotFoundError):
        await svc.list_members(
            uuid.uuid4(), MemberQueryParams(limit=50, offset=0), current_user_id=TEST_USER_ID
        )


@pytest.mark.integration
async def test_list_members_private_community_non_member_raises(db_session):
    """list_members() raises ForbiddenError for PRIVATE community if caller is not a member."""
    from app.schemas.community import MemberQueryParams

    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PRIVATE,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(ForbiddenError):
        await svc.list_members(
            community.id,
            MemberQueryParams(limit=50, offset=0),
            current_user_id=TEST_OTHER_USER_ID,
        )


@pytest.mark.integration
async def test_list_members_role_filter(db_session):
    """list_members() filters by role when params.role is provided."""
    from app.schemas.community import MemberQueryParams

    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MODERATOR,
    )
    await db_session.commit()

    svc = _svc(db_session)
    result = await svc.list_members(
        community.id,
        MemberQueryParams(limit=50, offset=0, role=MemberRole.MODERATOR),
        current_user_id=TEST_USER_ID,
    )

    assert all(m.role == MemberRole.MODERATOR for m in result.members)


# ===========================================================================
# remove_member
# ===========================================================================

@pytest.mark.integration
async def test_remove_member_returns_true(db_session):
    """remove_member() returns True when owner removes a regular member."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    result = await svc.remove_member(community.id, TEST_OTHER_USER_ID, TEST_USER_ID)

    assert result is True


@pytest.mark.integration
async def test_remove_member_decrements_member_count(db_session):
    """remove_member() decrements the community member_count."""
    from app.repositories.community_repository import CommunityRepository

    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    await svc.remove_member(community.id, TEST_OTHER_USER_ID, TEST_USER_ID)

    repo = CommunityRepository(db_session)
    updated = await repo.get_by_id(community.id)
    assert updated.member_count == 1


@pytest.mark.integration
async def test_remove_member_sets_status_removed(db_session):
    """remove_member() persists MembershipStatus.REMOVED."""
    from app.repositories.membership_repository import MembershipRepository

    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    await svc.remove_member(community.id, TEST_OTHER_USER_ID, TEST_USER_ID)

    repo = MembershipRepository(db_session)
    member = await repo.get_member(community.id, TEST_OTHER_USER_ID)
    assert member.status == MembershipStatus.REMOVED


@pytest.mark.integration
async def test_remove_member_non_member_caller_raises_forbidden(db_session):
    """remove_member() raises ForbiddenError if caller is not a mod/owner."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    third = await create_test_member(
        db_session,
        community_id=community.id,
        user_id=THIRD_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    # A plain MEMBER cannot remove another MEMBER
    with pytest.raises(ForbiddenError):
        await svc.remove_member(community.id, TEST_OTHER_USER_ID, THIRD_USER_ID)


@pytest.mark.integration
async def test_remove_member_target_not_found_raises(db_session):
    """remove_member() raises NotFoundError if target is not an active member."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=1
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(NotFoundError):
        await svc.remove_member(community.id, TEST_OTHER_USER_ID, TEST_USER_ID)


@pytest.mark.integration
async def test_remove_member_moderator_cannot_remove_owner(db_session):
    """remove_member() raises ForbiddenError if MOD tries to remove OWNER."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MODERATOR,
    )
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(ForbiddenError):
        await svc.remove_member(community.id, TEST_USER_ID, TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_remove_member_moderator_cannot_remove_moderator(db_session):
    """remove_member() raises ForbiddenError if MOD tries to remove another MOD."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=3
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MODERATOR,
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=THIRD_USER_ID,
        role=MemberRole.MODERATOR,
    )
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(ForbiddenError):
        await svc.remove_member(community.id, THIRD_USER_ID, TEST_OTHER_USER_ID)


# ===========================================================================
# ban_member
# ===========================================================================

@pytest.mark.integration
async def test_ban_member_returns_true(db_session):
    """ban_member() returns True when owner bans a regular member."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    result = await svc.ban_member(community.id, TEST_OTHER_USER_ID, TEST_USER_ID)

    assert result is True


@pytest.mark.integration
async def test_ban_member_sets_status_banned(db_session):
    """ban_member() persists MembershipStatus.BANNED and MemberRole.BANNED."""
    from app.repositories.membership_repository import MembershipRepository

    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    await svc.ban_member(community.id, TEST_OTHER_USER_ID, TEST_USER_ID)

    repo = MembershipRepository(db_session)
    member = await repo.get_member(community.id, TEST_OTHER_USER_ID)
    assert member.status == MembershipStatus.BANNED
    assert member.role == MemberRole.BANNED


@pytest.mark.integration
async def test_ban_member_decrements_member_count(db_session):
    """ban_member() decrements the community member_count."""
    from app.repositories.community_repository import CommunityRepository

    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    await svc.ban_member(community.id, TEST_OTHER_USER_ID, TEST_USER_ID)

    repo = CommunityRepository(db_session)
    updated = await repo.get_by_id(community.id)
    assert updated.member_count == 1


@pytest.mark.integration
async def test_ban_member_target_not_found_raises(db_session):
    """ban_member() raises NotFoundError if target is not an active member."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=1
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(NotFoundError):
        await svc.ban_member(community.id, TEST_OTHER_USER_ID, TEST_USER_ID)


@pytest.mark.integration
async def test_ban_member_non_mod_caller_raises_forbidden(db_session):
    """ban_member() raises ForbiddenError if caller is a plain MEMBER."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=3
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=THIRD_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(ForbiddenError):
        await svc.ban_member(community.id, TEST_OTHER_USER_ID, THIRD_USER_ID)


@pytest.mark.integration
async def test_ban_member_prevents_rejoining(db_session):
    """A banned user cannot rejoin the community — join_community raises ForbiddenError."""
    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PUBLIC,
        requires_approval=False,
        member_count=2,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    await svc.ban_member(community.id, TEST_OTHER_USER_ID, TEST_USER_ID)

    with pytest.raises(ForbiddenError):
        await svc.join_community(community.id, _join_request(), TEST_OTHER_USER_ID)


# ===========================================================================
# update_member_role
# ===========================================================================

@pytest.mark.integration
async def test_update_member_role_returns_schema(db_session):
    """update_member_role() returns a MemberSchema with the new role."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    result = await svc.update_member_role(
        community.id, TEST_OTHER_USER_ID, _role_update(MemberRole.MODERATOR), TEST_USER_ID
    )

    assert isinstance(result, MemberSchema)
    assert result.role == MemberRole.MODERATOR


@pytest.mark.integration
async def test_update_member_role_persists_change(db_session):
    """update_member_role() persists the new role to the database."""
    from app.repositories.membership_repository import MembershipRepository

    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=2
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    await svc.update_member_role(
        community.id, TEST_OTHER_USER_ID, _role_update(MemberRole.MODERATOR), TEST_USER_ID
    )

    repo = MembershipRepository(db_session)
    member = await repo.get_active_member(community.id, TEST_OTHER_USER_ID)
    assert member.role == MemberRole.MODERATOR


@pytest.mark.integration
async def test_update_member_role_non_owner_raises_forbidden(db_session):
    """update_member_role() raises ForbiddenError if caller is not the OWNER."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=3
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MODERATOR,
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=THIRD_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    # Moderator cannot promote/demote
    with pytest.raises(ForbiddenError):
        await svc.update_member_role(
            community.id, THIRD_USER_ID, _role_update(MemberRole.MODERATOR), TEST_OTHER_USER_ID
        )


@pytest.mark.integration
async def test_update_member_role_target_not_found_raises(db_session):
    """update_member_role() raises NotFoundError if target is not an active member."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=1
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(NotFoundError):
        await svc.update_member_role(
            community.id, TEST_OTHER_USER_ID, _role_update(MemberRole.MODERATOR), TEST_USER_ID
        )


# ===========================================================================
# list_join_requests
# ===========================================================================

@pytest.mark.integration
async def test_list_join_requests_returns_response(db_session):
    """list_join_requests() returns a JoinRequestListResponse."""
    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PRIVATE,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    result = await svc.list_join_requests(community.id, TEST_USER_ID)

    assert isinstance(result, JoinRequestListResponse)
    assert result.total == 0


@pytest.mark.integration
async def test_list_join_requests_shows_pending_requests(db_session):
    """list_join_requests() returns pending join requests for the community."""
    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PRIVATE,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    # Create a join request via the service
    await svc.join_community(community.id, _join_request("Let me in"), TEST_OTHER_USER_ID)

    result = await svc.list_join_requests(community.id, TEST_USER_ID)

    assert result.total == 1
    assert result.requests[0].requester_id == TEST_OTHER_USER_ID
    assert result.requests[0].status == JoinRequestStatus.PENDING


@pytest.mark.integration
async def test_list_join_requests_non_mod_raises_forbidden(db_session):
    """list_join_requests() raises ForbiddenError for a plain MEMBER caller."""
    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PRIVATE,
        member_count=2,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(ForbiddenError):
        await svc.list_join_requests(community.id, TEST_OTHER_USER_ID)


# ===========================================================================
# action_join_request
# ===========================================================================

@pytest.mark.integration
async def test_action_join_request_approve_returns_schema(db_session):
    """action_join_request(approve) returns a JoinRequestSchema with APPROVED status."""
    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PRIVATE,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    join_result = await svc.join_community(community.id, _join_request(), TEST_OTHER_USER_ID)
    request_id = join_result["request_id"]

    result = await svc.action_join_request(request_id, _action_request("approve"), TEST_USER_ID)

    assert isinstance(result, JoinRequestSchema)
    assert result.status == JoinRequestStatus.APPROVED


@pytest.mark.integration
async def test_action_join_request_approve_creates_membership(db_session):
    """Approving a join request creates an ACTIVE membership for the requester."""
    from app.repositories.membership_repository import MembershipRepository

    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PRIVATE,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    join_result = await svc.join_community(community.id, _join_request(), TEST_OTHER_USER_ID)
    await svc.action_join_request(
        join_result["request_id"], _action_request("approve"), TEST_USER_ID
    )

    repo = MembershipRepository(db_session)
    member = await repo.get_active_member(community.id, TEST_OTHER_USER_ID)
    assert member is not None
    assert member.status == MembershipStatus.ACTIVE


@pytest.mark.integration
async def test_action_join_request_approve_increments_member_count(db_session):
    """Approving a join request increments the community member_count."""
    from app.repositories.community_repository import CommunityRepository

    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PRIVATE,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    join_result = await svc.join_community(community.id, _join_request(), TEST_OTHER_USER_ID)
    await svc.action_join_request(
        join_result["request_id"], _action_request("approve"), TEST_USER_ID
    )

    repo = CommunityRepository(db_session)
    updated = await repo.get_by_id(community.id)
    assert updated.member_count == 2


@pytest.mark.integration
async def test_action_join_request_reject_returns_schema(db_session):
    """action_join_request(reject) returns a JoinRequestSchema with REJECTED status."""
    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PRIVATE,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    join_result = await svc.join_community(community.id, _join_request(), TEST_OTHER_USER_ID)

    result = await svc.action_join_request(
        join_result["request_id"], _action_request("reject"), TEST_USER_ID
    )

    assert result.status == JoinRequestStatus.REJECTED


@pytest.mark.integration
async def test_action_join_request_reject_does_not_create_membership(db_session):
    """Rejecting a join request does NOT create an active membership."""
    from app.repositories.membership_repository import MembershipRepository

    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PRIVATE,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    join_result = await svc.join_community(community.id, _join_request(), TEST_OTHER_USER_ID)
    await svc.action_join_request(
        join_result["request_id"], _action_request("reject"), TEST_USER_ID
    )

    repo = MembershipRepository(db_session)
    member = await repo.get_active_member(community.id, TEST_OTHER_USER_ID)
    assert member is None


@pytest.mark.integration
async def test_action_join_request_not_found_raises(db_session):
    """action_join_request() raises NotFoundError for an unknown request ID."""
    community = await create_test_community(
        db_session, creator_id=TEST_USER_ID, member_count=1
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    with pytest.raises(NotFoundError):
        await svc.action_join_request(uuid.uuid4(), _action_request("approve"), TEST_USER_ID)


@pytest.mark.integration
async def test_action_join_request_already_actioned_raises_validation(db_session):
    """action_join_request() raises ValidationError if the request is not PENDING."""
    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PRIVATE,
        member_count=1,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await db_session.commit()

    svc = _svc(db_session)
    join_result = await svc.join_community(community.id, _join_request(), TEST_OTHER_USER_ID)
    request_id = join_result["request_id"]

    # First action: approve
    await svc.action_join_request(request_id, _action_request("approve"), TEST_USER_ID)

    # Second action on same (now APPROVED) request
    with pytest.raises(ValidationError):
        await svc.action_join_request(request_id, _action_request("reject"), TEST_USER_ID)


@pytest.mark.integration
async def test_action_join_request_non_mod_raises_forbidden(db_session):
    """action_join_request() raises ForbiddenError if caller is a plain MEMBER."""
    community = await create_test_community(
        db_session,
        creator_id=TEST_USER_ID,
        visibility=CommunityVisibility.PRIVATE,
        member_count=2,
    )
    await create_test_member(
        db_session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )
    await db_session.commit()

    svc = _svc(db_session)
    join_result = await svc.join_community(community.id, _join_request(), THIRD_USER_ID)
    request_id = join_result["request_id"]

    with pytest.raises(ForbiddenError):
        await svc.action_join_request(request_id, _action_request("approve"), TEST_OTHER_USER_ID)
