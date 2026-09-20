"""
CP-16C — PostService Integration Tests

Validates service-layer behaviour for PostService.
All tests use an in-memory SQLite database via the db_session fixture.
Repository internals are NOT the focus — service orchestration, validation,
authorization, and error handling are.
"""

import uuid
import pytest

from app.services.post_service import PostService
from app.schemas.feed import (
    PostCreateRequest,
    PostUpdateRequest,
    PostQueryParams,
    ShareRequest,
    PostSchema,
    PostSummarySchema,
    PostListResponse,
    LikeActionResponse,
    BookmarkActionResponse,
    ShareActionResponse,
    BookmarkListResponse,
)
from shared.constants.status import PostStatus, PostVisibility
from shared.exceptions import NotFoundError, ForbiddenError, ValidationError
from tests.utils import create_test_post


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc(session) -> PostService:
    return PostService(session)


# ---------------------------------------------------------------------------
# create_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_create_post_returns_post_schema(db_session):
    """create_post() returns a PostSchema with the correct fields."""
    author_id = uuid.uuid4()
    svc = _svc(db_session)
    req = PostCreateRequest(title="My Travel Post", content="Great trip!")

    result = await svc.create_post(req, author_id)

    assert isinstance(result, PostSchema)
    assert result.title == "My Travel Post"
    assert result.content == "Great trip!"
    assert result.author_id == author_id


@pytest.mark.integration
async def test_create_post_defaults_to_published_public(db_session):
    """create_post() defaults to PUBLISHED status and PUBLIC visibility."""
    svc = _svc(db_session)
    req = PostCreateRequest(title="Default post")

    result = await svc.create_post(req, uuid.uuid4())

    assert result.status == PostStatus.PUBLISHED
    assert result.visibility == PostVisibility.PUBLIC


@pytest.mark.integration
async def test_create_post_stores_tags(db_session):
    """create_post() persists tags and exposes them on the returned schema."""
    svc = _svc(db_session)
    req = PostCreateRequest(title="Tagged", tags=["hiking", "nature"])

    result = await svc.create_post(req, uuid.uuid4())

    tag_values = {t.tag for t in result.tags}
    assert "hiking" in tag_values
    assert "nature" in tag_values


@pytest.mark.integration
async def test_create_post_raises_validation_error_for_community_private(db_session):
    """create_post() raises ValidationError when community_id + PRIVATE visibility."""
    svc = _svc(db_session)
    req = PostCreateRequest(
        title="Bad combo",
        community_id=uuid.uuid4(),
        visibility=PostVisibility.PRIVATE,
    )

    with pytest.raises(ValidationError):
        await svc.create_post(req, uuid.uuid4())


@pytest.mark.integration
async def test_create_post_raises_validation_error_for_public_with_community_id(db_session):
    """create_post() raises ValidationError when PUBLIC visibility + community_id is set."""
    svc = _svc(db_session)
    req = PostCreateRequest(
        title="Bad PUBLIC combo",
        community_id=uuid.uuid4(),
        visibility=PostVisibility.PUBLIC,
    )

    with pytest.raises(ValidationError):
        await svc.create_post(req, uuid.uuid4())


@pytest.mark.integration
async def test_create_post_raises_validation_error_for_community_without_community_id(db_session):
    """create_post() raises ValidationError when COMMUNITY visibility + no community_id."""
    svc = _svc(db_session)
    req = PostCreateRequest(
        title="No community given",
        community_id=None,
        visibility=PostVisibility.COMMUNITY,
    )

    with pytest.raises(ValidationError):
        await svc.create_post(req, uuid.uuid4())


@pytest.mark.integration
async def test_create_post_interaction_counts_start_at_zero(db_session):
    """Newly created post has like_count, share_count, comment_count all zero."""
    svc = _svc(db_session)
    req = PostCreateRequest(title="Fresh post")

    result = await svc.create_post(req, uuid.uuid4())

    assert result.like_count == 0
    assert result.share_count == 0
    assert result.comment_count == 0


@pytest.mark.integration
async def test_create_post_is_liked_false_for_author(db_session):
    """is_liked and is_bookmarked are False for a brand-new post."""
    author_id = uuid.uuid4()
    svc = _svc(db_session)
    req = PostCreateRequest(title="New post")

    result = await svc.create_post(req, author_id)

    assert result.is_liked is False
    assert result.is_bookmarked is False


# ---------------------------------------------------------------------------
# get_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_post_returns_post_schema(db_session):
    """get_post() returns a PostSchema for an existing post."""
    post = await create_test_post(db_session, title="Findable")
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.get_post(post.id)

    assert isinstance(result, PostSchema)
    assert result.id == post.id
    assert result.title == "Findable"


@pytest.mark.integration
async def test_get_post_raises_not_found_for_missing_id(db_session):
    """get_post() raises NotFoundError when the post does not exist."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.get_post(uuid.uuid4())


@pytest.mark.integration
async def test_get_post_public_visible_to_anonymous(db_session):
    """get_post() returns a PUBLIC post to an unauthenticated caller (no user_id)."""
    post = await create_test_post(db_session, visibility=PostVisibility.PUBLIC)
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.get_post(post.id, current_user_id=None)

    assert result.id == post.id


@pytest.mark.integration
async def test_get_post_private_raises_forbidden_for_other_user(db_session):
    """get_post() raises ForbiddenError when a non-author tries to view a PRIVATE post."""
    author_id = uuid.uuid4()
    post = await create_test_post(db_session, author_id=author_id, visibility=PostVisibility.PRIVATE)
    await db_session.commit()
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.get_post(post.id, current_user_id=uuid.uuid4())


@pytest.mark.integration
async def test_get_post_private_visible_to_author(db_session):
    """get_post() returns a PRIVATE post to its author."""
    author_id = uuid.uuid4()
    post = await create_test_post(db_session, author_id=author_id, visibility=PostVisibility.PRIVATE)
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.get_post(post.id, current_user_id=author_id)

    assert result.id == post.id


@pytest.mark.integration
async def test_get_post_private_raises_forbidden_for_anonymous(db_session):
    """get_post() raises ForbiddenError when an anonymous user tries to view a PRIVATE post."""
    post = await create_test_post(db_session, visibility=PostVisibility.PRIVATE)
    await db_session.commit()
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.get_post(post.id, current_user_id=None)


@pytest.mark.integration
async def test_get_post_enriches_is_liked_flag(db_session):
    """get_post() sets is_liked=True when the current user has liked the post."""
    author_id = uuid.uuid4()
    user_id = uuid.uuid4()
    post = await create_test_post(db_session, author_id=author_id)
    await db_session.commit()

    svc = _svc(db_session)
    await svc.like_post(post.id, user_id)

    result = await svc.get_post(post.id, current_user_id=user_id)

    assert result.is_liked is True


# ---------------------------------------------------------------------------
# update_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_update_post_changes_title(db_session):
    """update_post() changes the title and returns updated PostSchema."""
    author_id = uuid.uuid4()
    post = await create_test_post(db_session, author_id=author_id, title="Old title")
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.update_post(
        post.id,
        PostUpdateRequest(title="New title"),
        author_id,
    )

    assert result.title == "New title"


@pytest.mark.integration
async def test_update_post_raises_not_found_for_missing_post(db_session):
    """update_post() raises NotFoundError when the post does not exist."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.update_post(uuid.uuid4(), PostUpdateRequest(title="Ghost"), uuid.uuid4())


@pytest.mark.integration
async def test_update_post_raises_forbidden_for_non_author(db_session):
    """update_post() raises ForbiddenError when a non-author tries to edit."""
    post = await create_test_post(db_session, author_id=uuid.uuid4())
    await db_session.commit()
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.update_post(post.id, PostUpdateRequest(title="Hack"), uuid.uuid4())


@pytest.mark.integration
async def test_update_post_raises_validation_error_community_private(db_session):
    """update_post() raises ValidationError when setting PRIVATE on a community post."""
    author_id = uuid.uuid4()
    community_id = uuid.uuid4()
    post = await create_test_post(
        db_session, author_id=author_id,
        community_id=community_id,
        visibility=PostVisibility.PUBLIC,
    )
    await db_session.commit()
    svc = _svc(db_session)

    with pytest.raises(ValidationError):
        await svc.update_post(
            post.id,
            PostUpdateRequest(visibility=PostVisibility.PRIVATE),
            author_id,
        )


@pytest.mark.integration
async def test_update_post_partial_fields_only_changes_specified(db_session):
    """update_post() with a partial request only changes the specified fields."""
    author_id = uuid.uuid4()
    post = await create_test_post(
        db_session, author_id=author_id,
        title="Unchanged title",
        location="Amsterdam",
    )
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.update_post(
        post.id,
        PostUpdateRequest(location="Berlin"),
        author_id,
    )

    assert result.title == "Unchanged title"
    assert result.location == "Berlin"


# ---------------------------------------------------------------------------
# delete_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_delete_post_returns_true(db_session):
    """delete_post() returns True on successful deletion."""
    author_id = uuid.uuid4()
    post = await create_test_post(db_session, author_id=author_id)
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.delete_post(post.id, author_id)

    assert result is True


@pytest.mark.integration
async def test_delete_post_soft_deletes_post(db_session):
    """delete_post() soft-deletes so the post is no longer retrievable via get_post."""
    author_id = uuid.uuid4()
    post = await create_test_post(db_session, author_id=author_id)
    await db_session.commit()
    svc = _svc(db_session)

    await svc.delete_post(post.id, author_id)

    with pytest.raises(NotFoundError):
        await svc.get_post(post.id)


@pytest.mark.integration
async def test_delete_post_raises_not_found_for_missing_post(db_session):
    """delete_post() raises NotFoundError when the post does not exist."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.delete_post(uuid.uuid4(), uuid.uuid4())


@pytest.mark.integration
async def test_delete_post_raises_forbidden_for_non_author(db_session):
    """delete_post() raises ForbiddenError when a non-author tries to delete."""
    post = await create_test_post(db_session, author_id=uuid.uuid4())
    await db_session.commit()
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.delete_post(post.id, uuid.uuid4())


# ---------------------------------------------------------------------------
# list_posts
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_list_posts_returns_post_list_response(db_session):
    """list_posts() returns a PostListResponse."""
    await create_test_post(db_session, title="P1")
    await create_test_post(db_session, title="P2")
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.list_posts(PostQueryParams())

    assert isinstance(result, PostListResponse)
    assert result.total >= 2


@pytest.mark.integration
async def test_list_posts_excludes_private_posts_from_anonymous(db_session):
    """list_posts() does not return PRIVATE posts to unauthenticated callers."""
    await create_test_post(db_session, visibility=PostVisibility.PUBLIC, title="Public")
    await create_test_post(db_session, visibility=PostVisibility.PRIVATE, title="Private")
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.list_posts(PostQueryParams(), current_user_id=None)

    titles = [p.title for p in result.posts]
    assert "Public" in titles
    assert "Private" not in titles


@pytest.mark.integration
async def test_list_posts_respects_limit(db_session):
    """list_posts() respects the limit parameter."""
    for i in range(5):
        await create_test_post(db_session, title=f"Post {i}")
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.list_posts(PostQueryParams(limit=2))

    assert len(result.posts) == 2


@pytest.mark.integration
async def test_list_posts_has_more_flag(db_session):
    """list_posts() sets has_more=True when more results exist beyond the page."""
    for i in range(4):
        await create_test_post(db_session, title=f"Post {i}")
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.list_posts(PostQueryParams(limit=2, offset=0))

    assert result.has_more is True


@pytest.mark.integration
async def test_list_posts_author_filter(db_session):
    """list_posts() with author_id filter returns only that author's posts."""
    author_id = uuid.uuid4()
    await create_test_post(db_session, author_id=author_id, title="By author")
    await create_test_post(db_session, title="Other author")
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.list_posts(PostQueryParams(author_id=author_id))

    assert result.total == 1
    assert result.posts[0].title == "By author"


# ---------------------------------------------------------------------------
# get_posts_by_author
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_posts_by_author_returns_author_posts(db_session):
    """get_posts_by_author() returns a PostListResponse for the author."""
    author_id = uuid.uuid4()
    await create_test_post(db_session, author_id=author_id, title="Post A")
    await create_test_post(db_session, author_id=author_id, title="Post B")
    await create_test_post(db_session, title="Other")
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.get_posts_by_author(author_id)

    assert isinstance(result, PostListResponse)
    assert result.total == 2
    assert all(p.author_id == author_id for p in result.posts)


@pytest.mark.integration
async def test_get_posts_by_author_viewer_excludes_private(db_session):
    """get_posts_by_author() hides PRIVATE posts when viewed by another user."""
    author_id = uuid.uuid4()
    viewer_id = uuid.uuid4()
    await create_test_post(db_session, author_id=author_id, visibility=PostVisibility.PUBLIC, title="Public")
    await create_test_post(db_session, author_id=author_id, visibility=PostVisibility.PRIVATE, title="Private")
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.get_posts_by_author(author_id, current_user_id=viewer_id)

    titles = [p.title for p in result.posts]
    assert "Private" not in titles


@pytest.mark.integration
async def test_get_posts_by_author_owner_sees_all(db_session):
    """get_posts_by_author() returns all posts including PRIVATE when owner requests."""
    author_id = uuid.uuid4()
    await create_test_post(db_session, author_id=author_id, visibility=PostVisibility.PUBLIC, title="Public")
    await create_test_post(db_session, author_id=author_id, visibility=PostVisibility.PRIVATE, title="Private")
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.get_posts_by_author(author_id, current_user_id=author_id)

    assert result.total == 2


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
    svc = _svc(db_session)

    result = await svc.get_posts_by_community(community_id)

    assert isinstance(result, PostListResponse)
    assert result.total == 2


@pytest.mark.integration
async def test_get_posts_by_community_returns_post_summary_schemas(db_session):
    """get_posts_by_community() posts list contains PostSummarySchema items."""
    community_id = uuid.uuid4()
    await create_test_post(db_session, community_id=community_id)
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.get_posts_by_community(community_id)

    assert len(result.posts) == 1
    assert isinstance(result.posts[0], PostSummarySchema)


# ---------------------------------------------------------------------------
# like_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_like_post_returns_like_action_response(db_session):
    """like_post() returns a LikeActionResponse with is_liked=True."""
    post = await create_test_post(db_session)
    await db_session.commit()
    svc = _svc(db_session)
    user_id = uuid.uuid4()

    result = await svc.like_post(post.id, user_id)

    assert isinstance(result, LikeActionResponse)
    assert result.is_liked is True
    assert result.post_id == post.id


@pytest.mark.integration
async def test_like_post_increments_like_count(db_session):
    """like_post() increments the like_count in the response."""
    post = await create_test_post(db_session)
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.like_post(post.id, uuid.uuid4())

    assert result.like_count == 1


@pytest.mark.integration
async def test_like_post_raises_not_found_for_missing_post(db_session):
    """like_post() raises NotFoundError when the post does not exist."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.like_post(uuid.uuid4(), uuid.uuid4())


@pytest.mark.integration
async def test_like_post_raises_forbidden_for_private_post_non_owner(db_session):
    """like_post() raises ForbiddenError when user tries to like a PRIVATE post."""
    author_id = uuid.uuid4()
    post = await create_test_post(db_session, author_id=author_id, visibility=PostVisibility.PRIVATE)
    await db_session.commit()
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.like_post(post.id, uuid.uuid4())


# ---------------------------------------------------------------------------
# unlike_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_unlike_post_returns_like_action_response_with_is_liked_false(db_session):
    """unlike_post() returns LikeActionResponse with is_liked=False."""
    post = await create_test_post(db_session)
    await db_session.commit()
    svc = _svc(db_session)
    user_id = uuid.uuid4()

    await svc.like_post(post.id, user_id)
    result = await svc.unlike_post(post.id, user_id)

    assert isinstance(result, LikeActionResponse)
    assert result.is_liked is False
    assert result.post_id == post.id


@pytest.mark.integration
async def test_unlike_post_decrements_like_count(db_session):
    """unlike_post() decrements the like_count in the response."""
    post = await create_test_post(db_session)
    await db_session.commit()
    svc = _svc(db_session)
    user_id = uuid.uuid4()

    await svc.like_post(post.id, user_id)
    await svc.like_post(post.id, uuid.uuid4())
    result = await svc.unlike_post(post.id, user_id)

    assert result.like_count == 1


@pytest.mark.integration
async def test_unlike_post_on_non_liked_post_returns_zero_count(db_session):
    """unlike_post() on a post not liked by user returns like_count correctly."""
    post = await create_test_post(db_session)
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.unlike_post(post.id, uuid.uuid4())

    assert result.is_liked is False
    assert result.like_count == 0


# ---------------------------------------------------------------------------
# bookmark_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_bookmark_post_returns_bookmark_action_response(db_session):
    """bookmark_post() returns BookmarkActionResponse with is_bookmarked=True."""
    post = await create_test_post(db_session)
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.bookmark_post(post.id, uuid.uuid4())

    assert isinstance(result, BookmarkActionResponse)
    assert result.is_bookmarked is True
    assert result.post_id == post.id


@pytest.mark.integration
async def test_bookmark_post_raises_not_found_for_missing_post(db_session):
    """bookmark_post() raises NotFoundError when the post does not exist."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.bookmark_post(uuid.uuid4(), uuid.uuid4())


@pytest.mark.integration
async def test_bookmark_post_raises_forbidden_for_private_post(db_session):
    """bookmark_post() raises ForbiddenError for a PRIVATE post by a non-owner."""
    author_id = uuid.uuid4()
    post = await create_test_post(db_session, author_id=author_id, visibility=PostVisibility.PRIVATE)
    await db_session.commit()
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.bookmark_post(post.id, uuid.uuid4())


# ---------------------------------------------------------------------------
# unbookmark_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_unbookmark_post_returns_is_bookmarked_false(db_session):
    """unbookmark_post() returns BookmarkActionResponse with is_bookmarked=False."""
    post = await create_test_post(db_session)
    await db_session.commit()
    svc = _svc(db_session)
    user_id = uuid.uuid4()

    await svc.bookmark_post(post.id, user_id)
    result = await svc.unbookmark_post(post.id, user_id)

    assert isinstance(result, BookmarkActionResponse)
    assert result.is_bookmarked is False


@pytest.mark.integration
async def test_unbookmark_post_on_non_bookmarked_post(db_session):
    """unbookmark_post() on a post not bookmarked by user returns is_bookmarked=False."""
    post = await create_test_post(db_session)
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.unbookmark_post(post.id, uuid.uuid4())

    assert result.is_bookmarked is False


# ---------------------------------------------------------------------------
# share_post
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_share_post_returns_share_action_response(db_session):
    """share_post() returns ShareActionResponse with correct fields."""
    post = await create_test_post(db_session)
    await db_session.commit()
    svc = _svc(db_session)
    user_id = uuid.uuid4()

    result = await svc.share_post(post.id, user_id, ShareRequest(share_channel="twitter"))

    assert isinstance(result, ShareActionResponse)
    assert result.post_id == post.id
    assert result.share_count == 1
    assert result.share_id is not None


@pytest.mark.integration
async def test_share_post_increments_share_count(db_session):
    """share_post() increments the share count with each call."""
    post = await create_test_post(db_session)
    await db_session.commit()
    svc = _svc(db_session)

    await svc.share_post(post.id, uuid.uuid4(), ShareRequest())
    result = await svc.share_post(post.id, uuid.uuid4(), ShareRequest(share_channel="facebook"))

    assert result.share_count == 2


@pytest.mark.integration
async def test_share_post_raises_not_found_for_missing_post(db_session):
    """share_post() raises NotFoundError when the post does not exist."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.share_post(uuid.uuid4(), uuid.uuid4(), ShareRequest())


@pytest.mark.integration
async def test_share_post_raises_forbidden_for_private_post(db_session):
    """share_post() raises ForbiddenError for a PRIVATE post by a non-owner."""
    author_id = uuid.uuid4()
    post = await create_test_post(db_session, author_id=author_id, visibility=PostVisibility.PRIVATE)
    await db_session.commit()
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.share_post(post.id, uuid.uuid4(), ShareRequest())


# ---------------------------------------------------------------------------
# get_user_bookmarks
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_get_user_bookmarks_returns_bookmarked_posts(db_session):
    """get_user_bookmarks() returns posts the user has bookmarked."""
    p1 = await create_test_post(db_session, title="Bookmarked 1")
    p2 = await create_test_post(db_session, title="Bookmarked 2")
    await create_test_post(db_session, title="Not bookmarked")
    await db_session.commit()
    svc = _svc(db_session)
    user_id = uuid.uuid4()

    await svc.bookmark_post(p1.id, user_id)
    await svc.bookmark_post(p2.id, user_id)

    result = await svc.get_user_bookmarks(user_id)

    assert isinstance(result, BookmarkListResponse)
    assert result.total == 2
    ids = {p.id for p in result.bookmarks}
    assert p1.id in ids
    assert p2.id in ids


@pytest.mark.integration
async def test_get_user_bookmarks_returns_empty_when_no_bookmarks(db_session):
    """get_user_bookmarks() returns empty list for user with no bookmarks."""
    svc = _svc(db_session)

    result = await svc.get_user_bookmarks(uuid.uuid4())

    assert isinstance(result, BookmarkListResponse)
    assert result.total == 0
    assert len(result.bookmarks) == 0


@pytest.mark.integration
async def test_get_user_bookmarks_respects_pagination(db_session):
    """get_user_bookmarks() respects limit and offset."""
    posts = []
    for i in range(4):
        p = await create_test_post(db_session, title=f"BK{i}")
        posts.append(p)
    await db_session.commit()
    svc = _svc(db_session)
    user_id = uuid.uuid4()

    for p in posts:
        await svc.bookmark_post(p.id, user_id)

    result = await svc.get_user_bookmarks(user_id, limit=2, offset=0)

    assert result.total == 4
    assert len(result.bookmarks) == 2


# ---------------------------------------------------------------------------
# Visibility helper (_can_user_view_post via get_post)
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_community_post_visible_to_authenticated_user(db_session):
    """COMMUNITY visibility posts are accessible to any authenticated user."""
    post = await create_test_post(db_session, visibility=PostVisibility.COMMUNITY)
    await db_session.commit()
    svc = _svc(db_session)

    result = await svc.get_post(post.id, current_user_id=uuid.uuid4())

    assert result.id == post.id


@pytest.mark.integration
async def test_community_post_forbidden_to_anonymous(db_session):
    """COMMUNITY visibility posts are not accessible to anonymous users."""
    post = await create_test_post(db_session, visibility=PostVisibility.COMMUNITY)
    await db_session.commit()
    svc = _svc(db_session)

    with pytest.raises(ForbiddenError):
        await svc.get_post(post.id, current_user_id=None)
