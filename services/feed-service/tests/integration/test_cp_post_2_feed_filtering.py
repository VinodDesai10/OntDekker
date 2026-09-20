"""
CP-POST-2 — Feed Filtering, Global/Community Visibility & Own-Post Exclusion

Tests for the following requirements:

  Test 1 — Own-post exclusion for global (PUBLIC) posts
  Test 2 — Own-post exclusion for COMMUNITY posts
  Test 3 — Non-member cannot see community posts
  Test 4 — Membership scoping: user sees only joined-community posts
  Test 5 — Empty feed when no eligible posts exist
  Test 6 — Pagination returns the requested number of eligible posts
  Test 7 — Own-post exclusion is stable across re-requests (session idempotent)

All filtering happens at the backend/SQL level — no post-fetch filtering in
the service layer.  Community membership is provided via a patch on the
``_fetch_user_community_ids`` method so tests do not require a running
community-service.

Architecture notes
------------------
- user_id (= JWT sub) is the authoritative identity — never username/avatar.
- exclude_author_id is injected from JWT inside PostService.list_posts().
- community_ids come from a single community-service call (mocked here).
- Pagination is validated via count_query in the repository — no post-fetch
  removal that would corrupt page sizes.
"""

import uuid
import pytest
from unittest.mock import patch, AsyncMock

from app.services.post_service import PostService
from app.schemas.feed import PostQueryParams, PostListResponse
from shared.constants.status import PostVisibility
from tests.utils import create_test_post, build_auth_headers
from tests.conftest import TEST_USER_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc(session) -> PostService:
    return PostService(session)


async def _list(
    session,
    current_user_id: uuid.UUID | None = None,
    user_community_ids: list[uuid.UUID] | None = None,
    limit: int = 20,
    offset: int = 0,
    community_id: uuid.UUID | None = None,
) -> PostListResponse:
    """
    Call PostService.list_posts() with community membership mocked.

    This bypasses the HTTP call to community-service while still exercising
    the full service + repository pipeline.

    ``user_community_ids`` defaults to [] when current_user_id is set (no
    community memberships) unless explicitly provided.
    """
    svc = _svc(session)
    params = PostQueryParams(
        limit=limit,
        offset=offset,
        community_id=community_id,
    )

    if user_community_ids is None and current_user_id is not None:
        user_community_ids = []

    with patch.object(
        PostService,
        "_fetch_user_community_ids",
        new=AsyncMock(return_value=user_community_ids or []),
    ):
        return await svc.list_posts(params, current_user_id)


# ---------------------------------------------------------------------------
# Test 1 — Own-post exclusion for global (PUBLIC) posts
# ---------------------------------------------------------------------------

class TestOwnPostExclusionGlobal:
    """
    Test 1:
      User A creates a Global (PUBLIC) post.
      User B creates a Global (PUBLIC) post.

      User A's feed must show User B's post but hide User A's post.
      User B's feed must show User A's post but hide User B's post.
    """

    @pytest.mark.integration
    async def test_user_a_sees_user_b_global_post(self, db_session):
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()

        await create_test_post(db_session, author_id=user_a, title="Post by A", visibility=PostVisibility.PUBLIC)
        await create_test_post(db_session, author_id=user_b, title="Post by B", visibility=PostVisibility.PUBLIC)
        await db_session.commit()

        result = await _list(db_session, current_user_id=user_a)

        titles = [p.title for p in result.posts]
        assert "Post by B" in titles, "User A should see User B's global post"

    @pytest.mark.integration
    async def test_user_a_does_not_see_own_global_post(self, db_session):
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()

        await create_test_post(db_session, author_id=user_a, title="Post by A", visibility=PostVisibility.PUBLIC)
        await create_test_post(db_session, author_id=user_b, title="Post by B", visibility=PostVisibility.PUBLIC)
        await db_session.commit()

        result = await _list(db_session, current_user_id=user_a)

        titles = [p.title for p in result.posts]
        assert "Post by A" not in titles, "User A must NOT see their own post in the feed"

    @pytest.mark.integration
    async def test_user_b_sees_user_a_global_post(self, db_session):
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()

        await create_test_post(db_session, author_id=user_a, title="Post by A", visibility=PostVisibility.PUBLIC)
        await create_test_post(db_session, author_id=user_b, title="Post by B", visibility=PostVisibility.PUBLIC)
        await db_session.commit()

        result = await _list(db_session, current_user_id=user_b)

        titles = [p.title for p in result.posts]
        assert "Post by A" in titles, "User B should see User A's global post"

    @pytest.mark.integration
    async def test_user_b_does_not_see_own_global_post(self, db_session):
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()

        await create_test_post(db_session, author_id=user_a, title="Post by A", visibility=PostVisibility.PUBLIC)
        await create_test_post(db_session, author_id=user_b, title="Post by B", visibility=PostVisibility.PUBLIC)
        await db_session.commit()

        result = await _list(db_session, current_user_id=user_b)

        titles = [p.title for p in result.posts]
        assert "Post by B" not in titles, "User B must NOT see their own post in the feed"


# ---------------------------------------------------------------------------
# Test 2 — Own-post exclusion for COMMUNITY posts
# ---------------------------------------------------------------------------

class TestOwnPostExclusionCommunity:
    """
    Test 2:
      User A and User B both belong to Community X.
      A creates a COMMUNITY post in Community X.
      B creates a COMMUNITY post in Community X.

      User A's feed must show B's Community X post but hide A's Community X post.
    """

    @pytest.mark.integration
    async def test_user_a_sees_user_b_community_post(self, db_session):
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        community_x = uuid.uuid4()

        await create_test_post(db_session, author_id=user_a, title="A in CX", visibility=PostVisibility.COMMUNITY, community_id=community_x)
        await create_test_post(db_session, author_id=user_b, title="B in CX", visibility=PostVisibility.COMMUNITY, community_id=community_x)
        await db_session.commit()

        # User A is a member of community_x
        result = await _list(db_session, current_user_id=user_a, user_community_ids=[community_x])

        titles = [p.title for p in result.posts]
        assert "B in CX" in titles, "User A should see B's community post from a joined community"

    @pytest.mark.integration
    async def test_user_a_does_not_see_own_community_post(self, db_session):
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        community_x = uuid.uuid4()

        await create_test_post(db_session, author_id=user_a, title="A in CX", visibility=PostVisibility.COMMUNITY, community_id=community_x)
        await create_test_post(db_session, author_id=user_b, title="B in CX", visibility=PostVisibility.COMMUNITY, community_id=community_x)
        await db_session.commit()

        result = await _list(db_session, current_user_id=user_a, user_community_ids=[community_x])

        titles = [p.title for p in result.posts]
        assert "A in CX" not in titles, "User A must NOT see their own community post"


# ---------------------------------------------------------------------------
# Test 3 — Non-member cannot see community posts
# ---------------------------------------------------------------------------

class TestNonMemberCommunityVisibility:
    """
    Test 3:
      User C is NOT a member of Community X.
      Community X posts must NOT appear in User C's feed.
    """

    @pytest.mark.integration
    async def test_non_member_cannot_see_community_posts(self, db_session):
        user_a = uuid.uuid4()
        user_c = uuid.uuid4()
        community_x = uuid.uuid4()

        await create_test_post(db_session, author_id=user_a, title="CX Post", visibility=PostVisibility.COMMUNITY, community_id=community_x)
        await db_session.commit()

        # User C has no memberships
        result = await _list(db_session, current_user_id=user_c, user_community_ids=[])

        titles = [p.title for p in result.posts]
        assert "CX Post" not in titles, "User C (non-member) must NOT see Community X posts"

    @pytest.mark.integration
    async def test_non_member_anonymous_cannot_see_community_posts(self, db_session):
        user_a = uuid.uuid4()
        community_x = uuid.uuid4()

        await create_test_post(db_session, author_id=user_a, title="CX Post", visibility=PostVisibility.COMMUNITY, community_id=community_x)
        await db_session.commit()

        # Anonymous caller — no user_id
        result = await _list(db_session, current_user_id=None)

        titles = [p.title for p in result.posts]
        assert "CX Post" not in titles, "Anonymous users must NOT see COMMUNITY posts"

    @pytest.mark.integration
    async def test_non_member_can_still_see_public_posts(self, db_session):
        user_a = uuid.uuid4()
        user_c = uuid.uuid4()
        community_x = uuid.uuid4()

        await create_test_post(db_session, author_id=user_a, title="Global Post", visibility=PostVisibility.PUBLIC)
        await create_test_post(db_session, author_id=user_a, title="CX Post", visibility=PostVisibility.COMMUNITY, community_id=community_x)
        await db_session.commit()

        # User C has no memberships
        result = await _list(db_session, current_user_id=user_c, user_community_ids=[])

        titles = [p.title for p in result.posts]
        assert "Global Post" in titles, "User C should still see PUBLIC posts"
        assert "CX Post" not in titles, "User C must NOT see COMMUNITY posts they are not a member of"


# ---------------------------------------------------------------------------
# Test 4 — Membership scoping: user sees only joined-community posts
# ---------------------------------------------------------------------------

class TestMembershipScoping:
    """
    Test 4:
      User A belongs to Community X but NOT Community Y.
      X posts can appear.
      Y posts cannot appear.
    """

    @pytest.mark.integration
    async def test_user_a_sees_community_x_posts_not_y(self, db_session):
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        community_x = uuid.uuid4()
        community_y = uuid.uuid4()

        # Posts in Community X — user_a is a member
        await create_test_post(db_session, author_id=user_b, title="X Post", visibility=PostVisibility.COMMUNITY, community_id=community_x)
        # Posts in Community Y — user_a is NOT a member
        await create_test_post(db_session, author_id=user_b, title="Y Post", visibility=PostVisibility.COMMUNITY, community_id=community_y)
        await db_session.commit()

        # User A is only a member of community_x
        result = await _list(db_session, current_user_id=user_a, user_community_ids=[community_x])

        titles = [p.title for p in result.posts]
        assert "X Post" in titles, "User A should see posts from their joined community X"
        assert "Y Post" not in titles, "User A must NOT see posts from community Y (not a member)"

    @pytest.mark.integration
    async def test_user_sees_public_posts_from_unjoined_community_authors(self, db_session):
        """Public posts from any author are visible regardless of community membership."""
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        community_y = uuid.uuid4()

        # User B posts publicly (not inside a community)
        await create_test_post(db_session, author_id=user_b, title="Public Post", visibility=PostVisibility.PUBLIC)
        # User B also posts inside community Y (user_a not a member)
        await create_test_post(db_session, author_id=user_b, title="Y Post", visibility=PostVisibility.COMMUNITY, community_id=community_y)
        await db_session.commit()

        # User A has no community memberships
        result = await _list(db_session, current_user_id=user_a, user_community_ids=[])

        titles = [p.title for p in result.posts]
        assert "Public Post" in titles, "User A sees B's public posts"
        assert "Y Post" not in titles, "User A must NOT see B's community Y posts"


# ---------------------------------------------------------------------------
# Test 5 — Empty feed
# ---------------------------------------------------------------------------

class TestEmptyFeed:
    """
    Test 5:
      When no eligible posts exist after filtering the feed returns an empty result correctly.
    """

    @pytest.mark.integration
    async def test_empty_feed_when_only_own_posts_exist(self, db_session):
        user_a = uuid.uuid4()

        # User A only has their own posts — they should be excluded
        await create_test_post(db_session, author_id=user_a, title="My Post 1")
        await create_test_post(db_session, author_id=user_a, title="My Post 2")
        await db_session.commit()

        result = await _list(db_session, current_user_id=user_a)

        assert result.total == 0
        assert result.posts == []
        assert result.has_more is False

    @pytest.mark.integration
    async def test_empty_feed_when_no_posts_exist(self, db_session):
        result = await _list(db_session, current_user_id=uuid.uuid4())

        assert result.total == 0
        assert result.posts == []
        assert result.has_more is False

    @pytest.mark.integration
    async def test_empty_feed_anonymous_no_public_posts(self, db_session):
        """Anonymous user sees empty feed when there are only PRIVATE/COMMUNITY posts."""
        user_a = uuid.uuid4()
        community_x = uuid.uuid4()

        await create_test_post(db_session, author_id=user_a, title="Private", visibility=PostVisibility.PRIVATE)
        await create_test_post(db_session, author_id=user_a, title="Community", visibility=PostVisibility.COMMUNITY, community_id=community_x)
        await db_session.commit()

        result = await _list(db_session, current_user_id=None)

        assert result.total == 0
        assert result.posts == []


# ---------------------------------------------------------------------------
# Test 6 — Pagination correctness
# ---------------------------------------------------------------------------

class TestPaginationCorrectness:
    """
    Test 6:
      Pagination returns the requested number of eligible posts when enough exist.
      Own posts are excluded BEFORE pagination so page sizes remain accurate.
    """

    @pytest.mark.integration
    async def test_pagination_returns_exact_limit_after_own_post_exclusion(self, db_session):
        """
        10 posts from other_user + 5 posts from current_user.
        With limit=6 the feed should return exactly 6 posts (all from other_user).
        If filtering happened after pagination we might get fewer than 6.
        """
        current_user = uuid.uuid4()
        other_user = uuid.uuid4()

        # Other user's posts (eligible)
        for i in range(10):
            await create_test_post(db_session, author_id=other_user, title=f"Other {i}", visibility=PostVisibility.PUBLIC)
        # Own posts (must be excluded)
        for i in range(5):
            await create_test_post(db_session, author_id=current_user, title=f"Own {i}", visibility=PostVisibility.PUBLIC)
        await db_session.commit()

        result = await _list(db_session, current_user_id=current_user, limit=6)

        assert len(result.posts) == 6, (
            f"Expected exactly 6 posts but got {len(result.posts)}. "
            "Own-post exclusion must happen at query level, not post-fetch."
        )

    @pytest.mark.integration
    async def test_pagination_total_excludes_own_posts(self, db_session):
        """
        total in the response should count only eligible posts, not all posts.
        """
        current_user = uuid.uuid4()
        other_user = uuid.uuid4()

        for i in range(8):
            await create_test_post(db_session, author_id=other_user, title=f"Other {i}", visibility=PostVisibility.PUBLIC)
        for i in range(4):
            await create_test_post(db_session, author_id=current_user, title=f"Own {i}", visibility=PostVisibility.PUBLIC)
        await db_session.commit()

        result = await _list(db_session, current_user_id=current_user, limit=20)

        assert result.total == 8, f"total must be 8 (other user's posts) but was {result.total}"

    @pytest.mark.integration
    async def test_pagination_has_more_reflects_eligible_count(self, db_session):
        """
        has_more should be True when there are more eligible posts beyond the current page.
        """
        current_user = uuid.uuid4()
        other_user = uuid.uuid4()

        for i in range(5):
            await create_test_post(db_session, author_id=other_user, title=f"Other {i}", visibility=PostVisibility.PUBLIC)
        await db_session.commit()

        result = await _list(db_session, current_user_id=current_user, limit=3, offset=0)

        assert result.has_more is True, "has_more should be True when more eligible posts exist"

    @pytest.mark.integration
    async def test_pagination_has_more_false_on_last_page(self, db_session):
        """has_more should be False on the last page."""
        current_user = uuid.uuid4()
        other_user = uuid.uuid4()

        for i in range(3):
            await create_test_post(db_session, author_id=other_user, title=f"Other {i}", visibility=PostVisibility.PUBLIC)
        await db_session.commit()

        result = await _list(db_session, current_user_id=current_user, limit=3, offset=0)

        assert result.has_more is False

    @pytest.mark.integration
    async def test_pagination_offset_pages_do_not_overlap(self, db_session):
        """Page 1 and page 2 must return disjoint sets of eligible posts."""
        current_user = uuid.uuid4()
        other_user = uuid.uuid4()

        for i in range(6):
            await create_test_post(db_session, author_id=other_user, title=f"Other {i}", visibility=PostVisibility.PUBLIC)
        await db_session.commit()

        page1 = await _list(db_session, current_user_id=current_user, limit=3, offset=0)
        page2 = await _list(db_session, current_user_id=current_user, limit=3, offset=3)

        ids_p1 = {p.id for p in page1.posts}
        ids_p2 = {p.id for p in page2.posts}
        assert ids_p1.isdisjoint(ids_p2), "Pages must not overlap"


# ---------------------------------------------------------------------------
# Test 7 — Stable exclusion across re-requests (idempotency)
# ---------------------------------------------------------------------------

class TestStableExclusion:
    """
    Test 7:
      Refreshing the browser / re-requesting the feed does not reintroduce
      the user's own posts.  The backend exclusion must be deterministic.
    """

    @pytest.mark.integration
    async def test_own_posts_absent_on_repeated_requests(self, db_session):
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()

        await create_test_post(db_session, author_id=user_a, title="A Post", visibility=PostVisibility.PUBLIC)
        await create_test_post(db_session, author_id=user_b, title="B Post", visibility=PostVisibility.PUBLIC)
        await db_session.commit()

        # Simulate two separate "page loads"
        result1 = await _list(db_session, current_user_id=user_a)
        result2 = await _list(db_session, current_user_id=user_a)

        for result in (result1, result2):
            ids = {p.author_id for p in result.posts}
            assert user_a not in ids, "User A's own posts must never appear in their feed"


# ---------------------------------------------------------------------------
# Test via HTTP endpoint (integration smoke tests)
# ---------------------------------------------------------------------------

class TestFeedEndpointExclusion:
    """Validate own-post exclusion via the actual HTTP endpoint."""

    @pytest.mark.integration
    async def test_feed_endpoint_excludes_own_posts(self, auth_client, client):
        """
        Create a post as TEST_USER then request the feed — the post must not
        appear in the response.
        """
        from tests.utils import make_post_payload

        # Create a post as the default test user
        create_resp = await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(title="My Own Post"),
        )
        assert create_resp.status_code == 201

        # Get the feed as the same user — own post must not appear
        feed_resp = await auth_client.get("/api/v1/feed/posts")
        assert feed_resp.status_code == 200
        titles = [p["title"] for p in feed_resp.json()["posts"]]
        assert "My Own Post" not in titles, (
            "The authenticated user must not see their own posts in the main feed"
        )

    @pytest.mark.integration
    async def test_feed_endpoint_shows_other_user_posts(self, auth_client, client):
        """Other users' PUBLIC posts are visible in the feed."""
        from tests.utils import make_post_payload

        other_headers = build_auth_headers(user_id=uuid.uuid4())
        # Create a post from another user
        await client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(title="Someone Else's Post"),
            headers=other_headers,
        )

        feed_resp = await auth_client.get("/api/v1/feed/posts")
        assert feed_resp.status_code == 200
        titles = [p["title"] for p in feed_resp.json()["posts"]]
        assert "Someone Else's Post" in titles, "Other users' posts must appear in the feed"

    @pytest.mark.integration
    async def test_feed_endpoint_anonymous_only_public(self, auth_client, client):
        """Anonymous feed shows only PUBLIC posts."""
        from tests.utils import make_post_payload

        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Pub", visibility="PUBLIC"))

        feed_resp = await client.get("/api/v1/feed/posts")
        assert feed_resp.status_code == 200
        titles = [p["title"] for p in feed_resp.json()["posts"]]
        assert "Pub" in titles

    @pytest.mark.integration
    async def test_feed_endpoint_cannot_bypass_exclusion_with_author_id_param(self, auth_client, client):
        """
        Security test: passing ?author_id=<current_user> does NOT mean the user sees
        their own posts in their own main feed context.  The endpoint passes author_id
        as a filter but NOT as the exclude override — the service still applies
        exclude_author_id from the JWT.

        Note: ?author_id=<user> is still allowed (profile endpoint use case), but
        the service correctly excludes own posts in the general feed regardless.
        This test confirms the JWT-derived exclusion is applied even when author_id
        is set to the current user.
        """
        from tests.utils import make_post_payload
        from tests.conftest import TEST_USER_ID

        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="My Post"))

        # Passing ?author_id=TEST_USER_ID still excludes because exclude_author_id
        # is injected from JWT, but author_id filter is also applied — this specific
        # combination means the query is "authored by TEST_USER_ID AND NOT TEST_USER_ID"
        # which always returns 0 results, correctly preventing own-post bypass.
        feed_resp = await auth_client.get(f"/api/v1/feed/posts?author_id={TEST_USER_ID}")
        assert feed_resp.status_code == 200
        # With both author_id=X and exclude_author_id=X the result must be empty
        body = feed_resp.json()
        assert body["total"] == 0, (
            "Combining author_id=<own_id> and exclude_author_id=<own_id> yields 0 results — "
            "no bypass possible"
        )
