"""
CP-16B — InteractionRepository Integration Tests

Validates repository-level behaviour for InteractionRepository.
All tests use an in-memory SQLite database via the db_session fixture.

Notes on SQLite compatibility
------------------------------
like_post() and bookmark_post() use PostgreSQL's
  INSERT ... ON CONFLICT DO NOTHING
dialect statement.  On SQLite this becomes a plain INSERT, which raises an
IntegrityError on duplicate (post_id, user_id) due to the UniqueConstraint.

Consequence for tests
---------------------
- First like / bookmark: works normally on both engines.
- Duplicate like / bookmark: on PostgreSQL returns False (conflict ignored);
  on SQLite raises IntegrityError.

Strategy
--------
- Tests that only exercise the happy-path (first call) run unmodified.
- Tests that exercise idempotency / duplicate protection are marked with
  ``pytest.mark.skip`` and document why, directing to the Postgres env.
- All other methods (unlike, unbookmark, share, counts, existence checks,
  bulk queries) do not use PostgreSQL-specific constructs and run normally.
"""

import uuid
import pytest

from app.repositories.interaction_repository import InteractionRepository
from tests.utils import create_test_post


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo(session) -> InteractionRepository:
    return InteractionRepository(session)


# ---------------------------------------------------------------------------
# like_post — happy path
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_like_post_returns_true_on_first_like(db_session):
    """like_post() returns True when the like is successfully created."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    result = await repo.like_post(post.id, user_id)

    assert result is True


@pytest.mark.integration
async def test_like_post_creates_like_record(db_session):
    """like_post() persists a Like row that is_post_liked_by_user can find."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    await repo.like_post(post.id, user_id)

    assert await repo.is_post_liked_by_user(post.id, user_id) is True


@pytest.mark.integration
@pytest.mark.skip(
    reason=(
        "like_post() uses PostgreSQL INSERT ... ON CONFLICT DO NOTHING. "
        "On SQLite a duplicate insert raises IntegrityError instead of being "
        "silently ignored, so the idempotency return-value (False) cannot be "
        "tested on this engine. Covered by the PostgreSQL integration suite."
    )
)
async def test_like_post_returns_false_on_duplicate(db_session):
    """like_post() returns False when the user already liked the post (idempotent)."""
    pass


# ---------------------------------------------------------------------------
# unlike_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_unlike_post_returns_true_when_like_exists(db_session):
    """unlike_post() returns True when a like was successfully removed."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    await repo.like_post(post.id, user_id)
    result = await repo.unlike_post(post.id, user_id)

    assert result is True


@pytest.mark.integration
async def test_unlike_post_removes_like(db_session):
    """unlike_post() removes the like so is_post_liked_by_user returns False."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    await repo.like_post(post.id, user_id)
    await repo.unlike_post(post.id, user_id)

    assert await repo.is_post_liked_by_user(post.id, user_id) is False


@pytest.mark.integration
async def test_unlike_post_returns_false_when_no_like_exists(db_session):
    """unlike_post() returns False when the user has not liked the post."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    result = await repo.unlike_post(post.id, uuid.uuid4())

    assert result is False


# ---------------------------------------------------------------------------
# is_post_liked_by_user
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_is_post_liked_by_user_returns_false_before_like(db_session):
    """is_post_liked_by_user() returns False when no like exists."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    result = await repo.is_post_liked_by_user(post.id, uuid.uuid4())

    assert result is False


@pytest.mark.integration
async def test_is_post_liked_by_user_returns_true_after_like(db_session):
    """is_post_liked_by_user() returns True after a like is recorded."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    await repo.like_post(post.id, user_id)

    assert await repo.is_post_liked_by_user(post.id, user_id) is True


@pytest.mark.integration
async def test_is_post_liked_by_user_is_user_specific(db_session):
    """is_post_liked_by_user() is scoped to the given user, not all likers."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    await repo.like_post(post.id, user_a)

    assert await repo.is_post_liked_by_user(post.id, user_b) is False


# ---------------------------------------------------------------------------
# get_post_like_count
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_post_like_count_returns_zero_initially(db_session):
    """get_post_like_count() returns 0 for a post with no likes."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    count = await repo.get_post_like_count(post.id)

    assert count == 0


@pytest.mark.integration
async def test_get_post_like_count_increments_with_each_like(db_session):
    """get_post_like_count() returns the correct total after multiple likes."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    await repo.like_post(post.id, uuid.uuid4())
    await repo.like_post(post.id, uuid.uuid4())
    await repo.like_post(post.id, uuid.uuid4())

    count = await repo.get_post_like_count(post.id)

    assert count == 3


@pytest.mark.integration
async def test_get_post_like_count_decrements_after_unlike(db_session):
    """get_post_like_count() decreases after a like is removed."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    await repo.like_post(post.id, user_id)
    await repo.like_post(post.id, uuid.uuid4())
    await repo.unlike_post(post.id, user_id)

    count = await repo.get_post_like_count(post.id)

    assert count == 1


# ---------------------------------------------------------------------------
# get_posts_liked_by_user
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_posts_liked_by_user_returns_liked_post_ids(db_session):
    """get_posts_liked_by_user() returns the post IDs the user has liked."""
    p1 = await create_test_post(db_session, title="P1")
    p2 = await create_test_post(db_session, title="P2")
    p3 = await create_test_post(db_session, title="P3")
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    await repo.like_post(p1.id, user_id)
    await repo.like_post(p3.id, user_id)

    post_ids, total = await repo.get_posts_liked_by_user(user_id)

    assert total == 2
    assert set(post_ids) == {p1.id, p3.id}


@pytest.mark.integration
async def test_get_posts_liked_by_user_returns_empty_when_no_likes(db_session):
    """get_posts_liked_by_user() returns empty list for a user with no likes."""
    repo = _repo(db_session)

    post_ids, total = await repo.get_posts_liked_by_user(uuid.uuid4())

    assert total == 0
    assert len(post_ids) == 0


@pytest.mark.integration
async def test_get_posts_liked_by_user_respects_pagination(db_session):
    """get_posts_liked_by_user() respects limit and offset."""
    posts = []
    for i in range(5):
        p = await create_test_post(db_session, title=f"P{i}")
        posts.append(p)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    for p in posts:
        await repo.like_post(p.id, user_id)

    post_ids, total = await repo.get_posts_liked_by_user(user_id, limit=2, offset=0)

    assert total == 5
    assert len(post_ids) == 2


# ---------------------------------------------------------------------------
# bookmark_post — happy path
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_bookmark_post_returns_true_on_first_bookmark(db_session):
    """bookmark_post() returns True when the bookmark is successfully created."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    result = await repo.bookmark_post(post.id, uuid.uuid4())

    assert result is True


@pytest.mark.integration
async def test_bookmark_post_creates_bookmark_record(db_session):
    """bookmark_post() persists a Bookmark row findable via is_post_bookmarked_by_user."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    await repo.bookmark_post(post.id, user_id)

    assert await repo.is_post_bookmarked_by_user(post.id, user_id) is True


@pytest.mark.integration
@pytest.mark.skip(
    reason=(
        "bookmark_post() uses PostgreSQL INSERT ... ON CONFLICT DO NOTHING. "
        "On SQLite a duplicate insert raises IntegrityError instead of being "
        "silently ignored. Idempotency return-value test covered by Postgres suite."
    )
)
async def test_bookmark_post_returns_false_on_duplicate(db_session):
    """bookmark_post() returns False when the post is already bookmarked."""
    pass


# ---------------------------------------------------------------------------
# unbookmark_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_unbookmark_post_returns_true_when_bookmark_exists(db_session):
    """unbookmark_post() returns True when a bookmark was removed."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    await repo.bookmark_post(post.id, user_id)
    result = await repo.unbookmark_post(post.id, user_id)

    assert result is True


@pytest.mark.integration
async def test_unbookmark_post_removes_bookmark(db_session):
    """unbookmark_post() removes the record so is_post_bookmarked_by_user returns False."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    await repo.bookmark_post(post.id, user_id)
    await repo.unbookmark_post(post.id, user_id)

    assert await repo.is_post_bookmarked_by_user(post.id, user_id) is False


@pytest.mark.integration
async def test_unbookmark_post_returns_false_when_not_bookmarked(db_session):
    """unbookmark_post() returns False when the user has no bookmark for the post."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    result = await repo.unbookmark_post(post.id, uuid.uuid4())

    assert result is False


# ---------------------------------------------------------------------------
# is_post_bookmarked_by_user
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_is_post_bookmarked_returns_false_before_bookmark(db_session):
    """is_post_bookmarked_by_user() returns False when no bookmark exists."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    result = await repo.is_post_bookmarked_by_user(post.id, uuid.uuid4())

    assert result is False


@pytest.mark.integration
async def test_is_post_bookmarked_is_user_specific(db_session):
    """is_post_bookmarked_by_user() is scoped to the given user."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    await repo.bookmark_post(post.id, user_a)

    assert await repo.is_post_bookmarked_by_user(post.id, user_b) is False


# ---------------------------------------------------------------------------
# get_bookmarked_posts_by_user
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_bookmarked_posts_by_user_returns_bookmarked_ids(db_session):
    """get_bookmarked_posts_by_user() returns post IDs the user has bookmarked."""
    p1 = await create_test_post(db_session, title="B1")
    p2 = await create_test_post(db_session, title="B2")
    await create_test_post(db_session, title="B3")
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    await repo.bookmark_post(p1.id, user_id)
    await repo.bookmark_post(p2.id, user_id)

    post_ids, total = await repo.get_bookmarked_posts_by_user(user_id)

    assert total == 2
    assert set(post_ids) == {p1.id, p2.id}


@pytest.mark.integration
async def test_get_bookmarked_posts_by_user_empty_when_no_bookmarks(db_session):
    """get_bookmarked_posts_by_user() returns empty list with no bookmarks."""
    repo = _repo(db_session)

    post_ids, total = await repo.get_bookmarked_posts_by_user(uuid.uuid4())

    assert total == 0
    assert len(post_ids) == 0


@pytest.mark.integration
async def test_get_bookmarked_posts_by_user_respects_pagination(db_session):
    """get_bookmarked_posts_by_user() respects limit and offset."""
    posts = []
    for i in range(4):
        p = await create_test_post(db_session, title=f"BK{i}")
        posts.append(p)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    for p in posts:
        await repo.bookmark_post(p.id, user_id)

    post_ids, total = await repo.get_bookmarked_posts_by_user(user_id, limit=2, offset=0)

    assert total == 4
    assert len(post_ids) == 2


# ---------------------------------------------------------------------------
# share_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_share_post_creates_share_record(db_session):
    """share_post() persists a Share row and returns it."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    share = await repo.share_post(post.id, user_id, share_channel="twitter")

    assert share is not None
    assert share.id is not None
    assert share.post_id == post.id
    assert share.user_id == user_id
    assert share.share_channel == "twitter"


@pytest.mark.integration
async def test_share_post_allows_multiple_shares_by_same_user(db_session):
    """share_post() is not idempotent — the same user can share multiple times."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    share1 = await repo.share_post(post.id, user_id, share_channel="twitter")
    share2 = await repo.share_post(post.id, user_id, share_channel="instagram")

    assert share1.id != share2.id


@pytest.mark.integration
async def test_share_post_without_channel_stores_none(db_session):
    """share_post() with no channel stores share_channel=None."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    share = await repo.share_post(post.id, uuid.uuid4())

    assert share.share_channel is None


# ---------------------------------------------------------------------------
# get_post_share_count
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_post_share_count_returns_zero_initially(db_session):
    """get_post_share_count() returns 0 when no shares exist."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    count = await repo.get_post_share_count(post.id)

    assert count == 0


@pytest.mark.integration
async def test_get_post_share_count_reflects_all_shares(db_session):
    """get_post_share_count() counts every share event, including duplicates."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    await repo.share_post(post.id, user_id, share_channel="twitter")
    await repo.share_post(post.id, user_id, share_channel="facebook")
    await repo.share_post(post.id, uuid.uuid4(), share_channel="whatsapp")

    count = await repo.get_post_share_count(post.id)

    assert count == 3


# ---------------------------------------------------------------------------
# get_shares_by_user
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_shares_by_user_returns_user_shares(db_session):
    """get_shares_by_user() returns all Share records for that user."""
    p1 = await create_test_post(db_session, title="S1")
    p2 = await create_test_post(db_session, title="S2")
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    await repo.share_post(p1.id, user_id, share_channel="twitter")
    await repo.share_post(p2.id, user_id, share_channel="email")
    await repo.share_post(p1.id, uuid.uuid4())  # different user

    shares, total = await repo.get_shares_by_user(user_id)

    assert total == 2
    assert all(s.user_id == user_id for s in shares)


@pytest.mark.integration
async def test_get_shares_by_user_returns_empty_when_no_shares(db_session):
    """get_shares_by_user() returns empty list for a user with no shares."""
    repo = _repo(db_session)

    shares, total = await repo.get_shares_by_user(uuid.uuid4())

    assert total == 0
    assert len(shares) == 0


@pytest.mark.integration
async def test_get_shares_by_user_respects_pagination(db_session):
    """get_shares_by_user() respects limit and offset."""
    posts = []
    for i in range(5):
        p = await create_test_post(db_session, title=f"SP{i}")
        posts.append(p)
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    for p in posts:
        await repo.share_post(p.id, user_id)

    shares, total = await repo.get_shares_by_user(user_id, limit=3, offset=0)

    assert total == 5
    assert len(shares) == 3


# ---------------------------------------------------------------------------
# get_interaction_counts_for_posts
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_interaction_counts_returns_likes_and_shares(db_session):
    """get_interaction_counts_for_posts() returns like and share counts per post."""
    p1 = await create_test_post(db_session, title="IC1")
    p2 = await create_test_post(db_session, title="IC2")
    await db_session.commit()
    repo = _repo(db_session)

    await repo.like_post(p1.id, uuid.uuid4())
    await repo.like_post(p1.id, uuid.uuid4())
    await repo.share_post(p1.id, uuid.uuid4())
    await repo.share_post(p2.id, uuid.uuid4())
    await repo.share_post(p2.id, uuid.uuid4())

    counts = await repo.get_interaction_counts_for_posts([p1.id, p2.id])

    assert counts[p1.id]["likes"] == 2
    assert counts[p1.id]["shares"] == 1
    assert counts[p2.id]["likes"] == 0
    assert counts[p2.id]["shares"] == 2


@pytest.mark.integration
async def test_get_interaction_counts_initialises_zeros(db_session):
    """get_interaction_counts_for_posts() includes entries with zero counts."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    counts = await repo.get_interaction_counts_for_posts([post.id])

    assert post.id in counts
    assert counts[post.id]["likes"] == 0
    assert counts[post.id]["shares"] == 0


@pytest.mark.integration
async def test_get_interaction_counts_empty_list_returns_empty_dict(db_session):
    """get_interaction_counts_for_posts([]) returns an empty dict."""
    repo = _repo(db_session)

    counts = await repo.get_interaction_counts_for_posts([])

    assert counts == {}


# ---------------------------------------------------------------------------
# get_user_interactions_for_posts
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_user_interactions_returns_liked_and_bookmarked_flags(db_session):
    """get_user_interactions_for_posts() returns is_liked and is_bookmarked flags."""
    p1 = await create_test_post(db_session, title="UI1")
    p2 = await create_test_post(db_session, title="UI2")
    p3 = await create_test_post(db_session, title="UI3")
    await db_session.commit()
    repo = _repo(db_session)
    user_id = uuid.uuid4()

    await repo.like_post(p1.id, user_id)
    await repo.bookmark_post(p2.id, user_id)

    interactions = await repo.get_user_interactions_for_posts(
        [p1.id, p2.id, p3.id], user_id
    )

    assert interactions[p1.id]["is_liked"] is True
    assert interactions[p1.id]["is_bookmarked"] is False
    assert interactions[p2.id]["is_liked"] is False
    assert interactions[p2.id]["is_bookmarked"] is True
    assert interactions[p3.id]["is_liked"] is False
    assert interactions[p3.id]["is_bookmarked"] is False


@pytest.mark.integration
async def test_get_user_interactions_empty_list_returns_empty_dict(db_session):
    """get_user_interactions_for_posts([]) returns an empty dict."""
    repo = _repo(db_session)

    interactions = await repo.get_user_interactions_for_posts([], uuid.uuid4())

    assert interactions == {}


@pytest.mark.integration
async def test_get_user_interactions_is_user_specific(db_session):
    """get_user_interactions_for_posts() only reflects the requesting user's actions."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    await repo.like_post(post.id, user_a)

    interactions = await repo.get_user_interactions_for_posts([post.id], user_b)

    assert interactions[post.id]["is_liked"] is False


# ---------------------------------------------------------------------------
# get_comment_counts_for_posts (comment count helper on InteractionRepository)
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_interaction_repo_get_comment_counts_returns_correct_counts(db_session):
    """InteractionRepository.get_comment_counts_for_posts() mirrors CommentRepository counts."""
    from app.repositories.comment_repository import CommentRepository

    p1 = await create_test_post(db_session, title="CC1")
    p2 = await create_test_post(db_session, title="CC2")
    await db_session.commit()

    comment_repo = CommentRepository(db_session)
    await comment_repo.create(post_id=p1.id, author_id=uuid.uuid4(), content="A")
    await comment_repo.create(post_id=p1.id, author_id=uuid.uuid4(), content="B")
    await comment_repo.create(post_id=p2.id, author_id=uuid.uuid4(), content="C")

    repo = _repo(db_session)
    counts = await repo.get_comment_counts_for_posts([p1.id, p2.id])

    assert counts[p1.id] == 2
    assert counts[p2.id] == 1


@pytest.mark.integration
async def test_interaction_repo_get_comment_counts_empty_list(db_session):
    """InteractionRepository.get_comment_counts_for_posts([]) returns empty dict."""
    repo = _repo(db_session)

    counts = await repo.get_comment_counts_for_posts([])

    assert counts == {}
