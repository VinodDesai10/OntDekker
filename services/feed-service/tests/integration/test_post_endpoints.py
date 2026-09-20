"""
CP-16D — Post Endpoint Tests

Validates HTTP contract for all Post-related endpoints in the Feed Service.
Focus: status codes, response shape, auth enforcement, validation, error
responses, pagination, and query parameters.

Design note
-----------
Setup data (pre-existing posts) is created via the POST /posts HTTP endpoint
rather than via db_session.  This avoids a SQLite/aiosqlite session-sharing
bug that causes ``session.refresh()`` to return integer row IDs when a
``db_session`` and the app-fixture's sessionmaker both access the same
in-memory engine concurrently.

Service-layer or repository logic is NOT re-tested here; only HTTP behaviour
is verified.

Endpoints covered
-----------------
  POST   /api/v1/feed/posts
  GET    /api/v1/feed/posts
  GET    /api/v1/feed/posts/{post_id}
  PUT    /api/v1/feed/posts/{post_id}
  DELETE /api/v1/feed/posts/{post_id}
  GET    /api/v1/feed/users/{user_id}/posts
  GET    /api/v1/feed/communities/{community_id}/posts
"""

import uuid
import pytest

from tests.conftest import TEST_USER_ID
from tests.utils import make_post_payload, build_auth_headers


# ---------------------------------------------------------------------------
# POST /api/v1/feed/posts
# ---------------------------------------------------------------------------

class TestCreatePost:
    """POST /api/v1/feed/posts"""

    @pytest.mark.integration
    async def test_create_post_returns_201(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(title="New Trip"),
        )
        assert resp.status_code == 201

    @pytest.mark.integration
    async def test_create_post_response_schema(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(title="Schema Test"),
        )
        body = resp.json()
        assert "id" in body
        assert "author_id" in body
        assert body["title"] == "Schema Test"
        assert body["status"] == "PUBLISHED"
        assert body["visibility"] == "PUBLIC"
        assert "like_count" in body
        assert "comment_count" in body
        assert "share_count" in body
        assert "is_liked" in body
        assert "is_bookmarked" in body

    @pytest.mark.integration
    async def test_create_post_stores_tags(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(title="Tagged", tags=["hiking", "alps"]),
        )
        body = resp.json()
        tag_values = {t["tag"] for t in body["tags"]}
        assert "hiking" in tag_values
        assert "alps" in tag_values

    @pytest.mark.integration
    async def test_create_post_requires_authentication(self, client):
        resp = await client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(),
        )
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_create_post_missing_title_returns_422(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/feed/posts",
            json={"content": "No title here"},
        )
        assert resp.status_code == 422

    @pytest.mark.integration
    async def test_create_post_community_private_returns_400(self, auth_client):
        """community_id + PRIVATE visibility is rejected with HTTP 400 (business rule).

        The create_post handler now has an explicit try/except ValidationError block
        that converts the service-layer ValidationError → HTTPException(400).
        This aligns with update_post and delete_post which also return 400 for
        business-rule violations.
        """
        resp = await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(
                community_id=uuid.uuid4(),
                visibility="PRIVATE",
            ),
        )
        assert resp.status_code == 400

    @pytest.mark.integration
    async def test_create_post_public_with_community_id_returns_400(self, auth_client):
        """PUBLIC (Global) post with a community_id is rejected with HTTP 400."""
        resp = await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(
                community_id=uuid.uuid4(),
                visibility="PUBLIC",
            ),
        )
        assert resp.status_code == 400

    @pytest.mark.integration
    async def test_create_post_community_without_community_id_returns_400(self, auth_client):
        """COMMUNITY post without a community_id is rejected with HTTP 400."""
        resp = await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(
                community_id=None,
                visibility="COMMUNITY",
            ),
        )
        assert resp.status_code == 400

    @pytest.mark.integration
    async def test_create_post_invalid_bearer_returns_401(self, client):
        resp = await client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(),
            headers={"Authorization": "Bearer not-a-valid-token"},
        )
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_create_post_sets_author_id_from_token(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(title="Author Check"),
        )
        assert resp.json()["author_id"] == str(TEST_USER_ID)

    @pytest.mark.integration
    async def test_create_post_interaction_counts_zero(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(),
        )
        body = resp.json()
        assert body["like_count"] == 0
        assert body["comment_count"] == 0
        assert body["share_count"] == 0


# ---------------------------------------------------------------------------
# GET /api/v1/feed/posts
# ---------------------------------------------------------------------------

class TestListPosts:
    """GET /api/v1/feed/posts"""

    @pytest.mark.integration
    async def test_list_posts_returns_200(self, client):
        resp = await client.get("/api/v1/feed/posts")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_list_posts_response_schema(self, auth_client, client):
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Listed"))

        resp = await client.get("/api/v1/feed/posts")
        body = resp.json()
        assert "posts" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert "has_more" in body

    @pytest.mark.integration
    async def test_list_posts_pagination_limit(self, auth_client, client):
        for i in range(5):
            await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title=f"P{i}"))

        resp = await client.get("/api/v1/feed/posts?limit=2")
        body = resp.json()
        assert len(body["posts"]) == 2
        assert body["limit"] == 2

    @pytest.mark.integration
    async def test_list_posts_has_more_true_when_beyond_page(self, auth_client, client):
        for i in range(4):
            await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title=f"P{i}"))

        resp = await client.get("/api/v1/feed/posts?limit=2&offset=0")
        assert resp.json()["has_more"] is True

    @pytest.mark.integration
    async def test_list_posts_offset_pagination(self, auth_client, client):
        for i in range(4):
            await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title=f"Post {i}"))

        resp_p1 = await client.get("/api/v1/feed/posts?limit=2&offset=0")
        resp_p2 = await client.get("/api/v1/feed/posts?limit=2&offset=2")
        ids_p1 = {p["id"] for p in resp_p1.json()["posts"]}
        ids_p2 = {p["id"] for p in resp_p2.json()["posts"]}
        assert ids_p1.isdisjoint(ids_p2)

    @pytest.mark.integration
    async def test_list_posts_excludes_private_for_anonymous(self, auth_client, client):
        """Private posts are not returned to anonymous callers."""
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Public", visibility="PUBLIC"))
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Private", visibility="PRIVATE"))

        resp = await client.get("/api/v1/feed/posts")
        titles = [p["title"] for p in resp.json()["posts"]]
        assert "Public" in titles
        assert "Private" not in titles

    @pytest.mark.integration
    async def test_list_posts_author_filter(self, auth_client, client):
        """author_id query param returns only that author's posts."""
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Mine"))
        # Create a post as a different user
        other_headers = build_auth_headers(user_id=uuid.uuid4())
        await client.post("/api/v1/feed/posts", json=make_post_payload(title="Others"), headers=other_headers)

        resp = await client.get(f"/api/v1/feed/posts?author_id={TEST_USER_ID}")
        body = resp.json()
        assert body["total"] >= 1
        assert all(p["author_id"] == str(TEST_USER_ID) for p in body["posts"])

    @pytest.mark.integration
    async def test_list_posts_community_filter(self, auth_client, client):
        community_id = uuid.uuid4()
        # Create the community post as a *different* user so the TEST_USER_ID
        # (auth_client) can see it on GET — the service excludes the requesting
        # user's own posts from the general feed (own-post exclusion).
        other_headers = build_auth_headers(user_id=uuid.uuid4())
        await client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(title="InCommunity", community_id=community_id, visibility="COMMUNITY"),
            headers=other_headers,
        )
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="NoCommunity"))

        # Use auth_client for GET — COMMUNITY posts are only visible to authenticated users
        resp = await auth_client.get(f"/api/v1/feed/posts?community_id={community_id}")
        body = resp.json()
        assert body["total"] == 1
        assert body["posts"][0]["title"] == "InCommunity"

    @pytest.mark.integration
    async def test_list_posts_invalid_limit_returns_422(self, client):
        resp = await client.get("/api/v1/feed/posts?limit=0")
        assert resp.status_code == 422

    @pytest.mark.integration
    async def test_list_posts_limit_above_max_returns_422(self, client):
        resp = await client.get("/api/v1/feed/posts?limit=101")
        assert resp.status_code == 422

    @pytest.mark.integration
    async def test_list_posts_empty_database_returns_empty(self, client):
        resp = await client.get("/api/v1/feed/posts")
        body = resp.json()
        assert body["total"] == 0
        assert body["posts"] == []
        assert body["has_more"] is False


# ---------------------------------------------------------------------------
# GET /api/v1/feed/posts/{post_id}
# ---------------------------------------------------------------------------

class TestGetPost:
    """GET /api/v1/feed/posts/{post_id}"""

    @pytest.mark.integration
    async def test_get_post_returns_200(self, auth_client):
        create_resp = await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Findable"))
        post_id = create_resp.json()["id"]

        resp = await auth_client.get(f"/api/v1/feed/posts/{post_id}")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_get_post_response_schema(self, auth_client):
        create_resp = await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Schema"))
        post_id = create_resp.json()["id"]

        resp = await auth_client.get(f"/api/v1/feed/posts/{post_id}")
        body = resp.json()
        assert body["id"] == post_id
        assert body["title"] == "Schema"
        assert "author_id" in body
        assert "status" in body
        assert "visibility" in body
        assert "like_count" in body

    @pytest.mark.integration
    async def test_get_post_not_found_returns_404(self, client):
        resp = await client.get(f"/api/v1/feed/posts/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.integration
    async def test_get_post_private_anonymous_returns_403(self, auth_client, client):
        """Private post returns HTTP 403 for anonymous caller."""
        create_resp = await auth_client.post(
            "/api/v1/feed/posts", json=make_post_payload(visibility="PRIVATE")
        )
        post_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/feed/posts/{post_id}")
        assert resp.status_code == 403

    @pytest.mark.integration
    async def test_get_post_private_other_user_returns_403(self, auth_client, client):
        """Private post returns HTTP 403 for a different authenticated user."""
        create_resp = await auth_client.post(
            "/api/v1/feed/posts", json=make_post_payload(visibility="PRIVATE")
        )
        post_id = create_resp.json()["id"]
        other_headers = build_auth_headers(user_id=uuid.uuid4())

        resp = await client.get(f"/api/v1/feed/posts/{post_id}", headers=other_headers)
        assert resp.status_code == 403

    @pytest.mark.integration
    async def test_get_post_private_visible_to_author(self, auth_client):
        """Private post returns HTTP 200 to the author."""
        create_resp = await auth_client.post(
            "/api/v1/feed/posts", json=make_post_payload(visibility="PRIVATE")
        )
        post_id = create_resp.json()["id"]

        resp = await auth_client.get(f"/api/v1/feed/posts/{post_id}")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_get_post_public_no_auth_required(self, auth_client, client):
        """Public post is accessible without authentication."""
        create_resp = await auth_client.post(
            "/api/v1/feed/posts", json=make_post_payload(visibility="PUBLIC")
        )
        post_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/feed/posts/{post_id}")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_get_post_invalid_uuid_returns_422(self, client):
        resp = await client.get("/api/v1/feed/posts/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/v1/feed/posts/{post_id}
# ---------------------------------------------------------------------------

class TestUpdatePost:
    """PUT /api/v1/feed/posts/{post_id}"""

    @pytest.mark.integration
    async def test_update_post_returns_200(self, auth_client):
        create_resp = await auth_client.post("/api/v1/feed/posts", json=make_post_payload())
        post_id = create_resp.json()["id"]

        resp = await auth_client.put(
            f"/api/v1/feed/posts/{post_id}",
            json={"title": "Updated Title"},
        )
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_update_post_title_changed_in_response(self, auth_client):
        create_resp = await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Old"))
        post_id = create_resp.json()["id"]

        resp = await auth_client.put(
            f"/api/v1/feed/posts/{post_id}",
            json={"title": "New Title"},
        )
        assert resp.json()["title"] == "New Title"

    @pytest.mark.integration
    async def test_update_post_requires_authentication(self, auth_client, client):
        create_resp = await auth_client.post("/api/v1/feed/posts", json=make_post_payload())
        post_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/feed/posts/{post_id}",
            json={"title": "Hack"},
        )
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_update_post_non_author_returns_403(self, auth_client, client):
        """Non-author update returns HTTP 403."""
        create_resp = await auth_client.post("/api/v1/feed/posts", json=make_post_payload())
        post_id = create_resp.json()["id"]
        other_headers = build_auth_headers(user_id=uuid.uuid4())

        resp = await client.put(
            f"/api/v1/feed/posts/{post_id}",
            json={"title": "Hijack"},
            headers=other_headers,
        )
        assert resp.status_code == 403

    @pytest.mark.integration
    async def test_update_post_not_found_returns_404(self, auth_client):
        resp = await auth_client.put(
            f"/api/v1/feed/posts/{uuid.uuid4()}",
            json={"title": "Ghost"},
        )
        assert resp.status_code == 404

    @pytest.mark.integration
    async def test_update_post_community_private_returns_400(self, auth_client):
        """Setting PRIVATE on a community post returns HTTP 400.

        Creates a COMMUNITY post first, then attempts to update its visibility
        to PRIVATE which should be rejected.
        """
        community_id = uuid.uuid4()
        # Create a valid COMMUNITY post (membership check mocked to True in conftest)
        create_resp = await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(community_id=community_id, visibility="COMMUNITY"),
        )
        assert create_resp.status_code == 201, f"Setup failed: {create_resp.json()}"
        post_id = create_resp.json()["id"]

        resp = await auth_client.put(
            f"/api/v1/feed/posts/{post_id}",
            json={"visibility": "PRIVATE"},
        )
        assert resp.status_code == 400

    @pytest.mark.integration
    async def test_update_post_response_is_post_schema(self, auth_client):
        create_resp = await auth_client.post("/api/v1/feed/posts", json=make_post_payload())
        post_id = create_resp.json()["id"]

        resp = await auth_client.put(
            f"/api/v1/feed/posts/{post_id}",
            json={"content": "New content"},
        )
        body = resp.json()
        assert "id" in body
        assert "author_id" in body
        assert body["content"] == "New content"


# ---------------------------------------------------------------------------
# DELETE /api/v1/feed/posts/{post_id}
# ---------------------------------------------------------------------------

class TestDeletePost:
    """DELETE /api/v1/feed/posts/{post_id}"""

    @pytest.mark.integration
    async def test_delete_post_returns_204(self, auth_client):
        create_resp = await auth_client.post("/api/v1/feed/posts", json=make_post_payload())
        post_id = create_resp.json()["id"]

        resp = await auth_client.delete(f"/api/v1/feed/posts/{post_id}")
        assert resp.status_code == 204

    @pytest.mark.integration
    async def test_delete_post_no_body_on_204(self, auth_client):
        create_resp = await auth_client.post("/api/v1/feed/posts", json=make_post_payload())
        post_id = create_resp.json()["id"]

        resp = await auth_client.delete(f"/api/v1/feed/posts/{post_id}")
        assert resp.content == b""

    @pytest.mark.integration
    async def test_delete_post_requires_authentication(self, auth_client, client):
        create_resp = await auth_client.post("/api/v1/feed/posts", json=make_post_payload())
        post_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/feed/posts/{post_id}")
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_delete_post_non_author_returns_403(self, auth_client, client):
        create_resp = await auth_client.post("/api/v1/feed/posts", json=make_post_payload())
        post_id = create_resp.json()["id"]
        other_headers = build_auth_headers(user_id=uuid.uuid4())

        resp = await client.delete(f"/api/v1/feed/posts/{post_id}", headers=other_headers)
        assert resp.status_code == 403

    @pytest.mark.integration
    async def test_delete_post_not_found_returns_404(self, auth_client):
        resp = await auth_client.delete(f"/api/v1/feed/posts/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.integration
    async def test_delete_post_then_get_returns_404(self, auth_client):
        create_resp = await auth_client.post("/api/v1/feed/posts", json=make_post_payload())
        post_id = create_resp.json()["id"]

        await auth_client.delete(f"/api/v1/feed/posts/{post_id}")
        resp = await auth_client.get(f"/api/v1/feed/posts/{post_id}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/feed/users/{user_id}/posts
# ---------------------------------------------------------------------------

class TestGetUserPosts:
    """GET /api/v1/feed/users/{user_id}/posts"""

    @pytest.mark.integration
    async def test_get_user_posts_returns_200(self, client):
        resp = await client.get(f"/api/v1/feed/users/{uuid.uuid4()}/posts")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_get_user_posts_returns_author_posts(self, auth_client, client):
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="By Author"))
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Also By Author"))
        # Post by a different user
        other_headers = build_auth_headers(user_id=uuid.uuid4())
        await client.post("/api/v1/feed/posts", json=make_post_payload(title="Someone Else"), headers=other_headers)

        resp = await client.get(f"/api/v1/feed/users/{TEST_USER_ID}/posts")
        body = resp.json()
        assert body["total"] == 2
        assert all(p["author_id"] == str(TEST_USER_ID) for p in body["posts"])

    @pytest.mark.integration
    async def test_get_user_posts_hides_private_from_other_user(self, auth_client, client):
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Pub", visibility="PUBLIC"))
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Priv", visibility="PRIVATE"))
        other_headers = build_auth_headers(user_id=uuid.uuid4())

        resp = await client.get(f"/api/v1/feed/users/{TEST_USER_ID}/posts", headers=other_headers)
        titles = [p["title"] for p in resp.json()["posts"]]
        assert "Pub" in titles
        assert "Priv" not in titles

    @pytest.mark.integration
    async def test_get_user_posts_owner_sees_own_private(self, auth_client):
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Pub", visibility="PUBLIC"))
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Priv", visibility="PRIVATE"))

        resp = await auth_client.get(f"/api/v1/feed/users/{TEST_USER_ID}/posts")
        assert resp.json()["total"] == 2

    @pytest.mark.integration
    async def test_get_user_posts_empty_for_unknown_user(self, client):
        resp = await client.get(f"/api/v1/feed/users/{uuid.uuid4()}/posts")
        body = resp.json()
        assert body["total"] == 0
        assert body["posts"] == []

    @pytest.mark.integration
    async def test_get_user_posts_pagination_limit(self, auth_client, client):
        for i in range(4):
            await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title=f"P{i}"))

        resp = await client.get(f"/api/v1/feed/users/{TEST_USER_ID}/posts?limit=2")
        assert len(resp.json()["posts"]) == 2

    @pytest.mark.integration
    async def test_get_user_posts_response_schema(self, auth_client, client):
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload())

        resp = await client.get(f"/api/v1/feed/users/{TEST_USER_ID}/posts")
        body = resp.json()
        assert "posts" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert "has_more" in body


# ---------------------------------------------------------------------------
# GET /api/v1/feed/communities/{community_id}/posts
# ---------------------------------------------------------------------------

class TestGetCommunityPosts:
    """GET /api/v1/feed/communities/{community_id}/posts"""

    @pytest.mark.integration
    async def test_get_community_posts_returns_200(self, client):
        resp = await client.get(f"/api/v1/feed/communities/{uuid.uuid4()}/posts")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_get_community_posts_returns_community_posts(self, auth_client, client):
        community_id = uuid.uuid4()
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="In Community", community_id=community_id, visibility="COMMUNITY"))
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Also In Community", community_id=community_id, visibility="COMMUNITY"))
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="No Community"))

        resp = await client.get(f"/api/v1/feed/communities/{community_id}/posts")
        assert resp.json()["total"] == 2

    @pytest.mark.integration
    async def test_get_community_posts_empty_for_unknown_community(self, client):
        resp = await client.get(f"/api/v1/feed/communities/{uuid.uuid4()}/posts")
        body = resp.json()
        assert body["total"] == 0
        assert body["posts"] == []

    @pytest.mark.integration
    async def test_get_community_posts_response_schema(self, auth_client, client):
        community_id = uuid.uuid4()
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(community_id=community_id, visibility="COMMUNITY"))

        resp = await client.get(f"/api/v1/feed/communities/{community_id}/posts")
        body = resp.json()
        assert "posts" in body
        assert "total" in body
        assert "has_more" in body

    @pytest.mark.integration
    async def test_get_community_posts_pagination_limit(self, auth_client, client):
        community_id = uuid.uuid4()
        for i in range(4):
            await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title=f"P{i}", community_id=community_id, visibility="COMMUNITY"))

        resp = await client.get(f"/api/v1/feed/communities/{community_id}/posts?limit=2")
        assert len(resp.json()["posts"]) == 2

    @pytest.mark.integration
    async def test_get_community_posts_no_auth_required(self, auth_client, client):
        community_id = uuid.uuid4()
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(community_id=community_id, visibility="COMMUNITY"))

        resp = await client.get(f"/api/v1/feed/communities/{community_id}/posts")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/v1/feed/me/posts  (CP-POST-3)
# ---------------------------------------------------------------------------

class TestGetMyPosts:
    """GET /api/v1/feed/me/posts

    Verifies the authenticated-user-only My Posts endpoint introduced in
    CP-POST-3.  The JWT sub claim is the authoritative author identity — the
    caller cannot supply an arbitrary author_id to retrieve another user's
    posts.
    """

    @pytest.mark.integration
    async def test_get_my_posts_requires_authentication(self, client):
        """Unauthenticated requests must be rejected with 401."""
        resp = await client.get("/api/v1/feed/me/posts")
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_get_my_posts_returns_200_when_authenticated(self, auth_client):
        """Authenticated requests return 200 OK."""
        resp = await auth_client.get("/api/v1/feed/me/posts")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_get_my_posts_response_schema(self, auth_client):
        """Response contains the expected PostListResponse shape."""
        await auth_client.post("/api/v1/feed/posts", json=make_post_payload(title="Schema Check"))
        resp = await auth_client.get("/api/v1/feed/me/posts")
        body = resp.json()
        assert "posts" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert "has_more" in body

    @pytest.mark.integration
    async def test_get_my_posts_returns_global_post(self, auth_client):
        """Test 1: User A creates a Global (PUBLIC) post → My Posts returns it."""
        await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(title="Global Post A", visibility="PUBLIC"),
        )
        resp = await auth_client.get("/api/v1/feed/me/posts")
        body = resp.json()
        assert body["total"] >= 1
        titles = [p["title"] for p in body["posts"]]
        assert "Global Post A" in titles

    @pytest.mark.integration
    async def test_get_my_posts_returns_community_post(self, auth_client):
        """Test 2: User A creates a COMMUNITY post → My Posts returns it."""
        community_id = uuid.uuid4()
        await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(
                title="Community Post A",
                visibility="COMMUNITY",
                community_id=community_id,
            ),
        )
        resp = await auth_client.get("/api/v1/feed/me/posts")
        body = resp.json()
        titles = [p["title"] for p in body["posts"]]
        assert "Community Post A" in titles

    @pytest.mark.integration
    async def test_get_my_posts_returns_both_global_and_community(self, auth_client):
        """Test 3: User A creates both Global and Community posts → both returned."""
        community_id = uuid.uuid4()
        await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(title="Global A", visibility="PUBLIC"),
        )
        await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(
                title="Community A",
                visibility="COMMUNITY",
                community_id=community_id,
            ),
        )
        resp = await auth_client.get("/api/v1/feed/me/posts")
        body = resp.json()
        assert body["total"] >= 2
        titles = [p["title"] for p in body["posts"]]
        assert "Global A" in titles
        assert "Community A" in titles

    @pytest.mark.integration
    async def test_get_my_posts_excludes_other_users_posts(self, auth_client, client):
        """Test 4: User A's My Posts does not include User B's posts."""
        other_headers = build_auth_headers(user_id=uuid.uuid4())
        # User B creates a post
        await client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(title="User B Post"),
            headers=other_headers,
        )
        # User A creates a post
        await auth_client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(title="User A Post"),
        )
        resp = await auth_client.get("/api/v1/feed/me/posts")
        body = resp.json()
        # All returned posts must belong to User A (TEST_USER_ID)
        assert all(p["author_id"] == str(TEST_USER_ID) for p in body["posts"])
        # User B's title must not appear
        titles = [p["title"] for p in body["posts"]]
        assert "User B Post" not in titles

    @pytest.mark.integration
    async def test_get_my_posts_empty_when_no_posts(self, auth_client):
        """Test 5: User with no posts gets an empty paginated result."""
        resp = await auth_client.get("/api/v1/feed/me/posts")
        body = resp.json()
        assert body["total"] == 0
        assert body["posts"] == []
        assert body["has_more"] is False

    @pytest.mark.integration
    async def test_get_my_posts_cannot_use_query_param_to_get_other_user(self, auth_client, client):
        """Test 7: author_id query param cannot override JWT identity.

        Passing an arbitrary author_id as a query parameter must NOT cause the
        endpoint to return that user's posts.  The endpoint ignores all
        author-id-style query parameters — only the JWT sub is used.
        """
        other_id = uuid.uuid4()
        other_headers = build_auth_headers(user_id=other_id)
        # Other user creates a post
        await client.post(
            "/api/v1/feed/posts",
            json=make_post_payload(title="Should Not Appear"),
            headers=other_headers,
        )
        # Current user (TEST_USER_ID) calls /me/posts with other user's id
        resp = await auth_client.get(
            "/api/v1/feed/me/posts",
            params={"author_id": str(other_id)},  # should be ignored
        )
        body = resp.json()
        # The endpoint does not accept author_id — result is USER_A's posts only
        titles = [p["title"] for p in body["posts"]]
        assert "Should Not Appear" not in titles

    @pytest.mark.integration
    async def test_get_my_posts_pagination_limit(self, auth_client):
        """Pagination: limit parameter restricts result count."""
        for i in range(5):
            await auth_client.post(
                "/api/v1/feed/posts",
                json=make_post_payload(title=f"Paginated Post {i}"),
            )
        resp = await auth_client.get("/api/v1/feed/me/posts?limit=3")
        body = resp.json()
        assert len(body["posts"]) == 3
        assert body["total"] == 5
        assert body["has_more"] is True

    @pytest.mark.integration
    async def test_get_my_posts_pagination_offset(self, auth_client):
        """Pagination: offset parameter skips earlier posts."""
        for i in range(4):
            await auth_client.post(
                "/api/v1/feed/posts",
                json=make_post_payload(title=f"Offset Post {i}"),
            )
        resp = await auth_client.get("/api/v1/feed/me/posts?limit=2&offset=2")
        body = resp.json()
        assert len(body["posts"]) == 2
        assert body["total"] == 4

    @pytest.mark.integration
    async def test_get_my_posts_all_posts_authored_by_jwt_user(self, auth_client):
        """All returned posts have author_id equal to the JWT sub (TEST_USER_ID)."""
        for i in range(3):
            await auth_client.post(
                "/api/v1/feed/posts",
                json=make_post_payload(title=f"Mine {i}"),
            )
        resp = await auth_client.get("/api/v1/feed/me/posts")
        body = resp.json()
        assert all(p["author_id"] == str(TEST_USER_ID) for p in body["posts"])

    @pytest.mark.integration
    async def test_get_my_posts_invalid_bearer_returns_401(self, client):
        """Invalid/expired token is rejected with 401."""
        resp = await client.get(
            "/api/v1/feed/me/posts",
            headers={"Authorization": "Bearer not-a-valid-token"},
        )
        assert resp.status_code == 401
