"""
CP-16B — PostRepository Integration Tests

Validates repository-level behaviour for PostRepository.
All tests use an in-memory SQLite database via the db_session fixture.
Business logic and HTTP behaviour are out of scope.
"""

import uuid
import pytest
from datetime import datetime, timezone, timedelta

from app.repositories.post_repository import PostRepository
from app.schemas.feed import PostQueryParams
from shared.constants.status import PostStatus, PostVisibility
from tests.utils import create_test_post


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo(session) -> PostRepository:
    return PostRepository(session)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_create_post_returns_post_with_id(db_session):
    """create() persists a post and returns an ORM instance with a UUID id."""
    author_id = uuid.uuid4()
    repo = _repo(db_session)

    post = await repo.create(author_id=author_id, title="My first post")

    assert post is not None
    assert post.id is not None
    assert isinstance(post.id, uuid.UUID)
    assert post.author_id == author_id
    assert post.title == "My first post"


@pytest.mark.integration
async def test_create_post_stores_optional_fields(db_session):
    """create() persists content, location, community_id, and expedition_id."""
    author_id = uuid.uuid4()
    community_id = uuid.uuid4()
    expedition_id = uuid.uuid4()
    repo = _repo(db_session)

    post = await repo.create(
        author_id=author_id,
        title="Full post",
        content="Some content",
        location="Amsterdam",
        community_id=community_id,
        expedition_id=expedition_id,
    )

    assert post.content == "Some content"
    assert post.location == "Amsterdam"
    assert post.community_id == community_id
    assert post.expedition_id == expedition_id


@pytest.mark.integration
async def test_create_post_with_tags_stores_tags(db_session):
    """create() with tags persists tag rows and exposes them on post.tags."""
    repo = _repo(db_session)

    post = await repo.create(
        author_id=uuid.uuid4(),
        title="Tagged post",
        tags=["hiking", "nature", "Alps"],
    )

    tag_values = {t.tag for t in post.tags}
    assert tag_values == {"hiking", "nature", "alps"}  # tags are lowercased


@pytest.mark.integration
async def test_create_post_default_status_and_visibility(db_session):
    """create() defaults to PUBLISHED status and PUBLIC visibility."""
    repo = _repo(db_session)

    post = await repo.create(author_id=uuid.uuid4(), title="Default post")

    assert post.status == PostStatus.PUBLISHED
    assert post.visibility == PostVisibility.PUBLIC


@pytest.mark.integration
async def test_create_post_is_not_deleted(db_session):
    """Newly created post has is_deleted=False."""
    repo = _repo(db_session)

    post = await repo.create(author_id=uuid.uuid4(), title="Live post")

    assert post.is_deleted is False


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_by_id_returns_existing_post(db_session):
    """get_by_id() returns the post when it exists."""
    post = await create_test_post(db_session, title="Findable post")
    await db_session.commit()

    repo = _repo(db_session)
    found = await repo.get_by_id(post.id)

    assert found is not None
    assert found.id == post.id
    assert found.title == "Findable post"


@pytest.mark.integration
async def test_get_by_id_returns_none_for_missing_id(db_session):
    """get_by_id() returns None when the ID does not exist."""
    repo = _repo(db_session)

    result = await repo.get_by_id(uuid.uuid4())

    assert result is None


@pytest.mark.integration
async def test_get_by_id_excludes_soft_deleted_by_default(db_session):
    """get_by_id() returns None for a soft-deleted post by default."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(post.id)

    result = await repo.get_by_id(post.id)

    assert result is None


@pytest.mark.integration
async def test_get_by_id_includes_deleted_when_flag_set(db_session):
    """get_by_id(include_deleted=True) returns soft-deleted posts."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(post.id)

    result = await repo.get_by_id(post.id, include_deleted=True)

    assert result is not None
    assert result.is_deleted is True


# ---------------------------------------------------------------------------
# get_many
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_many_returns_matching_posts(db_session):
    """get_many() returns all posts whose IDs are in the list."""
    p1 = await create_test_post(db_session, title="Post A")
    p2 = await create_test_post(db_session, title="Post B")
    await create_test_post(db_session, title="Post C")
    await db_session.commit()

    repo = _repo(db_session)
    results = await repo.get_many([p1.id, p2.id])

    ids = {p.id for p in results}
    assert ids == {p1.id, p2.id}


@pytest.mark.integration
async def test_get_many_excludes_soft_deleted(db_session):
    """get_many() excludes soft-deleted posts by default."""
    p1 = await create_test_post(db_session, title="Visible")
    p2 = await create_test_post(db_session, title="Deleted")
    await db_session.commit()

    repo = _repo(db_session)
    await repo.soft_delete(p2.id)

    results = await repo.get_many([p1.id, p2.id])

    assert len(results) == 1
    assert results[0].id == p1.id


@pytest.mark.integration
async def test_get_many_empty_list_returns_empty(db_session):
    """get_many([]) returns an empty list without error."""
    repo = _repo(db_session)

    results = await repo.get_many([])

    assert results == [] or list(results) == []


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_update_changes_title(db_session):
    """update() persists a new title and returns the updated post."""
    post = await create_test_post(db_session, title="Old title")
    await db_session.commit()
    repo = _repo(db_session)

    updated = await repo.update(post.id, title="New title")

    assert updated is not None
    assert updated.title == "New title"


@pytest.mark.integration
async def test_update_replaces_tags(db_session):
    """update(tags=[...]) replaces all existing tags."""
    post = await create_test_post(db_session, tags=["old-tag"])
    await db_session.commit()
    repo = _repo(db_session)

    updated = await repo.update(post.id, tags=["new-tag", "another"])

    # The test session uses expire_on_commit=False, so stale PostTag identity-map
    # entries from the initial create may persist after the repository's internal
    # commit.  Explicitly refresh the tags collection to force a fresh DB load.
    await db_session.refresh(updated, attribute_names=["tags"])

    tag_values = {t.tag for t in updated.tags}
    assert tag_values == {"new-tag", "another"}
    assert "old-tag" not in tag_values


@pytest.mark.integration
async def test_update_returns_none_for_missing_post(db_session):
    """update() returns None when the post ID does not exist."""
    repo = _repo(db_session)

    result = await repo.update(uuid.uuid4(), title="Ghost update")

    assert result is None


@pytest.mark.integration
async def test_update_returns_none_for_deleted_post(db_session):
    """update() returns None for a soft-deleted post."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(post.id)

    result = await repo.update(post.id, title="Should not apply")

    assert result is None


# ---------------------------------------------------------------------------
# soft_delete
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_soft_delete_returns_true_on_success(db_session):
    """soft_delete() returns True when the post was deleted."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    result = await repo.soft_delete(post.id)

    assert result is True


@pytest.mark.integration
async def test_soft_delete_sets_is_deleted_flag(db_session):
    """soft_delete() sets is_deleted=True and deleted_at on the post."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(post.id)

    deleted_post = await repo.get_by_id(post.id, include_deleted=True)

    assert deleted_post.is_deleted is True
    assert deleted_post.deleted_at is not None


@pytest.mark.integration
async def test_soft_delete_returns_false_for_missing_post(db_session):
    """soft_delete() returns False when the post ID does not exist."""
    repo = _repo(db_session)

    result = await repo.soft_delete(uuid.uuid4())

    assert result is False


@pytest.mark.integration
async def test_soft_delete_is_idempotent(db_session):
    """Calling soft_delete() twice returns False the second time."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(post.id)

    result = await repo.soft_delete(post.id)

    assert result is False


# ---------------------------------------------------------------------------
# hard_delete
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_hard_delete_removes_post_permanently(db_session):
    """hard_delete() permanently removes the post row."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    deleted = await repo.hard_delete(post.id)
    found = await repo.get_by_id(post.id, include_deleted=True)

    assert deleted is True
    assert found is None


@pytest.mark.integration
async def test_hard_delete_returns_false_for_missing_post(db_session):
    """hard_delete() returns False when the post ID does not exist."""
    repo = _repo(db_session)

    result = await repo.hard_delete(uuid.uuid4())

    assert result is False


# ---------------------------------------------------------------------------
# list_posts — basic retrieval
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_list_posts_returns_all_published(db_session):
    """list_posts() returns all published, non-deleted posts."""
    await create_test_post(db_session, title="Post 1")
    await create_test_post(db_session, title="Post 2")
    await db_session.commit()

    repo = _repo(db_session)
    params = PostQueryParams()
    posts, total = await repo.list_posts(params)

    assert total >= 2
    assert len(posts) >= 2


@pytest.mark.integration
async def test_list_posts_excludes_soft_deleted(db_session):
    """list_posts() does not include soft-deleted posts."""
    p1 = await create_test_post(db_session, title="Visible")
    p2 = await create_test_post(db_session, title="Gone")
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(p2.id)

    params = PostQueryParams()
    posts, total = await repo.list_posts(params)

    ids = {p.id for p in posts}
    assert p1.id in ids
    assert p2.id not in ids


# ---------------------------------------------------------------------------
# list_posts — pagination
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_list_posts_pagination_limit(db_session):
    """list_posts() respects the limit parameter."""
    for i in range(5):
        await create_test_post(db_session, title=f"Post {i}")
    await db_session.commit()

    repo = _repo(db_session)
    params = PostQueryParams(limit=2, offset=0)
    posts, total = await repo.list_posts(params)

    assert len(posts) == 2
    assert total >= 5


@pytest.mark.integration
async def test_list_posts_pagination_offset(db_session):
    """list_posts() with offset skips earlier results."""
    for i in range(4):
        await create_test_post(db_session, title=f"Paged {i}")
    await db_session.commit()

    repo = _repo(db_session)
    params_all = PostQueryParams(limit=100, offset=0)
    params_paged = PostQueryParams(limit=100, offset=2)

    all_posts, _ = await repo.list_posts(params_all)
    paged_posts, _ = await repo.list_posts(params_paged)

    assert len(paged_posts) == len(all_posts) - 2


@pytest.mark.integration
async def test_list_posts_ordered_newest_first(db_session):
    """list_posts() returns results in descending created_at order."""
    p1 = await create_test_post(db_session, title="Earlier")
    await db_session.commit()
    p2 = await create_test_post(db_session, title="Later")
    await db_session.commit()

    repo = _repo(db_session)
    params = PostQueryParams(limit=10)
    posts, _ = await repo.list_posts(params)

    ids = [p.id for p in posts]
    assert ids.index(p2.id) < ids.index(p1.id)


# ---------------------------------------------------------------------------
# list_posts — filtering
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_list_posts_filter_by_author(db_session):
    """list_posts() with author_id filter returns only that author's posts."""
    author_a = uuid.uuid4()
    author_b = uuid.uuid4()
    await create_test_post(db_session, author_id=author_a, title="By A")
    await create_test_post(db_session, author_id=author_b, title="By B")
    await db_session.commit()

    repo = _repo(db_session)
    params = PostQueryParams(author_id=author_a)
    posts, total = await repo.list_posts(params)

    assert total == 1
    assert all(p.author_id == author_a for p in posts)


@pytest.mark.integration
async def test_list_posts_filter_by_community(db_session):
    """list_posts() with community_id filter returns only community posts."""
    community_id = uuid.uuid4()
    await create_test_post(db_session, community_id=community_id, title="In community")
    await create_test_post(db_session, title="No community")
    await db_session.commit()

    repo = _repo(db_session)
    params = PostQueryParams(community_id=community_id)
    posts, total = await repo.list_posts(params)

    assert total == 1
    assert posts[0].community_id == community_id


@pytest.mark.integration
async def test_list_posts_filter_by_visibility(db_session):
    """list_posts() with visibility filter returns only matching posts."""
    await create_test_post(db_session, visibility=PostVisibility.PUBLIC, title="Public")
    await create_test_post(db_session, visibility=PostVisibility.PRIVATE, title="Private")
    await db_session.commit()

    repo = _repo(db_session)
    params = PostQueryParams(visibility=PostVisibility.PRIVATE)
    posts, total = await repo.list_posts(params)

    assert total == 1
    assert posts[0].visibility == PostVisibility.PRIVATE


@pytest.mark.integration
async def test_list_posts_filter_by_location_partial_match(db_session):
    """list_posts() location filter does a case-insensitive partial match."""
    await create_test_post(db_session, location="Amsterdam, Netherlands", title="NL post")
    await create_test_post(db_session, location="Berlin, Germany", title="DE post")
    await db_session.commit()

    repo = _repo(db_session)
    params = PostQueryParams(location="amsterdam")
    posts, total = await repo.list_posts(params)

    assert total == 1
    assert "Amsterdam" in posts[0].location


@pytest.mark.integration
async def test_list_posts_filter_by_tags(db_session):
    """list_posts() tags filter (comma-separated) returns matching posts."""
    await create_test_post(db_session, tags=["hiking", "mountains"], title="Hike post")
    await create_test_post(db_session, tags=["beach", "summer"], title="Beach post")
    await db_session.commit()

    repo = _repo(db_session)
    params = PostQueryParams(tags="hiking")
    posts, total = await repo.list_posts(params)

    assert total == 1
    assert posts[0].title == "Hike post"


@pytest.mark.integration
async def test_list_posts_filter_by_date_range(db_session):
    """list_posts() since/until filters narrow results by created_at."""
    p1 = await create_test_post(db_session, title="Old post")
    await db_session.commit()

    cutoff = datetime.now(timezone.utc)

    p2 = await create_test_post(db_session, title="New post")
    await db_session.commit()

    repo = _repo(db_session)
    params = PostQueryParams(since=cutoff)
    posts, total = await repo.list_posts(params)

    ids = {p.id for p in posts}
    assert p2.id in ids
    assert p1.id not in ids


# ---------------------------------------------------------------------------
# get_posts_by_author
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_posts_by_author_returns_author_posts(db_session):
    """get_posts_by_author() returns all published posts for that author."""
    author_id = uuid.uuid4()
    await create_test_post(db_session, author_id=author_id, title="Post 1")
    await create_test_post(db_session, author_id=author_id, title="Post 2")
    await create_test_post(db_session, title="Other author")
    await db_session.commit()

    repo = _repo(db_session)
    posts, total = await repo.get_posts_by_author(author_id)

    assert total == 2
    assert all(p.author_id == author_id for p in posts)


@pytest.mark.integration
async def test_get_posts_by_author_viewer_sees_only_public(db_session):
    """A different viewer cannot see private posts."""
    author_id = uuid.uuid4()
    viewer_id = uuid.uuid4()
    await create_test_post(db_session, author_id=author_id, visibility=PostVisibility.PUBLIC, title="Public")
    await create_test_post(db_session, author_id=author_id, visibility=PostVisibility.PRIVATE, title="Private")
    await db_session.commit()

    repo = _repo(db_session)
    posts, total = await repo.get_posts_by_author(author_id, current_user_id=viewer_id)

    # Private posts are not visible to other users
    assert all(p.visibility != PostVisibility.PRIVATE for p in posts)


@pytest.mark.integration
async def test_get_posts_by_author_owner_sees_all(db_session):
    """The author viewing their own posts sees all visibility levels."""
    author_id = uuid.uuid4()
    await create_test_post(db_session, author_id=author_id, visibility=PostVisibility.PUBLIC, title="Public")
    await create_test_post(db_session, author_id=author_id, visibility=PostVisibility.PRIVATE, title="Private")
    await db_session.commit()

    repo = _repo(db_session)
    posts, total = await repo.get_posts_by_author(author_id, current_user_id=author_id)

    assert total == 2


# ---------------------------------------------------------------------------
# get_posts_by_community
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_posts_by_community_returns_community_posts(db_session):
    """get_posts_by_community() returns posts for the given community."""
    community_id = uuid.uuid4()
    await create_test_post(db_session, community_id=community_id, title="In community")
    await create_test_post(db_session, community_id=community_id, title="Also in community")
    await create_test_post(db_session, title="No community")
    await db_session.commit()

    repo = _repo(db_session)
    posts, total = await repo.get_posts_by_community(community_id)

    assert total == 2
    assert all(p.community_id == community_id for p in posts)


@pytest.mark.integration
async def test_get_posts_by_community_excludes_private_posts(db_session):
    """get_posts_by_community() does not return PRIVATE posts."""
    community_id = uuid.uuid4()
    await create_test_post(
        db_session, community_id=community_id,
        visibility=PostVisibility.PRIVATE, title="Private"
    )
    await create_test_post(
        db_session, community_id=community_id,
        visibility=PostVisibility.PUBLIC, title="Public"
    )
    await db_session.commit()

    repo = _repo(db_session)
    posts, total = await repo.get_posts_by_community(community_id)

    assert total == 1
    assert posts[0].visibility == PostVisibility.PUBLIC


# ---------------------------------------------------------------------------
# search_posts_by_tags
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_search_posts_by_tags_returns_matching_posts(db_session):
    """search_posts_by_tags() returns posts that have any of the given tags."""
    await create_test_post(db_session, tags=["hiking", "alps"], title="Alpine hike")
    await create_test_post(db_session, tags=["beach", "ocean"], title="Beachside")
    await db_session.commit()

    repo = _repo(db_session)
    posts, total = await repo.search_posts_by_tags(["alps"])

    assert total == 1
    assert posts[0].title == "Alpine hike"


@pytest.mark.integration
async def test_search_posts_by_tags_uses_or_logic(db_session):
    """search_posts_by_tags() returns posts matching ANY of the supplied tags."""
    await create_test_post(db_session, tags=["hiking"], title="Hike")
    await create_test_post(db_session, tags=["beach"], title="Beach")
    await create_test_post(db_session, tags=["city"], title="City")
    await db_session.commit()

    repo = _repo(db_session)
    posts, total = await repo.search_posts_by_tags(["hiking", "beach"])

    assert total == 2


@pytest.mark.integration
async def test_search_posts_by_tags_is_case_insensitive(db_session):
    """search_posts_by_tags() matches tags case-insensitively."""
    await create_test_post(db_session, tags=["HIKING"], title="Case test")
    await db_session.commit()

    repo = _repo(db_session)
    posts, total = await repo.search_posts_by_tags(["hiking"])

    assert total == 1


# ---------------------------------------------------------------------------
# add_media / remove_media
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_add_media_attaches_media_to_post(db_session):
    """add_media() creates a PostMedia row linked to the post."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    media = await repo.add_media(
        post_id=post.id,
        media_url="https://cdn.example.com/image.jpg",
        object_key="posts/image.jpg",
        display_order=0,
        alt_text="A mountain trail",
    )

    assert media is not None
    assert media.post_id == post.id
    assert media.media_url == "https://cdn.example.com/image.jpg"
    assert media.alt_text == "A mountain trail"


@pytest.mark.integration
async def test_add_media_returns_none_for_missing_post(db_session):
    """add_media() returns None when the post does not exist."""
    repo = _repo(db_session)

    result = await repo.add_media(
        post_id=uuid.uuid4(),
        media_url="https://cdn.example.com/image.jpg",
        object_key="posts/image.jpg",
    )

    assert result is None


@pytest.mark.integration
async def test_remove_media_deletes_media_row(db_session):
    """remove_media() deletes the media record and returns True."""
    post = await create_test_post(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    media = await repo.add_media(
        post_id=post.id,
        media_url="https://cdn.example.com/del.jpg",
        object_key="posts/del.jpg",
    )

    result = await repo.remove_media(post_id=post.id, media_id=media.id)

    assert result is True


@pytest.mark.integration
async def test_remove_media_returns_false_for_wrong_post(db_session):
    """remove_media() returns False when media_id doesn't belong to post_id."""
    p1 = await create_test_post(db_session, title="Post 1")
    p2 = await create_test_post(db_session, title="Post 2")
    await db_session.commit()
    repo = _repo(db_session)

    media = await repo.add_media(
        post_id=p1.id,
        media_url="https://cdn.example.com/img.jpg",
        object_key="posts/img.jpg",
    )

    # Try to remove p1's media using p2 as the post
    result = await repo.remove_media(post_id=p2.id, media_id=media.id)

    assert result is False
