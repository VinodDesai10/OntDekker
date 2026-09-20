"""
CP-16D — Interaction Endpoint Tests

Validates HTTP contract for all Interaction-related endpoints in the Feed
Service. Focus: status codes, response shape, auth enforcement, error
responses, and idempotency behaviour.

Endpoints covered
-----------------
  POST   /api/v1/feed/posts/{post_id}/like
  DELETE /api/v1/feed/posts/{post_id}/like
  POST   /api/v1/feed/posts/{post_id}/bookmark
  DELETE /api/v1/feed/posts/{post_id}/bookmark
  GET    /api/v1/feed/me/bookmarks
  POST   /api/v1/feed/posts/{post_id}/share
"""

import uuid
import pytest

from tests.conftest import TEST_USER_ID
from tests.utils import create_test_post, build_auth_headers, make_share_payload
from shared.constants.status import PostVisibility


# ---------------------------------------------------------------------------
# POST /api/v1/feed/posts/{post_id}/like
# ---------------------------------------------------------------------------

class TestLikePost:
    """POST /api/v1/feed/posts/{post_id}/like"""

    @pytest.mark.integration
    async def test_like_post_returns_200(self, auth_client, db_session):
        """Authenticated like returns HTTP 200."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.post(f"/api/v1/feed/posts/{post.id}/like")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_like_post_response_schema(self, auth_client, db_session):
        """Response contains post_id, is_liked, like_count."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.post(f"/api/v1/feed/posts/{post.id}/like")
        body = resp.json()
        assert body["post_id"] == str(post.id)
        assert body["is_liked"] is True
        assert "like_count" in body
        assert body["like_count"] == 1

    @pytest.mark.integration
    async def test_like_post_requires_authentication(self, client, db_session):
        """Unauthenticated like returns HTTP 401."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await client.post(f"/api/v1/feed/posts/{post.id}/like")
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_like_post_not_found_returns_404(self, auth_client):
        """Liking a non-existent post returns HTTP 404."""
        resp = await auth_client.post(f"/api/v1/feed/posts/{uuid.uuid4()}/like")
        assert resp.status_code == 404

    @pytest.mark.integration
    async def test_like_private_post_non_owner_returns_403(
        self, client, db_session
    ):
        """Liking a PRIVATE post as a non-owner returns HTTP 403."""
        post = await create_test_post(
            db_session, author_id=uuid.uuid4(), visibility=PostVisibility.PRIVATE
        )
        await db_session.commit()
        other_headers = build_auth_headers(user_id=uuid.uuid4())

        resp = await client.post(
            f"/api/v1/feed/posts/{post.id}/like", headers=other_headers
        )
        assert resp.status_code == 403

    @pytest.mark.integration
    async def test_like_post_idempotent_double_like(self, auth_client, db_session):
        """Liking an already-liked post is idempotent — still 200, count stays 1."""
        post = await create_test_post(db_session)
        await db_session.commit()

        await auth_client.post(f"/api/v1/feed/posts/{post.id}/like")
        resp = await auth_client.post(f"/api/v1/feed/posts/{post.id}/like")
        assert resp.status_code == 200
        assert resp.json()["like_count"] == 1


# ---------------------------------------------------------------------------
# DELETE /api/v1/feed/posts/{post_id}/like
# ---------------------------------------------------------------------------

class TestUnlikePost:
    """DELETE /api/v1/feed/posts/{post_id}/like"""

    @pytest.mark.integration
    async def test_unlike_post_returns_200(self, auth_client, db_session):
        """Unlike (after liking) returns HTTP 200."""
        post = await create_test_post(db_session)
        await db_session.commit()

        await auth_client.post(f"/api/v1/feed/posts/{post.id}/like")
        resp = await auth_client.delete(f"/api/v1/feed/posts/{post.id}/like")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_unlike_post_response_schema(self, auth_client, db_session):
        """Response contains post_id, is_liked=False, like_count."""
        post = await create_test_post(db_session)
        await db_session.commit()

        await auth_client.post(f"/api/v1/feed/posts/{post.id}/like")
        resp = await auth_client.delete(f"/api/v1/feed/posts/{post.id}/like")
        body = resp.json()
        assert body["post_id"] == str(post.id)
        assert body["is_liked"] is False
        assert body["like_count"] == 0

    @pytest.mark.integration
    async def test_unlike_post_requires_authentication(self, client, db_session):
        """Unauthenticated unlike returns HTTP 401."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await client.delete(f"/api/v1/feed/posts/{post.id}/like")
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_unlike_post_idempotent_not_liked(self, auth_client, db_session):
        """Unlike on a post that was never liked returns 200 with is_liked=False."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.delete(f"/api/v1/feed/posts/{post.id}/like")
        assert resp.status_code == 200
        assert resp.json()["is_liked"] is False
        assert resp.json()["like_count"] == 0

    @pytest.mark.integration
    async def test_like_then_unlike_cycle(self, auth_client, db_session):
        """Like followed by unlike results in like_count=0."""
        post = await create_test_post(db_session)
        await db_session.commit()

        await auth_client.post(f"/api/v1/feed/posts/{post.id}/like")
        resp = await auth_client.delete(f"/api/v1/feed/posts/{post.id}/like")
        assert resp.json()["like_count"] == 0
        assert resp.json()["is_liked"] is False


# ---------------------------------------------------------------------------
# POST /api/v1/feed/posts/{post_id}/bookmark
# ---------------------------------------------------------------------------

class TestBookmarkPost:
    """POST /api/v1/feed/posts/{post_id}/bookmark"""

    @pytest.mark.integration
    async def test_bookmark_post_returns_200(self, auth_client, db_session):
        """Authenticated bookmark returns HTTP 200."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.post(f"/api/v1/feed/posts/{post.id}/bookmark")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_bookmark_post_response_schema(self, auth_client, db_session):
        """Response contains post_id and is_bookmarked=True."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.post(f"/api/v1/feed/posts/{post.id}/bookmark")
        body = resp.json()
        assert body["post_id"] == str(post.id)
        assert body["is_bookmarked"] is True

    @pytest.mark.integration
    async def test_bookmark_post_requires_authentication(self, client, db_session):
        """Unauthenticated bookmark returns HTTP 401."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await client.post(f"/api/v1/feed/posts/{post.id}/bookmark")
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_bookmark_post_not_found_returns_404(self, auth_client):
        """Bookmarking a non-existent post returns HTTP 404."""
        resp = await auth_client.post(
            f"/api/v1/feed/posts/{uuid.uuid4()}/bookmark"
        )
        assert resp.status_code == 404

    @pytest.mark.integration
    async def test_bookmark_private_post_non_owner_returns_403(
        self, client, db_session
    ):
        """Bookmarking a PRIVATE post as non-owner returns HTTP 403."""
        post = await create_test_post(
            db_session, author_id=uuid.uuid4(), visibility=PostVisibility.PRIVATE
        )
        await db_session.commit()
        other_headers = build_auth_headers(user_id=uuid.uuid4())

        resp = await client.post(
            f"/api/v1/feed/posts/{post.id}/bookmark", headers=other_headers
        )
        assert resp.status_code == 403

    @pytest.mark.integration
    async def test_bookmark_idempotent_double_bookmark(
        self, auth_client, db_session
    ):
        """Double bookmark is idempotent — returns 200 both times."""
        post = await create_test_post(db_session)
        await db_session.commit()

        await auth_client.post(f"/api/v1/feed/posts/{post.id}/bookmark")
        resp = await auth_client.post(f"/api/v1/feed/posts/{post.id}/bookmark")
        assert resp.status_code == 200
        assert resp.json()["is_bookmarked"] is True


# ---------------------------------------------------------------------------
# DELETE /api/v1/feed/posts/{post_id}/bookmark
# ---------------------------------------------------------------------------

class TestUnbookmarkPost:
    """DELETE /api/v1/feed/posts/{post_id}/bookmark"""

    @pytest.mark.integration
    async def test_unbookmark_post_returns_200(self, auth_client, db_session):
        """Unbookmark (after bookmarking) returns HTTP 200."""
        post = await create_test_post(db_session)
        await db_session.commit()

        await auth_client.post(f"/api/v1/feed/posts/{post.id}/bookmark")
        resp = await auth_client.delete(f"/api/v1/feed/posts/{post.id}/bookmark")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_unbookmark_post_response_schema(self, auth_client, db_session):
        """Response contains post_id and is_bookmarked=False."""
        post = await create_test_post(db_session)
        await db_session.commit()

        await auth_client.post(f"/api/v1/feed/posts/{post.id}/bookmark")
        resp = await auth_client.delete(f"/api/v1/feed/posts/{post.id}/bookmark")
        body = resp.json()
        assert body["post_id"] == str(post.id)
        assert body["is_bookmarked"] is False

    @pytest.mark.integration
    async def test_unbookmark_requires_authentication(self, client, db_session):
        """Unauthenticated unbookmark returns HTTP 401."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await client.delete(f"/api/v1/feed/posts/{post.id}/bookmark")
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_unbookmark_not_bookmarked_post_idempotent(
        self, auth_client, db_session
    ):
        """Unbookmarking a post that was never bookmarked returns 200."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.delete(
            f"/api/v1/feed/posts/{post.id}/bookmark"
        )
        assert resp.status_code == 200
        assert resp.json()["is_bookmarked"] is False

    @pytest.mark.integration
    async def test_bookmark_then_unbookmark_cycle(self, auth_client, db_session):
        """Bookmark then unbookmark results in is_bookmarked=False."""
        post = await create_test_post(db_session)
        await db_session.commit()

        await auth_client.post(f"/api/v1/feed/posts/{post.id}/bookmark")
        resp = await auth_client.delete(
            f"/api/v1/feed/posts/{post.id}/bookmark"
        )
        assert resp.json()["is_bookmarked"] is False


# ---------------------------------------------------------------------------
# GET /api/v1/feed/me/bookmarks
# ---------------------------------------------------------------------------

class TestGetMyBookmarks:
    """GET /api/v1/feed/me/bookmarks"""

    @pytest.mark.integration
    async def test_get_bookmarks_returns_200(self, auth_client):
        """Authenticated request returns HTTP 200."""
        resp = await auth_client.get("/api/v1/feed/me/bookmarks")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_get_bookmarks_requires_authentication(self, client):
        """Unauthenticated request returns HTTP 401."""
        resp = await client.get("/api/v1/feed/me/bookmarks")
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_get_bookmarks_response_schema(self, auth_client):
        """Response has bookmarks, total, limit, offset, has_more fields."""
        resp = await auth_client.get("/api/v1/feed/me/bookmarks")
        body = resp.json()
        assert "bookmarks" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert "has_more" in body

    @pytest.mark.integration
    async def test_get_bookmarks_empty_for_new_user(self, auth_client):
        """New user with no bookmarks gets empty list."""
        resp = await auth_client.get("/api/v1/feed/me/bookmarks")
        body = resp.json()
        assert body["total"] == 0
        assert body["bookmarks"] == []

    @pytest.mark.integration
    async def test_get_bookmarks_contains_bookmarked_posts(
        self, auth_client, db_session
    ):
        """Bookmarked posts appear in the /me/bookmarks response."""
        p1 = await create_test_post(db_session, title="BK1")
        p2 = await create_test_post(db_session, title="BK2")
        await db_session.commit()

        await auth_client.post(f"/api/v1/feed/posts/{p1.id}/bookmark")
        await auth_client.post(f"/api/v1/feed/posts/{p2.id}/bookmark")

        resp = await auth_client.get("/api/v1/feed/me/bookmarks")
        body = resp.json()
        assert body["total"] == 2
        ids = {bk["id"] for bk in body["bookmarks"]}
        assert str(p1.id) in ids
        assert str(p2.id) in ids

    @pytest.mark.integration
    async def test_get_bookmarks_does_not_show_others_bookmarks(
        self, auth_client, client, db_session
    ):
        """User A's bookmarks are not visible to user B."""
        post = await create_test_post(db_session)
        await db_session.commit()
        # User A bookmarks the post
        await auth_client.post(f"/api/v1/feed/posts/{post.id}/bookmark")

        # User B requests their own bookmarks
        other_headers = build_auth_headers(user_id=uuid.uuid4())
        resp = await client.get("/api/v1/feed/me/bookmarks", headers=other_headers)
        assert resp.json()["total"] == 0

    @pytest.mark.integration
    async def test_get_bookmarks_pagination_limit(self, auth_client, db_session):
        """limit query param restricts the number of returned bookmarks."""
        posts = [await create_test_post(db_session, title=f"P{i}") for i in range(4)]
        await db_session.commit()
        for p in posts:
            await auth_client.post(f"/api/v1/feed/posts/{p.id}/bookmark")

        resp = await auth_client.get("/api/v1/feed/me/bookmarks?limit=2")
        body = resp.json()
        assert len(body["bookmarks"]) == 2
        assert body["total"] == 4

    @pytest.mark.integration
    async def test_get_bookmarks_invalid_limit_returns_422(self, auth_client):
        """limit=0 returns HTTP 422."""
        resp = await auth_client.get("/api/v1/feed/me/bookmarks?limit=0")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/feed/posts/{post_id}/share
# ---------------------------------------------------------------------------

class TestSharePost:
    """POST /api/v1/feed/posts/{post_id}/share"""

    @pytest.mark.integration
    async def test_share_post_returns_200(self, auth_client, db_session):
        """Authenticated share returns HTTP 200."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.post(
            f"/api/v1/feed/posts/{post.id}/share",
            json=make_share_payload(),
        )
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_share_post_response_schema(self, auth_client, db_session):
        """Response contains post_id, share_count, share_id."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.post(
            f"/api/v1/feed/posts/{post.id}/share",
            json=make_share_payload(share_channel="twitter"),
        )
        body = resp.json()
        assert body["post_id"] == str(post.id)
        assert body["share_count"] == 1
        assert "share_id" in body
        assert body["share_id"] is not None

    @pytest.mark.integration
    async def test_share_post_requires_authentication(self, client, db_session):
        """Unauthenticated share returns HTTP 401."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await client.post(
            f"/api/v1/feed/posts/{post.id}/share",
            json=make_share_payload(),
        )
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_share_post_not_found_returns_404(self, auth_client):
        """Sharing a non-existent post returns HTTP 404."""
        resp = await auth_client.post(
            f"/api/v1/feed/posts/{uuid.uuid4()}/share",
            json=make_share_payload(),
        )
        assert resp.status_code == 404

    @pytest.mark.integration
    async def test_share_private_post_non_owner_returns_403(
        self, client, db_session
    ):
        """Sharing a PRIVATE post as a non-owner returns HTTP 403."""
        post = await create_test_post(
            db_session, author_id=uuid.uuid4(), visibility=PostVisibility.PRIVATE
        )
        await db_session.commit()
        other_headers = build_auth_headers(user_id=uuid.uuid4())

        resp = await client.post(
            f"/api/v1/feed/posts/{post.id}/share",
            json=make_share_payload(),
            headers=other_headers,
        )
        assert resp.status_code == 403

    @pytest.mark.integration
    async def test_share_post_increments_share_count_on_repeated_shares(
        self, auth_client, db_session
    ):
        """Each share call increments the share_count (not idempotent)."""
        post = await create_test_post(db_session)
        await db_session.commit()

        await auth_client.post(
            f"/api/v1/feed/posts/{post.id}/share",
            json=make_share_payload(),
        )
        resp = await auth_client.post(
            f"/api/v1/feed/posts/{post.id}/share",
            json=make_share_payload(share_channel="facebook"),
        )
        assert resp.json()["share_count"] == 2

    @pytest.mark.integration
    async def test_share_post_no_channel_accepted(self, auth_client, db_session):
        """Share with no share_channel field is accepted."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.post(
            f"/api/v1/feed/posts/{post.id}/share",
            json={},
        )
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_share_post_share_ids_are_unique_across_calls(
        self, auth_client, db_session
    ):
        """Each share generates a distinct share_id."""
        post = await create_test_post(db_session)
        await db_session.commit()

        r1 = await auth_client.post(
            f"/api/v1/feed/posts/{post.id}/share", json=make_share_payload()
        )
        r2 = await auth_client.post(
            f"/api/v1/feed/posts/{post.id}/share", json=make_share_payload()
        )
        assert r1.json()["share_id"] != r2.json()["share_id"]
