"""
CP-16E.2 — DiscussionRepository Integration Tests

Validates repository-level behaviour for DiscussionRepository.
All tests use an in-memory SQLite database via the db_session fixture.

DiscussionRepository uses session.flush() (no commit) for writes.
Tests need await db_session.commit() before re-querying when the
session identity-map may hold stale data.
"""

import uuid
import pytest

from app.repositories.discussion_repository import DiscussionRepository
from tests.conftest import TEST_USER_ID, TEST_OTHER_USER_ID
from tests.utils import (
    create_test_community,
    create_test_discussion,
    create_test_comment,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo(session) -> DiscussionRepository:
    return DiscussionRepository(session)


# ===========================================================================
# create_discussion
# ===========================================================================

@pytest.mark.integration
async def test_create_discussion_returns_discussion_with_id(db_session):
    """create_discussion() persists a discussion and returns an ORM instance with a UUID id."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    discussion = await repo.create_discussion(
        community_id=community.id,
        author_id=TEST_USER_ID,
        title="My First Discussion",
    )

    assert discussion is not None
    assert discussion.id is not None
    assert isinstance(discussion.id, uuid.UUID)


@pytest.mark.integration
async def test_create_discussion_stores_community_and_author(db_session):
    """create_discussion() persists community_id and author_id."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    discussion = await repo.create_discussion(
        community_id=community.id,
        author_id=TEST_USER_ID,
        title="Fields Test",
    )

    assert discussion.community_id == community.id
    assert discussion.author_id == TEST_USER_ID


@pytest.mark.integration
async def test_create_discussion_strips_title_whitespace(db_session):
    """create_discussion() strips whitespace from the title."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    discussion = await repo.create_discussion(
        community_id=community.id,
        author_id=TEST_USER_ID,
        title="  Padded Title  ",
    )

    assert discussion.title == "Padded Title"


@pytest.mark.integration
async def test_create_discussion_stores_optional_content(db_session):
    """create_discussion() persists the optional content field."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    discussion = await repo.create_discussion(
        community_id=community.id,
        author_id=TEST_USER_ID,
        title="With Content",
        content="Some discussion body text.",
    )

    assert discussion.content == "Some discussion body text."


@pytest.mark.integration
async def test_create_discussion_default_comment_count_is_zero(db_session):
    """create_discussion() initialises comment_count=0."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    discussion = await repo.create_discussion(
        community_id=community.id,
        author_id=TEST_USER_ID,
        title="Zero Comments",
    )

    assert discussion.comment_count == 0


@pytest.mark.integration
async def test_create_discussion_is_not_deleted(db_session):
    """Newly created discussion has is_deleted=False."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    discussion = await repo.create_discussion(
        community_id=community.id,
        author_id=TEST_USER_ID,
        title="Not Deleted",
    )

    assert discussion.is_deleted is False


# ===========================================================================
# get_discussion_by_id
# ===========================================================================

@pytest.mark.integration
async def test_get_discussion_by_id_returns_existing_discussion(db_session):
    """get_discussion_by_id() returns the discussion when it exists."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()

    repo = _repo(db_session)
    found = await repo.get_discussion_by_id(discussion.id)

    assert found is not None
    assert found.id == discussion.id


@pytest.mark.integration
async def test_get_discussion_by_id_returns_none_for_missing_id(db_session):
    """get_discussion_by_id() returns None when the ID does not exist."""
    repo = _repo(db_session)

    result = await repo.get_discussion_by_id(uuid.uuid4())

    assert result is None


@pytest.mark.integration
async def test_get_discussion_by_id_excludes_soft_deleted_by_default(db_session):
    """get_discussion_by_id() returns None for a soft-deleted discussion."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_discussion(discussion.id)

    result = await repo.get_discussion_by_id(discussion.id)

    assert result is None


@pytest.mark.integration
async def test_get_discussion_by_id_includes_deleted_when_flag_set(db_session):
    """get_discussion_by_id(include_deleted=True) returns soft-deleted discussions."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_discussion(discussion.id)

    result = await repo.get_discussion_by_id(discussion.id, include_deleted=True)

    assert result is not None
    assert result.is_deleted is True


# ===========================================================================
# list_discussions
# ===========================================================================

@pytest.mark.integration
async def test_list_discussions_returns_non_deleted_discussions(db_session):
    """list_discussions() returns non-deleted discussions for a community."""
    community = await create_test_community(db_session)
    await db_session.commit()
    await create_test_discussion(db_session, community_id=community.id, title="Post A")
    await create_test_discussion(db_session, community_id=community.id, title="Post B")
    await db_session.commit()

    repo = _repo(db_session)
    discussions, total = await repo.list_discussions(community.id)

    assert total == 2
    assert len(discussions) == 2


@pytest.mark.integration
async def test_list_discussions_excludes_soft_deleted(db_session):
    """list_discussions() does not include soft-deleted discussions."""
    community = await create_test_community(db_session)
    await db_session.commit()
    visible = await create_test_discussion(db_session, community_id=community.id, title="Visible")
    gone = await create_test_discussion(db_session, community_id=community.id, title="Gone")
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_discussion(gone.id)

    discussions, total = await repo.list_discussions(community.id)

    ids = {d.id for d in discussions}
    assert visible.id in ids
    assert gone.id not in ids
    assert total == 1


@pytest.mark.integration
async def test_list_discussions_filters_by_community(db_session):
    """list_discussions() returns only discussions for the specified community."""
    community_a = await create_test_community(db_session, name="Comm A")
    community_b = await create_test_community(db_session, name="Comm B")
    await db_session.commit()
    await create_test_discussion(db_session, community_id=community_a.id, title="In A")
    await create_test_discussion(db_session, community_id=community_b.id, title="In B")
    await db_session.commit()

    repo = _repo(db_session)
    discussions, total = await repo.list_discussions(community_a.id)

    assert total == 1
    assert discussions[0].community_id == community_a.id


@pytest.mark.integration
async def test_list_discussions_ordered_newest_first(db_session):
    """list_discussions() returns discussions in descending created_at order."""
    community = await create_test_community(db_session)
    await db_session.commit()
    d1 = await create_test_discussion(db_session, community_id=community.id, title="Earlier")
    await db_session.commit()
    d2 = await create_test_discussion(db_session, community_id=community.id, title="Later")
    await db_session.commit()

    repo = _repo(db_session)
    discussions, _ = await repo.list_discussions(community.id, limit=10)

    ids = [d.id for d in discussions]
    assert ids.index(d2.id) < ids.index(d1.id)


@pytest.mark.integration
async def test_list_discussions_respects_limit(db_session):
    """list_discussions() respects the limit parameter."""
    community = await create_test_community(db_session)
    await db_session.commit()
    for i in range(5):
        await create_test_discussion(db_session, community_id=community.id, title=f"D{i}")
    await db_session.commit()

    repo = _repo(db_session)
    discussions, total = await repo.list_discussions(community.id, limit=2, offset=0)

    assert len(discussions) == 2
    assert total == 5


@pytest.mark.integration
async def test_list_discussions_respects_offset(db_session):
    """list_discussions() with offset skips earlier results."""
    community = await create_test_community(db_session)
    await db_session.commit()
    for i in range(4):
        await create_test_discussion(db_session, community_id=community.id, title=f"D{i}")
    await db_session.commit()

    repo = _repo(db_session)
    all_d, _ = await repo.list_discussions(community.id, limit=100, offset=0)
    paged_d, _ = await repo.list_discussions(community.id, limit=100, offset=2)

    assert len(paged_d) == len(all_d) - 2


@pytest.mark.integration
async def test_list_discussions_returns_empty_for_community_with_none(db_session):
    """list_discussions() returns empty list and total=0 when no discussions exist."""
    community = await create_test_community(db_session)
    await db_session.commit()

    repo = _repo(db_session)
    discussions, total = await repo.list_discussions(community.id)

    assert discussions == [] or list(discussions) == []
    assert total == 0


# ===========================================================================
# update_discussion
# ===========================================================================

@pytest.mark.integration
async def test_update_discussion_changes_title(db_session):
    """update_discussion() persists a new title."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id, title="Old Title")
    await db_session.commit()
    repo = _repo(db_session)

    updated = await repo.update_discussion(discussion.id, title="New Title")

    assert updated is not None
    assert updated.title == "New Title"


@pytest.mark.integration
async def test_update_discussion_strips_title_whitespace(db_session):
    """update_discussion() strips whitespace from the new title."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    repo = _repo(db_session)

    updated = await repo.update_discussion(discussion.id, title="  Padded  ")

    assert updated.title == "Padded"


@pytest.mark.integration
async def test_update_discussion_changes_content(db_session):
    """update_discussion() persists new content."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(
        db_session, community_id=community.id, content="Old content"
    )
    await db_session.commit()
    repo = _repo(db_session)

    updated = await repo.update_discussion(discussion.id, content="New content")

    assert updated.content == "New content"


@pytest.mark.integration
async def test_update_discussion_returns_none_for_missing_id(db_session):
    """update_discussion() returns None when the discussion ID does not exist."""
    repo = _repo(db_session)

    result = await repo.update_discussion(uuid.uuid4(), title="Ghost")

    assert result is None


@pytest.mark.integration
async def test_update_discussion_returns_none_for_deleted_discussion(db_session):
    """update_discussion() returns None for a soft-deleted discussion."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_discussion(discussion.id)

    result = await repo.update_discussion(discussion.id, title="After Delete")

    assert result is None


# ===========================================================================
# soft_delete_discussion
# ===========================================================================

@pytest.mark.integration
async def test_soft_delete_discussion_returns_true_on_success(db_session):
    """soft_delete_discussion() returns True when the discussion was deleted."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    repo = _repo(db_session)

    result = await repo.soft_delete_discussion(discussion.id)

    assert result is True


@pytest.mark.integration
async def test_soft_delete_discussion_sets_is_deleted_flag(db_session):
    """soft_delete_discussion() sets is_deleted=True."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_discussion(discussion.id)

    deleted = await repo.get_discussion_by_id(discussion.id, include_deleted=True)

    assert deleted.is_deleted is True


@pytest.mark.integration
async def test_soft_delete_discussion_sets_deleted_at(db_session):
    """soft_delete_discussion() sets deleted_at timestamp."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_discussion(discussion.id)

    deleted = await repo.get_discussion_by_id(discussion.id, include_deleted=True)

    assert deleted.deleted_at is not None


@pytest.mark.integration
async def test_soft_delete_discussion_returns_false_for_missing_id(db_session):
    """soft_delete_discussion() returns False when the ID does not exist."""
    repo = _repo(db_session)

    result = await repo.soft_delete_discussion(uuid.uuid4())

    assert result is False


@pytest.mark.integration
async def test_soft_delete_discussion_is_idempotent(db_session):
    """Calling soft_delete_discussion() twice returns False the second time."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_discussion(discussion.id)

    result = await repo.soft_delete_discussion(discussion.id)

    assert result is False


# ===========================================================================
# increment_comment_count / decrement_comment_count
# ===========================================================================

@pytest.mark.integration
async def test_increment_comment_count_adds_one(db_session):
    """increment_comment_count() increments comment_count by 1."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(
        db_session, community_id=community.id, comment_count=3
    )
    await db_session.commit()
    repo = _repo(db_session)

    await repo.increment_comment_count(discussion.id)
    await db_session.commit()

    found = await repo.get_discussion_by_id(discussion.id)
    assert found.comment_count == 4


@pytest.mark.integration
async def test_decrement_comment_count_subtracts_one(db_session):
    """decrement_comment_count() decrements comment_count by 1."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(
        db_session, community_id=community.id, comment_count=3
    )
    await db_session.commit()
    repo = _repo(db_session)

    await repo.decrement_comment_count(discussion.id)
    await db_session.commit()

    found = await repo.get_discussion_by_id(discussion.id)
    assert found.comment_count == 2


@pytest.mark.integration
async def test_decrement_comment_count_floors_at_zero(db_session):
    """decrement_comment_count() does not go below 0 (floor at 0)."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(
        db_session, community_id=community.id, comment_count=0
    )
    await db_session.commit()
    repo = _repo(db_session)

    await repo.decrement_comment_count(discussion.id)
    await db_session.commit()

    found = await repo.get_discussion_by_id(discussion.id)
    assert found.comment_count == 0


# ===========================================================================
# create_comment
# ===========================================================================

@pytest.mark.integration
async def test_create_comment_returns_comment_with_id(db_session):
    """create_comment() persists a comment and returns an ORM instance with a UUID id."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    repo = _repo(db_session)

    comment = await repo.create_comment(
        discussion_id=discussion.id,
        author_id=TEST_USER_ID,
        content="Great discussion!",
    )

    assert comment is not None
    assert comment.id is not None
    assert isinstance(comment.id, uuid.UUID)


@pytest.mark.integration
async def test_create_comment_stores_discussion_and_author(db_session):
    """create_comment() persists discussion_id and author_id."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    repo = _repo(db_session)

    comment = await repo.create_comment(
        discussion_id=discussion.id,
        author_id=TEST_USER_ID,
        content="Test comment",
    )

    assert comment.discussion_id == discussion.id
    assert comment.author_id == TEST_USER_ID


@pytest.mark.integration
async def test_create_comment_strips_content_whitespace(db_session):
    """create_comment() strips whitespace from content."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    repo = _repo(db_session)

    comment = await repo.create_comment(
        discussion_id=discussion.id,
        author_id=TEST_USER_ID,
        content="  Padded content  ",
    )

    assert comment.content == "Padded content"


@pytest.mark.integration
async def test_create_comment_is_not_deleted(db_session):
    """Newly created comment has is_deleted=False."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    repo = _repo(db_session)

    comment = await repo.create_comment(
        discussion_id=discussion.id,
        author_id=TEST_USER_ID,
        content="Not deleted",
    )

    assert comment.is_deleted is False


# ===========================================================================
# get_comment_by_id
# ===========================================================================

@pytest.mark.integration
async def test_get_comment_by_id_returns_existing_comment(db_session):
    """get_comment_by_id() returns the comment when it exists."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    comment = await create_test_comment(db_session, discussion_id=discussion.id)
    await db_session.commit()

    repo = _repo(db_session)
    found = await repo.get_comment_by_id(comment.id)

    assert found is not None
    assert found.id == comment.id


@pytest.mark.integration
async def test_get_comment_by_id_returns_none_for_missing_id(db_session):
    """get_comment_by_id() returns None when the ID does not exist."""
    repo = _repo(db_session)

    result = await repo.get_comment_by_id(uuid.uuid4())

    assert result is None


@pytest.mark.integration
async def test_get_comment_by_id_excludes_soft_deleted_by_default(db_session):
    """get_comment_by_id() returns None for a soft-deleted comment."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    comment = await create_test_comment(db_session, discussion_id=discussion.id)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_comment(comment.id)

    result = await repo.get_comment_by_id(comment.id)

    assert result is None


@pytest.mark.integration
async def test_get_comment_by_id_includes_deleted_when_flag_set(db_session):
    """get_comment_by_id(include_deleted=True) returns soft-deleted comments."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    comment = await create_test_comment(db_session, discussion_id=discussion.id)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_comment(comment.id)

    result = await repo.get_comment_by_id(comment.id, include_deleted=True)

    assert result is not None
    assert result.is_deleted is True


# ===========================================================================
# list_comments
# ===========================================================================

@pytest.mark.integration
async def test_list_comments_returns_non_deleted_comments(db_session):
    """list_comments() returns non-deleted comments for a discussion."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    await create_test_comment(db_session, discussion_id=discussion.id, content="Comment A")
    await create_test_comment(db_session, discussion_id=discussion.id, content="Comment B")
    await db_session.commit()

    repo = _repo(db_session)
    comments, total = await repo.list_comments(discussion.id)

    assert total == 2
    assert len(comments) == 2


@pytest.mark.integration
async def test_list_comments_excludes_soft_deleted(db_session):
    """list_comments() does not include soft-deleted comments."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    visible = await create_test_comment(
        db_session, discussion_id=discussion.id, content="Visible"
    )
    gone = await create_test_comment(
        db_session, discussion_id=discussion.id, content="Gone"
    )
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_comment(gone.id)

    comments, total = await repo.list_comments(discussion.id)

    ids = {c.id for c in comments}
    assert visible.id in ids
    assert gone.id not in ids
    assert total == 1


@pytest.mark.integration
async def test_list_comments_filters_by_discussion(db_session):
    """list_comments() returns only comments for the specified discussion."""
    community = await create_test_community(db_session)
    await db_session.commit()
    d1 = await create_test_discussion(db_session, community_id=community.id, title="D1")
    d2 = await create_test_discussion(db_session, community_id=community.id, title="D2")
    await db_session.commit()
    await create_test_comment(db_session, discussion_id=d1.id, content="For D1")
    await create_test_comment(db_session, discussion_id=d2.id, content="For D2")
    await db_session.commit()

    repo = _repo(db_session)
    comments, total = await repo.list_comments(d1.id)

    assert total == 1
    assert comments[0].discussion_id == d1.id


@pytest.mark.integration
async def test_list_comments_ordered_oldest_first(db_session):
    """list_comments() returns comments in ascending created_at order (oldest first)."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    c1 = await create_test_comment(db_session, discussion_id=discussion.id, content="First")
    await db_session.commit()
    c2 = await create_test_comment(db_session, discussion_id=discussion.id, content="Second")
    await db_session.commit()

    repo = _repo(db_session)
    comments, _ = await repo.list_comments(discussion.id, limit=10)

    ids = [c.id for c in comments]
    assert ids.index(c1.id) < ids.index(c2.id)


@pytest.mark.integration
async def test_list_comments_respects_limit(db_session):
    """list_comments() respects the limit parameter."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    for i in range(5):
        await create_test_comment(
            db_session, discussion_id=discussion.id, content=f"Comment {i}"
        )
    await db_session.commit()

    repo = _repo(db_session)
    comments, total = await repo.list_comments(discussion.id, limit=2, offset=0)

    assert len(comments) == 2
    assert total == 5


@pytest.mark.integration
async def test_list_comments_respects_offset(db_session):
    """list_comments() with offset skips earlier results."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    for i in range(4):
        await create_test_comment(
            db_session, discussion_id=discussion.id, content=f"Comment {i}"
        )
    await db_session.commit()

    repo = _repo(db_session)
    all_c, _ = await repo.list_comments(discussion.id, limit=100, offset=0)
    paged_c, _ = await repo.list_comments(discussion.id, limit=100, offset=2)

    assert len(paged_c) == len(all_c) - 2


@pytest.mark.integration
async def test_list_comments_returns_empty_when_none(db_session):
    """list_comments() returns empty list and total=0 when no comments exist."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()

    repo = _repo(db_session)
    comments, total = await repo.list_comments(discussion.id)

    assert comments == [] or list(comments) == []
    assert total == 0


# ===========================================================================
# update_comment
# ===========================================================================

@pytest.mark.integration
async def test_update_comment_changes_content(db_session):
    """update_comment() persists new content and returns the updated comment."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    comment = await create_test_comment(
        db_session, discussion_id=discussion.id, content="Old content"
    )
    await db_session.commit()
    repo = _repo(db_session)

    updated = await repo.update_comment(comment.id, content="New content")

    assert updated is not None
    assert updated.content == "New content"


@pytest.mark.integration
async def test_update_comment_strips_content_whitespace(db_session):
    """update_comment() strips whitespace from the new content."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    comment = await create_test_comment(db_session, discussion_id=discussion.id)
    await db_session.commit()
    repo = _repo(db_session)

    updated = await repo.update_comment(comment.id, content="  Padded  ")

    assert updated.content == "Padded"


@pytest.mark.integration
async def test_update_comment_returns_none_for_missing_id(db_session):
    """update_comment() returns None when the comment ID does not exist."""
    repo = _repo(db_session)

    result = await repo.update_comment(uuid.uuid4(), content="Ghost update")

    assert result is None


@pytest.mark.integration
async def test_update_comment_returns_none_for_deleted_comment(db_session):
    """update_comment() returns None for a soft-deleted comment."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    comment = await create_test_comment(db_session, discussion_id=discussion.id)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_comment(comment.id)

    result = await repo.update_comment(comment.id, content="After delete")

    assert result is None


# ===========================================================================
# soft_delete_comment
# ===========================================================================

@pytest.mark.integration
async def test_soft_delete_comment_returns_true_on_success(db_session):
    """soft_delete_comment() returns True when the comment was deleted."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    comment = await create_test_comment(db_session, discussion_id=discussion.id)
    await db_session.commit()
    repo = _repo(db_session)

    result = await repo.soft_delete_comment(comment.id)

    assert result is True


@pytest.mark.integration
async def test_soft_delete_comment_sets_is_deleted_flag(db_session):
    """soft_delete_comment() sets is_deleted=True on the comment."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    comment = await create_test_comment(db_session, discussion_id=discussion.id)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_comment(comment.id)

    deleted = await repo.get_comment_by_id(comment.id, include_deleted=True)

    assert deleted.is_deleted is True


@pytest.mark.integration
async def test_soft_delete_comment_sets_deleted_at(db_session):
    """soft_delete_comment() sets deleted_at timestamp on the comment."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    comment = await create_test_comment(db_session, discussion_id=discussion.id)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_comment(comment.id)

    deleted = await repo.get_comment_by_id(comment.id, include_deleted=True)

    assert deleted.deleted_at is not None


@pytest.mark.integration
async def test_soft_delete_comment_stores_deleted_by(db_session):
    """soft_delete_comment() stores the deleted_by user ID."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    comment = await create_test_comment(db_session, discussion_id=discussion.id)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_comment(comment.id, deleted_by=TEST_USER_ID)

    deleted = await repo.get_comment_by_id(comment.id, include_deleted=True)

    assert deleted.deleted_by == TEST_USER_ID


@pytest.mark.integration
async def test_soft_delete_comment_returns_false_for_missing_id(db_session):
    """soft_delete_comment() returns False when the ID does not exist."""
    repo = _repo(db_session)

    result = await repo.soft_delete_comment(uuid.uuid4())

    assert result is False


@pytest.mark.integration
async def test_soft_delete_comment_is_idempotent(db_session):
    """Calling soft_delete_comment() twice returns False the second time."""
    community = await create_test_community(db_session)
    await db_session.commit()
    discussion = await create_test_discussion(db_session, community_id=community.id)
    await db_session.commit()
    comment = await create_test_comment(db_session, discussion_id=discussion.id)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete_comment(comment.id)

    result = await repo.soft_delete_comment(comment.id)

    assert result is False
