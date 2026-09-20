"""
CP-16B — CommentRepository Integration Tests

Validates repository-level behaviour for CommentRepository.
All tests use an in-memory SQLite database via the db_session fixture.

Notes:
- get_recent_comments_for_posts uses PostgreSQL ANY() syntax; skipped on SQLite.
- CommentRepository.create enforces one level of nesting: parent must have
  parent_comment_id IS NULL.
"""

import uuid
import pytest

from app.repositories.comment_repository import CommentRepository
from tests.utils import create_test_post, create_test_comment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo(session) -> CommentRepository:
    return CommentRepository(session)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_create_comment_returns_comment_with_id(db_session):
    """create() persists a top-level comment and returns a Comment with a UUID id."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    comment = await repo.create(
        post_id=post.id,
        author_id=uuid.uuid4(),
        content="Great travel post!",
    )

    assert comment is not None
    assert comment.id is not None
    assert isinstance(comment.id, uuid.UUID)
    assert comment.post_id == post.id
    assert comment.content == "Great travel post!"
    assert comment.parent_comment_id is None


@pytest.mark.integration
async def test_create_comment_strips_whitespace(db_session):
    """create() strips leading/trailing whitespace from content."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    comment = await repo.create(
        post_id=post.id,
        author_id=uuid.uuid4(),
        content="   Trimmed content   ",
    )

    assert comment.content == "Trimmed content"


@pytest.mark.integration
async def test_create_comment_returns_none_for_missing_post(db_session):
    """create() returns None when the post_id does not exist."""
    repo = _repo(db_session)

    result = await repo.create(
        post_id=uuid.uuid4(),
        author_id=uuid.uuid4(),
        content="Comment on ghost post",
    )

    assert result is None


@pytest.mark.integration
async def test_create_comment_returns_none_for_deleted_post(db_session):
    """create() returns None when the post is soft-deleted."""
    from app.repositories.post_repository import PostRepository

    post = await create_test_post(db_session)
    await db_session.commit()
    await PostRepository(db_session).soft_delete(post.id)

    repo = _repo(db_session)
    result = await repo.create(
        post_id=post.id,
        author_id=uuid.uuid4(),
        content="On deleted post",
    )

    assert result is None


# ---------------------------------------------------------------------------
# create — replies / nesting
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_create_reply_sets_parent_comment_id(db_session):
    """create() with a parent_comment_id creates a reply."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    parent = await repo.create(
        post_id=post.id,
        author_id=uuid.uuid4(),
        content="Parent comment",
    )
    reply = await repo.create(
        post_id=post.id,
        author_id=uuid.uuid4(),
        content="A reply",
        parent_comment_id=parent.id,
    )

    assert reply is not None
    assert reply.parent_comment_id == parent.id


@pytest.mark.integration
async def test_create_reply_to_reply_is_rejected(db_session):
    """create() returns None when trying to reply to a reply (one-level only)."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    parent = await repo.create(
        post_id=post.id,
        author_id=uuid.uuid4(),
        content="Top-level",
    )
    reply = await repo.create(
        post_id=post.id,
        author_id=uuid.uuid4(),
        content="First reply",
        parent_comment_id=parent.id,
    )

    # Attempt to reply to the reply — should fail
    nested = await repo.create(
        post_id=post.id,
        author_id=uuid.uuid4(),
        content="Nested reply",
        parent_comment_id=reply.id,
    )

    assert nested is None


@pytest.mark.integration
async def test_create_reply_returns_none_for_missing_parent(db_session):
    """create() returns None when the parent_comment_id does not exist."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    result = await repo.create(
        post_id=post.id,
        author_id=uuid.uuid4(),
        content="Orphan reply",
        parent_comment_id=uuid.uuid4(),
    )

    assert result is None


@pytest.mark.integration
async def test_create_reply_requires_same_post(db_session):
    """create() returns None when parent comment belongs to a different post."""
    post_a = await create_test_post(db_session, title="Post A")
    post_b = await create_test_post(db_session, title="Post B")
    await db_session.commit()
    repo = _repo(db_session)

    parent = await repo.create(
        post_id=post_a.id,
        author_id=uuid.uuid4(),
        content="On post A",
    )

    result = await repo.create(
        post_id=post_b.id,
        author_id=uuid.uuid4(),
        content="Cross-post reply attempt",
        parent_comment_id=parent.id,
    )

    assert result is None


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_by_id_returns_existing_comment(db_session):
    """get_by_id() returns the comment when it exists."""
    post = await create_test_post(db_session)
    await db_session.commit()
    comment = await create_test_comment(db_session, post_id=post.id, content="Find me")
    await db_session.commit()

    repo = _repo(db_session)
    found = await repo.get_by_id(comment.id)

    assert found is not None
    assert found.id == comment.id
    assert found.content == "Find me"


@pytest.mark.integration
async def test_get_by_id_returns_none_for_missing_id(db_session):
    """get_by_id() returns None for an unknown ID."""
    repo = _repo(db_session)

    result = await repo.get_by_id(uuid.uuid4())

    assert result is None


@pytest.mark.integration
async def test_get_by_id_excludes_soft_deleted_by_default(db_session):
    """get_by_id() returns None for a soft-deleted comment by default."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    parent = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="To delete")
    await repo.soft_delete(parent.id)

    result = await repo.get_by_id(parent.id)

    assert result is None


@pytest.mark.integration
async def test_get_by_id_includes_deleted_when_flag_set(db_session):
    """get_by_id(include_deleted=True) returns soft-deleted comments."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    comment = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Bye")
    await repo.soft_delete(comment.id)

    result = await repo.get_by_id(comment.id, include_deleted=True)

    assert result is not None
    assert result.is_deleted is True


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_update_changes_comment_content(db_session):
    """update() persists new content and returns the updated comment."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    comment = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Original")

    updated = await repo.update(comment.id, content="Edited content")

    assert updated is not None
    assert updated.content == "Edited content"


@pytest.mark.integration
async def test_update_returns_none_for_missing_comment(db_session):
    """update() returns None when the comment ID does not exist."""
    repo = _repo(db_session)

    result = await repo.update(uuid.uuid4(), content="Ghost edit")

    assert result is None


@pytest.mark.integration
async def test_update_returns_none_for_deleted_comment(db_session):
    """update() returns None for a soft-deleted comment."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    comment = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Will be deleted")
    await repo.soft_delete(comment.id)

    result = await repo.update(comment.id, content="Too late")

    assert result is None


# ---------------------------------------------------------------------------
# soft_delete
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_soft_delete_comment_returns_true(db_session):
    """soft_delete() returns True when deletion succeeds."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    comment = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Delete me")

    result = await repo.soft_delete(comment.id)

    assert result is True


@pytest.mark.integration
async def test_soft_delete_comment_sets_deleted_flag_and_replaces_content(db_session):
    """soft_delete() sets is_deleted=True and replaces content with '[deleted]'."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    comment = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Secret text")
    await repo.soft_delete(comment.id)

    deleted = await repo.get_by_id(comment.id, include_deleted=True)

    assert deleted.is_deleted is True
    assert deleted.content == "[deleted]"
    assert deleted.deleted_at is not None


@pytest.mark.integration
async def test_soft_delete_comment_returns_false_for_missing_id(db_session):
    """soft_delete() returns False when the comment ID does not exist."""
    repo = _repo(db_session)

    result = await repo.soft_delete(uuid.uuid4())

    assert result is False


# ---------------------------------------------------------------------------
# hard_delete
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_hard_delete_comment_removes_row(db_session):
    """hard_delete() permanently removes the comment."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    comment = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Erase me")

    deleted = await repo.hard_delete(comment.id)
    found = await repo.get_by_id(comment.id, include_deleted=True)

    assert deleted is True
    assert found is None


@pytest.mark.integration
async def test_hard_delete_comment_returns_false_for_missing_id(db_session):
    """hard_delete() returns False when the ID does not exist."""
    repo = _repo(db_session)

    result = await repo.hard_delete(uuid.uuid4())

    assert result is False


# ---------------------------------------------------------------------------
# get_comments_for_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_comments_for_post_returns_top_level_only(db_session):
    """get_comments_for_post() returns only top-level (non-reply) comments."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    parent = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Top-level")
    await repo.create(
        post_id=post.id, author_id=uuid.uuid4(),
        content="Reply", parent_comment_id=parent.id
    )

    comments, total = await repo.get_comments_for_post(post.id)

    assert total == 1
    assert comments[0].id == parent.id


@pytest.mark.integration
async def test_get_comments_for_post_loads_replies_when_requested(db_session):
    """get_comments_for_post(include_replies=True) eager-loads reply objects."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    parent = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Parent")
    await repo.create(
        post_id=post.id, author_id=uuid.uuid4(),
        content="Child", parent_comment_id=parent.id
    )

    comments, total = await repo.get_comments_for_post(post.id, include_replies=True)

    assert len(comments[0].replies) == 1
    assert comments[0].replies[0].content == "Child"


@pytest.mark.integration
async def test_get_comments_for_post_ordered_oldest_first(db_session):
    """get_comments_for_post() returns comments ordered by created_at ascending."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    c1 = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="First")
    c2 = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Second")

    comments, _ = await repo.get_comments_for_post(post.id)

    ids = [c.id for c in comments]
    assert ids.index(c1.id) < ids.index(c2.id)


@pytest.mark.integration
async def test_get_comments_for_post_excludes_deleted(db_session):
    """get_comments_for_post() excludes soft-deleted comments."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    c1 = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Live")
    c2 = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Deleted")
    await repo.soft_delete(c2.id)

    comments, total = await repo.get_comments_for_post(post.id)

    ids = {c.id for c in comments}
    assert c1.id in ids
    assert c2.id not in ids
    assert total == 1


@pytest.mark.integration
async def test_get_comments_for_post_pagination(db_session):
    """get_comments_for_post() respects limit and offset parameters."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    for i in range(5):
        await repo.create(post_id=post.id, author_id=uuid.uuid4(), content=f"Comment {i}")

    comments, total = await repo.get_comments_for_post(post.id, limit=2, offset=0)

    assert total == 5
    assert len(comments) == 2


# ---------------------------------------------------------------------------
# get_replies_for_comment
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_replies_for_comment_returns_direct_replies(db_session):
    """get_replies_for_comment() returns all replies for a parent comment."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    parent = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Parent")
    r1 = await repo.create(
        post_id=post.id, author_id=uuid.uuid4(),
        content="Reply 1", parent_comment_id=parent.id
    )
    r2 = await repo.create(
        post_id=post.id, author_id=uuid.uuid4(),
        content="Reply 2", parent_comment_id=parent.id
    )

    replies, total = await repo.get_replies_for_comment(parent.id)

    assert total == 2
    reply_ids = {r.id for r in replies}
    assert {r1.id, r2.id} == reply_ids


@pytest.mark.integration
async def test_get_replies_for_comment_excludes_deleted(db_session):
    """get_replies_for_comment() excludes soft-deleted replies."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    parent = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Parent")
    r1 = await repo.create(
        post_id=post.id, author_id=uuid.uuid4(),
        content="Active reply", parent_comment_id=parent.id
    )
    r2 = await repo.create(
        post_id=post.id, author_id=uuid.uuid4(),
        content="Deleted reply", parent_comment_id=parent.id
    )
    await repo.soft_delete(r2.id)

    replies, total = await repo.get_replies_for_comment(parent.id)

    assert total == 1
    assert replies[0].id == r1.id


@pytest.mark.integration
async def test_get_replies_for_comment_returns_empty_when_no_replies(db_session):
    """get_replies_for_comment() returns empty list for a comment with no replies."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    parent = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Lonely")

    replies, total = await repo.get_replies_for_comment(parent.id)

    assert total == 0
    assert len(replies) == 0


# ---------------------------------------------------------------------------
# get_comments_by_author
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_comments_by_author_returns_all_author_comments(db_session):
    """get_comments_by_author() returns comments across all posts for the author."""
    post_a = await create_test_post(db_session, title="Post A")
    post_b = await create_test_post(db_session, title="Post B")
    await db_session.commit()
    repo = _repo(db_session)
    author_id = uuid.uuid4()

    await repo.create(post_id=post_a.id, author_id=author_id, content="Comment on A")
    await repo.create(post_id=post_b.id, author_id=author_id, content="Comment on B")
    await repo.create(post_id=post_a.id, author_id=uuid.uuid4(), content="Other author")

    comments, total = await repo.get_comments_by_author(author_id)

    assert total == 2
    assert all(c.author_id == author_id for c in comments)


@pytest.mark.integration
async def test_get_comments_by_author_excludes_deleted(db_session):
    """get_comments_by_author() excludes soft-deleted comments."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    author_id = uuid.uuid4()

    c1 = await repo.create(post_id=post.id, author_id=author_id, content="Active")
    c2 = await repo.create(post_id=post.id, author_id=author_id, content="Deleted")
    await repo.soft_delete(c2.id)

    comments, total = await repo.get_comments_by_author(author_id)

    assert total == 1
    assert comments[0].id == c1.id


# ---------------------------------------------------------------------------
# get_comment_count_for_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_comment_count_for_post_returns_correct_count(db_session):
    """get_comment_count_for_post() counts all non-deleted comments including replies."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    parent = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Top")
    await repo.create(
        post_id=post.id, author_id=uuid.uuid4(),
        content="Reply", parent_comment_id=parent.id
    )

    count = await repo.get_comment_count_for_post(post.id)

    assert count == 2


@pytest.mark.integration
async def test_get_comment_count_excludes_deleted(db_session):
    """get_comment_count_for_post() does not count soft-deleted comments."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    c1 = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Live")
    c2 = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Dead")
    await repo.soft_delete(c2.id)

    count = await repo.get_comment_count_for_post(post.id)

    assert count == 1


@pytest.mark.integration
async def test_get_comment_count_returns_zero_for_post_with_no_comments(db_session):
    """get_comment_count_for_post() returns 0 when there are no comments."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    count = await repo.get_comment_count_for_post(post.id)

    assert count == 0


# ---------------------------------------------------------------------------
# get_comment_counts_for_posts
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_comment_counts_for_posts_returns_correct_counts(db_session):
    """get_comment_counts_for_posts() returns per-post comment counts."""
    p1 = await create_test_post(db_session, title="P1")
    p2 = await create_test_post(db_session, title="P2")
    p3 = await create_test_post(db_session, title="P3")
    await db_session.commit()
    repo = _repo(db_session)

    await repo.create(post_id=p1.id, author_id=uuid.uuid4(), content="A")
    await repo.create(post_id=p1.id, author_id=uuid.uuid4(), content="B")
    await repo.create(post_id=p2.id, author_id=uuid.uuid4(), content="C")

    counts = await repo.get_comment_counts_for_posts([p1.id, p2.id, p3.id])

    assert counts[p1.id] == 2
    assert counts[p2.id] == 1
    assert counts[p3.id] == 0


@pytest.mark.integration
async def test_get_comment_counts_for_posts_empty_list_returns_empty_dict(db_session):
    """get_comment_counts_for_posts([]) returns an empty dict."""
    repo = _repo(db_session)

    counts = await repo.get_comment_counts_for_posts([])

    assert counts == {}


# ---------------------------------------------------------------------------
# get_recent_comments_for_posts — skipped (PostgreSQL ANY() syntax)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skip(
    reason=(
        "get_recent_comments_for_posts uses a raw SQL query with PostgreSQL "
        "ANY() syntax which is not supported by SQLite. This method is covered "
        "by the PostgreSQL integration environment."
    )
)
async def test_get_recent_comments_for_posts_skipped(db_session):
    pass


# ---------------------------------------------------------------------------
# can_user_modify_comment
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_can_user_modify_comment_returns_true_for_author(db_session):
    """can_user_modify_comment() returns True for the comment's author."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    author_id = uuid.uuid4()
    comment = await repo.create(post_id=post.id, author_id=author_id, content="Mine")

    result = await repo.can_user_modify_comment(comment.id, author_id)

    assert result is True


@pytest.mark.integration
async def test_can_user_modify_comment_returns_false_for_other_user(db_session):
    """can_user_modify_comment() returns False for a user who is not the author."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    comment = await repo.create(post_id=post.id, author_id=uuid.uuid4(), content="Not yours")

    result = await repo.can_user_modify_comment(comment.id, uuid.uuid4())

    assert result is False


@pytest.mark.integration
async def test_can_user_modify_comment_returns_false_for_missing_comment(db_session):
    """can_user_modify_comment() returns False when the comment does not exist."""
    repo = _repo(db_session)

    result = await repo.can_user_modify_comment(uuid.uuid4(), uuid.uuid4())

    assert result is False


@pytest.mark.integration
async def test_can_user_modify_comment_returns_false_for_deleted_comment(db_session):
    """can_user_modify_comment() returns False for a soft-deleted comment."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    author_id = uuid.uuid4()
    comment = await repo.create(post_id=post.id, author_id=author_id, content="Gone")
    await repo.soft_delete(comment.id)

    result = await repo.can_user_modify_comment(comment.id, author_id)

    assert result is False
