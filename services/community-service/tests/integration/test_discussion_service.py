"""
CP-16E.3 — DiscussionService Integration Tests

Validates service-layer behaviour for DiscussionService.
Tests exercise the full Service → Repository → SQLite stack.
No HTTP requests; no mocking of repository methods.

Public methods under test:
  - create_discussion
  - get_discussion
  - list_discussions
  - update_discussion
  - delete_discussion
  - create_comment
  - list_comments
  - update_comment
  - delete_comment
"""

import uuid
import pytest

from app.services.discussion_service import DiscussionService
from app.schemas.community import (
    DiscussionCreateRequest,
    DiscussionUpdateRequest,
    DiscussionCommentCreateRequest,
    DiscussionCommentUpdateRequest,
    DiscussionSchema,
    DiscussionListResponse,
    DiscussionCommentSchema,
    DiscussionCommentListResponse,
    DiscussionQueryParams,
    CommentQueryParams,
)
from shared.constants.status import CommunityVisibility, MemberRole, MembershipStatus
from shared.exceptions import NotFoundError, ForbiddenError

from tests.conftest import TEST_USER_ID, TEST_OTHER_USER_ID
from tests.utils import (
    create_test_community,
    create_test_member,
    create_test_discussion,
    create_test_comment,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc(session) -> DiscussionService:
    return DiscussionService(session)


def _disc_create(title: str = "Test Discussion", content: str = "Some content.") -> DiscussionCreateRequest:
    return DiscussionCreateRequest(title=title, content=content)


def _disc_update(**kwargs) -> DiscussionUpdateRequest:
    return DiscussionUpdateRequest(**kwargs)


def _comment_create(content: str = "A test comment.") -> DiscussionCommentCreateRequest:
    return DiscussionCommentCreateRequest(content=content)


def _comment_update(content: str) -> DiscussionCommentUpdateRequest:
    return DiscussionCommentUpdateRequest(content=content)


def _disc_params(**kwargs) -> DiscussionQueryParams:
    defaults = {"limit": 20, "offset": 0}
    defaults.update(kwargs)
    return DiscussionQueryParams(**defaults)


def _comment_params(**kwargs) -> CommentQueryParams:
    defaults = {"limit": 50, "offset": 0}
    defaults.update(kwargs)
    return CommentQueryParams(**defaults)


THIRD_USER_ID = uuid.UUID("c0000000-0000-0000-0000-000000000003")


# ---------------------------------------------------------------------------
# Shared setup helper: community + owner + optional extra member
# ---------------------------------------------------------------------------

async def _setup_community(
    session,
    visibility: CommunityVisibility = CommunityVisibility.PUBLIC,
    requires_approval: bool = False,
    add_other_user: bool = False,
    other_role: MemberRole = MemberRole.MEMBER,
):
    """Create a community with TEST_USER_ID as owner. Optionally add TEST_OTHER_USER_ID."""
    community = await create_test_community(
        session,
        creator_id=TEST_USER_ID,
        visibility=visibility,
        requires_approval=requires_approval,
        member_count=1,
    )
    await create_test_member(
        session, community_id=community.id, user_id=TEST_USER_ID, role=MemberRole.OWNER
    )
    if add_other_user:
        await create_test_member(
            session,
            community_id=community.id,
            user_id=TEST_OTHER_USER_ID,
            role=other_role,
        )
    await session.commit()
    return community


# ===========================================================================
# create_discussion
# ===========================================================================

@pytest.mark.integration
async def test_create_discussion_returns_schema(db_session):
    """create_discussion() returns a DiscussionSchema on success."""
    community = await _setup_community(db_session)
    svc = _svc(db_session)

    result = await svc.create_discussion(community.id, _disc_create(), TEST_USER_ID)

    assert isinstance(result, DiscussionSchema)


@pytest.mark.integration
async def test_create_discussion_fields_are_correct(db_session):
    """create_discussion() persists and returns the correct field values."""
    community = await _setup_community(db_session)
    svc = _svc(db_session)

    result = await svc.create_discussion(
        community.id,
        _disc_create(title="Slow Travel Routes", content="Let's discuss routes."),
        TEST_USER_ID,
    )

    assert result.title == "Slow Travel Routes"
    assert result.content == "Let's discuss routes."
    assert result.community_id == community.id
    assert result.author_id == TEST_USER_ID
    assert result.comment_count == 0
    assert result.is_deleted is False


@pytest.mark.integration
async def test_create_discussion_non_member_raises_forbidden(db_session):
    """create_discussion() raises ForbiddenError if caller is not an active member."""
    community = await _setup_community(db_session)
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.create_discussion(community.id, _disc_create(), TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_create_discussion_member_can_post(db_session):
    """A regular member (non-owner) can create a discussion."""
    community = await _setup_community(db_session, add_other_user=True)
    svc = _svc(db_session)

    result = await svc.create_discussion(
        community.id, _disc_create(title="Member Post"), TEST_OTHER_USER_ID
    )

    assert result.author_id == TEST_OTHER_USER_ID
    assert result.community_id == community.id


# ===========================================================================
# get_discussion
# ===========================================================================

@pytest.mark.integration
async def test_get_discussion_returns_schema(db_session):
    """get_discussion() returns a DiscussionSchema for a known discussion."""
    community = await _setup_community(db_session)
    discussion = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    svc = _svc(db_session)

    result = await svc.get_discussion(discussion.id, current_user_id=TEST_USER_ID)

    assert isinstance(result, DiscussionSchema)
    assert result.id == discussion.id


@pytest.mark.integration
async def test_get_discussion_not_found_raises(db_session):
    """get_discussion() raises NotFoundError for an unknown discussion ID."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.get_discussion(uuid.uuid4())


@pytest.mark.integration
async def test_get_discussion_public_community_no_auth(db_session):
    """get_discussion() on a PUBLIC community is accessible without auth."""
    community = await _setup_community(db_session, visibility=CommunityVisibility.PUBLIC)
    discussion = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    svc = _svc(db_session)

    result = await svc.get_discussion(discussion.id, current_user_id=None)

    assert result.id == discussion.id


@pytest.mark.integration
async def test_get_discussion_private_community_non_member_raises(db_session):
    """get_discussion() raises ForbiddenError for PRIVATE community non-member."""
    community = await _setup_community(db_session, visibility=CommunityVisibility.PRIVATE)
    discussion = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.get_discussion(discussion.id, current_user_id=TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_get_discussion_private_community_member_succeeds(db_session):
    """get_discussion() returns the discussion for a PRIVATE community member."""
    community = await _setup_community(
        db_session, visibility=CommunityVisibility.PRIVATE, add_other_user=True
    )
    discussion = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    svc = _svc(db_session)

    result = await svc.get_discussion(discussion.id, current_user_id=TEST_OTHER_USER_ID)

    assert result.id == discussion.id


# ===========================================================================
# list_discussions
# ===========================================================================

@pytest.mark.integration
async def test_list_discussions_returns_response(db_session):
    """list_discussions() returns a DiscussionListResponse."""
    community = await _setup_community(db_session)
    svc = _svc(db_session)

    result = await svc.list_discussions(community.id, _disc_params())

    assert isinstance(result, DiscussionListResponse)


@pytest.mark.integration
async def test_list_discussions_includes_created_discussions(db_session):
    """list_discussions() includes discussions created in the community."""
    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID, title="Listed Discussion"
    )
    svc = _svc(db_session)

    result = await svc.list_discussions(community.id, _disc_params())

    ids = [d.id for d in result.discussions]
    assert disc.id in ids


@pytest.mark.integration
async def test_list_discussions_community_not_found_raises(db_session):
    """list_discussions() raises NotFoundError for unknown community."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.list_discussions(uuid.uuid4(), _disc_params())


@pytest.mark.integration
async def test_list_discussions_private_community_non_member_raises(db_session):
    """list_discussions() raises ForbiddenError for PRIVATE community non-member."""
    community = await _setup_community(db_session, visibility=CommunityVisibility.PRIVATE)
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.list_discussions(
            community.id, _disc_params(), current_user_id=TEST_OTHER_USER_ID
        )


@pytest.mark.integration
async def test_list_discussions_pagination(db_session):
    """list_discussions() respects limit and offset parameters."""
    community = await _setup_community(db_session)
    for i in range(5):
        await create_test_discussion(
            db_session,
            community_id=community.id,
            author_id=TEST_USER_ID,
            title=f"Discussion {i}",
        )
    svc = _svc(db_session)

    result = await svc.list_discussions(community.id, _disc_params(limit=2, offset=0))

    assert len(result.discussions) <= 2
    assert result.limit == 2


@pytest.mark.integration
async def test_list_discussions_excludes_deleted(db_session):
    """list_discussions() does not include soft-deleted discussions."""
    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    svc = _svc(db_session)
    await svc.delete_discussion(disc.id, current_user_id=TEST_USER_ID)

    result = await svc.list_discussions(community.id, _disc_params())

    ids = [d.id for d in result.discussions]
    assert disc.id not in ids


# ===========================================================================
# update_discussion
# ===========================================================================

@pytest.mark.integration
async def test_update_discussion_returns_schema(db_session):
    """update_discussion() returns an updated DiscussionSchema."""
    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID, title="Original"
    )
    svc = _svc(db_session)

    result = await svc.update_discussion(disc.id, _disc_update(title="Updated"), TEST_USER_ID)

    assert isinstance(result, DiscussionSchema)
    assert result.title == "Updated"


@pytest.mark.integration
async def test_update_discussion_author_can_edit_own(db_session):
    """The discussion author can update their own discussion."""
    community = await _setup_community(db_session, add_other_user=True)
    disc = await create_test_discussion(
        db_session,
        community_id=community.id,
        author_id=TEST_OTHER_USER_ID,
        title="By Other",
    )
    svc = _svc(db_session)

    result = await svc.update_discussion(
        disc.id, _disc_update(title="Edited By Author"), TEST_OTHER_USER_ID
    )

    assert result.title == "Edited By Author"


@pytest.mark.integration
async def test_update_discussion_owner_can_edit_any(db_session):
    """Community OWNER can edit any member's discussion."""
    community = await _setup_community(db_session, add_other_user=True)
    disc = await create_test_discussion(
        db_session,
        community_id=community.id,
        author_id=TEST_OTHER_USER_ID,
        title="Member Discussion",
    )
    svc = _svc(db_session)

    result = await svc.update_discussion(
        disc.id, _disc_update(title="Owner Override"), TEST_USER_ID
    )

    assert result.title == "Owner Override"


@pytest.mark.integration
async def test_update_discussion_moderator_can_edit_any(db_session):
    """Community MODERATOR can edit any member's discussion."""
    community = await _setup_community(
        db_session, add_other_user=True, other_role=MemberRole.MODERATOR
    )
    disc = await create_test_discussion(
        db_session,
        community_id=community.id,
        author_id=TEST_USER_ID,
        title="Owner Post",
    )
    # Add a third regular member as the discussion author to test
    await create_test_member(
        db_session,
        community_id=community.id,
        user_id=THIRD_USER_ID,
        role=MemberRole.MEMBER,
    )
    disc2 = await create_test_discussion(
        db_session,
        community_id=community.id,
        author_id=THIRD_USER_ID,
        title="Regular Post",
    )
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.update_discussion(
        disc2.id, _disc_update(title="Mod Edited"), TEST_OTHER_USER_ID
    )

    assert result.title == "Mod Edited"


@pytest.mark.integration
async def test_update_discussion_non_author_member_raises_forbidden(db_session):
    """A regular member cannot update another member's discussion."""
    community = await _setup_community(db_session, add_other_user=True)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID, title="Owner Post"
    )
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.update_discussion(disc.id, _disc_update(title="Stolen"), TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_update_discussion_not_found_raises(db_session):
    """update_discussion() raises NotFoundError for unknown discussion ID."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.update_discussion(uuid.uuid4(), _disc_update(title="Ghost"), TEST_USER_ID)


# ===========================================================================
# delete_discussion
# ===========================================================================

@pytest.mark.integration
async def test_delete_discussion_returns_true(db_session):
    """delete_discussion() returns True on success."""
    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    svc = _svc(db_session)

    result = await svc.delete_discussion(disc.id, TEST_USER_ID)

    assert result is True


@pytest.mark.integration
async def test_delete_discussion_makes_it_unfindable(db_session):
    """After delete_discussion(), get_discussion() raises NotFoundError."""
    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    svc = _svc(db_session)

    await svc.delete_discussion(disc.id, TEST_USER_ID)

    with pytest.raises(NotFoundError):
        await svc.get_discussion(disc.id)


@pytest.mark.integration
async def test_delete_discussion_owner_can_delete_any(db_session):
    """Community OWNER can soft-delete any member's discussion."""
    community = await _setup_community(db_session, add_other_user=True)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_OTHER_USER_ID
    )
    svc = _svc(db_session)

    result = await svc.delete_discussion(disc.id, TEST_USER_ID)

    assert result is True


@pytest.mark.integration
async def test_delete_discussion_non_author_member_raises_forbidden(db_session):
    """A regular member cannot delete another member's discussion."""
    community = await _setup_community(db_session, add_other_user=True)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.delete_discussion(disc.id, TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_delete_discussion_not_found_raises(db_session):
    """delete_discussion() raises NotFoundError for unknown discussion ID."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.delete_discussion(uuid.uuid4(), TEST_USER_ID)


# ===========================================================================
# create_comment
# ===========================================================================

@pytest.mark.integration
async def test_create_comment_returns_schema(db_session):
    """create_comment() returns a DiscussionCommentSchema."""
    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    svc = _svc(db_session)

    result = await svc.create_comment(disc.id, _comment_create(), TEST_USER_ID)

    assert isinstance(result, DiscussionCommentSchema)


@pytest.mark.integration
async def test_create_comment_fields_are_correct(db_session):
    """create_comment() returns the correct field values."""
    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    svc = _svc(db_session)

    result = await svc.create_comment(
        disc.id, _comment_create("Great topic!"), TEST_USER_ID
    )

    assert result.content == "Great topic!"
    assert result.author_id == TEST_USER_ID
    assert result.discussion_id == disc.id
    assert result.is_deleted is False


@pytest.mark.integration
async def test_create_comment_increments_comment_count(db_session):
    """create_comment() increments the discussion comment_count by 1."""
    from app.repositories.discussion_repository import DiscussionRepository

    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID, comment_count=0
    )
    svc = _svc(db_session)

    await svc.create_comment(disc.id, _comment_create(), TEST_USER_ID)

    repo = DiscussionRepository(db_session)
    updated = await repo.get_discussion_by_id(disc.id)
    assert updated.comment_count == 1


@pytest.mark.integration
async def test_create_comment_discussion_not_found_raises(db_session):
    """create_comment() raises NotFoundError for unknown discussion ID."""
    community = await _setup_community(db_session)
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.create_comment(uuid.uuid4(), _comment_create(), TEST_USER_ID)


@pytest.mark.integration
async def test_create_comment_non_member_raises_forbidden(db_session):
    """create_comment() raises ForbiddenError if caller is not an active member."""
    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.create_comment(disc.id, _comment_create(), TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_create_multiple_comments_increments_count(db_session):
    """Multiple comments each increment the comment_count once."""
    from app.repositories.discussion_repository import DiscussionRepository

    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID, comment_count=0
    )
    svc = _svc(db_session)

    await svc.create_comment(disc.id, _comment_create("First"), TEST_USER_ID)
    await svc.create_comment(disc.id, _comment_create("Second"), TEST_USER_ID)

    repo = DiscussionRepository(db_session)
    updated = await repo.get_discussion_by_id(disc.id)
    assert updated.comment_count == 2


# ===========================================================================
# list_comments
# ===========================================================================

@pytest.mark.integration
async def test_list_comments_returns_response(db_session):
    """list_comments() returns a DiscussionCommentListResponse."""
    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    svc = _svc(db_session)

    result = await svc.list_comments(disc.id, _comment_params())

    assert isinstance(result, DiscussionCommentListResponse)


@pytest.mark.integration
async def test_list_comments_includes_created_comments(db_session):
    """list_comments() includes comments added to the discussion."""
    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    comment = await create_test_comment(
        db_session, discussion_id=disc.id, author_id=TEST_USER_ID, content="Hello!"
    )
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.list_comments(disc.id, _comment_params())

    ids = [c.id for c in result.comments]
    assert comment.id in ids


@pytest.mark.integration
async def test_list_comments_discussion_not_found_raises(db_session):
    """list_comments() raises NotFoundError for unknown discussion ID."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.list_comments(uuid.uuid4(), _comment_params())


@pytest.mark.integration
async def test_list_comments_private_community_non_member_raises(db_session):
    """list_comments() raises ForbiddenError for PRIVATE community non-member."""
    community = await _setup_community(db_session, visibility=CommunityVisibility.PRIVATE)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.list_comments(disc.id, _comment_params(), current_user_id=TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_list_comments_excludes_deleted_comments(db_session):
    """list_comments() does not return soft-deleted comments."""
    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    comment = await create_test_comment(
        db_session, discussion_id=disc.id, author_id=TEST_USER_ID
    )
    await db_session.commit()
    svc = _svc(db_session)
    await svc.delete_comment(comment.id, TEST_USER_ID)

    result = await svc.list_comments(disc.id, _comment_params())

    ids = [c.id for c in result.comments]
    assert comment.id not in ids


# ===========================================================================
# update_comment
# ===========================================================================

@pytest.mark.integration
async def test_update_comment_returns_schema(db_session):
    """update_comment() returns an updated DiscussionCommentSchema."""
    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    comment = await create_test_comment(
        db_session, discussion_id=disc.id, author_id=TEST_USER_ID, content="Original"
    )
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.update_comment(comment.id, _comment_update("Updated content"), TEST_USER_ID)

    assert isinstance(result, DiscussionCommentSchema)
    assert result.content == "Updated content"


@pytest.mark.integration
async def test_update_comment_author_can_edit_own(db_session):
    """Comment author can update their own comment."""
    community = await _setup_community(db_session, add_other_user=True)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    comment = await create_test_comment(
        db_session, discussion_id=disc.id, author_id=TEST_OTHER_USER_ID, content="My comment"
    )
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.update_comment(comment.id, _comment_update("Edited"), TEST_OTHER_USER_ID)

    assert result.content == "Edited"


@pytest.mark.integration
async def test_update_comment_owner_can_edit_any(db_session):
    """Community OWNER can update any comment."""
    community = await _setup_community(db_session, add_other_user=True)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    comment = await create_test_comment(
        db_session, discussion_id=disc.id, author_id=TEST_OTHER_USER_ID, content="Member comment"
    )
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.update_comment(comment.id, _comment_update("Owner edited"), TEST_USER_ID)

    assert result.content == "Owner edited"


@pytest.mark.integration
async def test_update_comment_non_author_member_raises_forbidden(db_session):
    """A regular member cannot update another member's comment."""
    community = await _setup_community(db_session, add_other_user=True)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    # Owner's comment; other user tries to edit
    comment = await create_test_comment(
        db_session, discussion_id=disc.id, author_id=TEST_USER_ID, content="Owner comment"
    )
    await db_session.commit()
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.update_comment(comment.id, _comment_update("Hijacked"), TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_update_comment_not_found_raises(db_session):
    """update_comment() raises NotFoundError for unknown comment ID."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.update_comment(uuid.uuid4(), _comment_update("Ghost"), TEST_USER_ID)


# ===========================================================================
# delete_comment
# ===========================================================================

@pytest.mark.integration
async def test_delete_comment_returns_true(db_session):
    """delete_comment() returns True on success."""
    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    comment = await create_test_comment(
        db_session, discussion_id=disc.id, author_id=TEST_USER_ID
    )
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.delete_comment(comment.id, TEST_USER_ID)

    assert result is True


@pytest.mark.integration
async def test_delete_comment_decrements_comment_count(db_session):
    """delete_comment() decrements the discussion comment_count by 1."""
    from app.repositories.discussion_repository import DiscussionRepository

    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID, comment_count=1
    )
    comment = await create_test_comment(
        db_session, discussion_id=disc.id, author_id=TEST_USER_ID
    )
    await db_session.commit()
    svc = _svc(db_session)

    await svc.delete_comment(comment.id, TEST_USER_ID)

    repo = DiscussionRepository(db_session)
    updated = await repo.get_discussion_by_id(disc.id)
    assert updated.comment_count == 0


@pytest.mark.integration
async def test_delete_comment_author_can_delete_own(db_session):
    """Comment author can soft-delete their own comment."""
    community = await _setup_community(db_session, add_other_user=True)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    comment = await create_test_comment(
        db_session, discussion_id=disc.id, author_id=TEST_OTHER_USER_ID
    )
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.delete_comment(comment.id, TEST_OTHER_USER_ID)

    assert result is True


@pytest.mark.integration
async def test_delete_comment_owner_can_delete_any(db_session):
    """Community OWNER can soft-delete any comment."""
    community = await _setup_community(db_session, add_other_user=True)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    comment = await create_test_comment(
        db_session, discussion_id=disc.id, author_id=TEST_OTHER_USER_ID
    )
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.delete_comment(comment.id, TEST_USER_ID)

    assert result is True


@pytest.mark.integration
async def test_delete_comment_non_author_member_raises_forbidden(db_session):
    """A regular member cannot delete another member's comment."""
    community = await _setup_community(db_session, add_other_user=True)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    # Owner writes the comment; other user (MEMBER) tries to delete it
    comment = await create_test_comment(
        db_session, discussion_id=disc.id, author_id=TEST_USER_ID
    )
    await db_session.commit()
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.delete_comment(comment.id, TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_delete_comment_not_found_raises(db_session):
    """delete_comment() raises NotFoundError for unknown comment ID."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.delete_comment(uuid.uuid4(), TEST_USER_ID)


@pytest.mark.integration
async def test_delete_comment_marks_as_deleted(db_session):
    """Soft-deleted comment is marked is_deleted=True and excluded from normal queries."""
    from app.repositories.discussion_repository import DiscussionRepository

    community = await _setup_community(db_session)
    disc = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    comment = await create_test_comment(
        db_session, discussion_id=disc.id, author_id=TEST_USER_ID
    )
    await db_session.commit()
    svc = _svc(db_session)

    await svc.delete_comment(comment.id, TEST_USER_ID)

    repo = DiscussionRepository(db_session)
    # With include_deleted=False (default) it should not be found
    deleted = await repo.get_comment_by_id(comment.id, include_deleted=False)
    assert deleted is None

    # With include_deleted=True it should still exist
    deleted_record = await repo.get_comment_by_id(comment.id, include_deleted=True)
    assert deleted_record is not None
    assert deleted_record.is_deleted is True
