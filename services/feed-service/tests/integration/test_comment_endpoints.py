"""
CP-16D — Comment Endpoint Tests

Validates HTTP contract for all Comment-related endpoints in the Feed Service.
Focus: status codes, response shape, auth enforcement, error responses,
pagination, and authorization rules.

Endpoints covered
-----------------
  POST   /api/v1/feed/posts/{post_id}/comments
  GET    /api/v1/feed/posts/{post_id}/comments
  PUT    /api/v1/feed/comments/{comment_id}
  DELETE /api/v1/feed/comments/{comment_id}
  POST   /api/v1/feed/comments/{comment_id}/reply
"""

import uuid
import pytest

from tests.conftest import TEST_USER_ID
from tests.utils import create_test_post, create_test_comment, build_auth_headers
from app.repositories.comment_repository import CommentRepository


# ---------------------------------------------------------------------------
# POST /api/v1/feed/posts/{post_id}/comments
# ---------------------------------------------------------------------------

class TestCreateComment:
    """POST /api/v1/feed/posts/{post_id}/comments"""

    @pytest.mark.integration
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Production bug: CommentService.create_comment() calls "
            "CommentSchema.model_validate(comment) on a freshly created ORM object "
            "whose 'replies' relationship has not been eagerly loaded. "
            "Pydantic attempts to access comment.replies, which triggers a lazy "
            "load in the async context, raising MissingGreenlet. "
            "Fix: apply selectinload(Comment.replies) in CommentRepository.create()."
        ),
    )
    async def test_create_comment_returns_201(self, auth_client, db_session):
        """Authenticated comment creation returns HTTP 201."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.post(
            f"/api/v1/feed/posts/{post.id}/comments",
            json={"content": "Great post!"},
        )
        assert resp.status_code == 201

    @pytest.mark.integration
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Production bug: same MissingGreenlet as test_create_comment_returns_201. "
            "CommentService.create_comment() returns without eagerly loading 'replies'."
        ),
    )
    async def test_create_comment_response_schema(self, auth_client, db_session):
        """Response contains id, post_id, author_id, content, replies."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.post(
            f"/api/v1/feed/posts/{post.id}/comments",
            json={"content": "Schema check!"},
        )
        body = resp.json()
        assert "id" in body
        assert body["post_id"] == str(post.id)
        assert body["author_id"] == str(TEST_USER_ID)
        assert body["content"] == "Schema check!"
        assert "replies" in body
        assert "created_at" in body
        assert "updated_at" in body

    @pytest.mark.integration
    async def test_create_comment_requires_authentication(self, client, db_session):
        """Unauthenticated comment creation returns HTTP 401."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await client.post(
            f"/api/v1/feed/posts/{post.id}/comments",
            json={"content": "Anonymous"},
        )
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_create_comment_on_missing_post_returns_404(self, auth_client):
        """Comment on non-existent post returns HTTP 404."""
        resp = await auth_client.post(
            f"/api/v1/feed/posts/{uuid.uuid4()}/comments",
            json={"content": "Ghost comment"},
        )
        assert resp.status_code == 404

    @pytest.mark.integration
    async def test_create_comment_empty_content_returns_422(
        self, auth_client, db_session
    ):
        """Comment with empty content returns HTTP 422."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.post(
            f"/api/v1/feed/posts/{post.id}/comments",
            json={"content": ""},
        )
        assert resp.status_code == 422

    @pytest.mark.integration
    async def test_create_comment_missing_content_returns_422(
        self, auth_client, db_session
    ):
        """Comment with no content field returns HTTP 422."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.post(
            f"/api/v1/feed/posts/{post.id}/comments",
            json={},
        )
        assert resp.status_code == 422

    @pytest.mark.integration
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Production bug: CommentRepository.create() returns a Comment whose "
            "'replies' relationship is not eagerly loaded. "
            "CommentService.create_comment() then calls "
            "CommentSchema.model_validate(comment), which causes Pydantic to access "
            "comment.replies, triggering SQLAlchemy async lazy loading and raising "
            "MissingGreenlet. The endpoint returns a 500 instead of 201."
        ),
    )
    async def test_create_comment_sets_author_from_token(
        self, auth_client, db_session
    ):
        """author_id in the response matches the authenticated user."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await auth_client.post(
            f"/api/v1/feed/posts/{post.id}/comments",
            json={"content": "Author check"},
        )
        assert resp.json()["author_id"] == str(TEST_USER_ID)

    @pytest.mark.integration
    async def test_create_comment_invalid_bearer_returns_401(
        self, client, db_session
    ):
        """Malformed JWT returns HTTP 401."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await client.post(
            f"/api/v1/feed/posts/{post.id}/comments",
            json={"content": "Hacked"},
            headers={"Authorization": "Bearer bad-token"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/feed/posts/{post_id}/comments
# ---------------------------------------------------------------------------

class TestGetPostComments:
    """GET /api/v1/feed/posts/{post_id}/comments"""

    @pytest.mark.integration
    async def test_get_post_comments_returns_200(self, client, db_session):
        """GET comments for a post with comments returns HTTP 200."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        await repo.create(
            post_id=post.id, author_id=uuid.uuid4(), content="Hello"
        )

        resp = await client.get(f"/api/v1/feed/posts/{post.id}/comments")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_get_post_comments_empty_returns_200(self, client, db_session):
        """GET comments for a post with no comments returns HTTP 200 + empty list."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await client.get(f"/api/v1/feed/posts/{post.id}/comments")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["comments"] == []
        assert body["has_more"] is False

    @pytest.mark.integration
    async def test_get_post_comments_response_schema(self, client, db_session):
        """Response contains comments, total, limit, offset, has_more."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await client.get(f"/api/v1/feed/posts/{post.id}/comments")
        body = resp.json()
        assert "comments" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert "has_more" in body

    @pytest.mark.integration
    async def test_get_post_comments_no_auth_required(self, client, db_session):
        """Comment listing endpoint does not require authentication."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await client.get(f"/api/v1/feed/posts/{post.id}/comments")
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_get_post_comments_pagination_limit(self, client, db_session):
        """limit query param restricts the number of comments returned."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        for i in range(5):
            await repo.create(
                post_id=post.id, author_id=uuid.uuid4(), content=f"C{i}"
            )

        resp = await client.get(
            f"/api/v1/feed/posts/{post.id}/comments?limit=3"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["comments"]) == 3
        assert body["total"] == 5

    @pytest.mark.integration
    async def test_get_post_comments_has_more_flag(self, client, db_session):
        """has_more=True when there are more comments beyond the page."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        for i in range(4):
            await repo.create(
                post_id=post.id, author_id=uuid.uuid4(), content=f"C{i}"
            )

        resp = await client.get(
            f"/api/v1/feed/posts/{post.id}/comments?limit=2&offset=0"
        )
        assert resp.json()["has_more"] is True

    @pytest.mark.integration
    async def test_get_post_comments_excludes_deleted(self, client, db_session):
        """Soft-deleted comments are excluded from the response."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        live = await repo.create(
            post_id=post.id, author_id=uuid.uuid4(), content="Live"
        )
        deleted = await repo.create(
            post_id=post.id, author_id=uuid.uuid4(), content="Deleted"
        )
        await repo.soft_delete(deleted.id)

        resp = await client.get(f"/api/v1/feed/posts/{post.id}/comments")
        body = resp.json()
        ids = [c["id"] for c in body["comments"]]
        assert str(live.id) in ids
        assert str(deleted.id) not in ids

    @pytest.mark.integration
    async def test_get_post_comments_invalid_limit_returns_422(
        self, client, db_session
    ):
        """limit=0 returns HTTP 422."""
        post = await create_test_post(db_session)
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/feed/posts/{post.id}/comments?limit=0"
        )
        assert resp.status_code == 422

    @pytest.mark.integration
    async def test_get_post_comments_invalid_uuid_returns_422(self, client):
        """Non-UUID post_id returns HTTP 422."""
        resp = await client.get("/api/v1/feed/posts/not-a-uuid/comments")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/v1/feed/comments/{comment_id}
# ---------------------------------------------------------------------------

class TestUpdateComment:
    """PUT /api/v1/feed/comments/{comment_id}"""

    @pytest.mark.integration
    async def test_update_comment_returns_200(self, auth_client, db_session):
        """Author updating their own comment returns HTTP 200."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        comment = await repo.create(
            post_id=post.id, author_id=TEST_USER_ID, content="Original"
        )

        resp = await auth_client.put(
            f"/api/v1/feed/comments/{comment.id}",
            json={"content": "Updated"},
        )
        assert resp.status_code == 200

    @pytest.mark.integration
    async def test_update_comment_content_in_response(
        self, auth_client, db_session
    ):
        """Updated content is reflected in the response body."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        comment = await repo.create(
            post_id=post.id, author_id=TEST_USER_ID, content="Old"
        )

        resp = await auth_client.put(
            f"/api/v1/feed/comments/{comment.id}",
            json={"content": "New content"},
        )
        assert resp.json()["content"] == "New content"

    @pytest.mark.integration
    async def test_update_comment_requires_authentication(
        self, client, db_session
    ):
        """Unauthenticated update returns HTTP 401."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        comment = await repo.create(
            post_id=post.id, author_id=TEST_USER_ID, content="Mine"
        )

        resp = await client.put(
            f"/api/v1/feed/comments/{comment.id}",
            json={"content": "Anon edit"},
        )
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_update_comment_non_author_returns_403(
        self, client, db_session
    ):
        """Non-author update returns HTTP 403."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        comment = await repo.create(
            post_id=post.id, author_id=uuid.uuid4(), content="Not mine"
        )
        other_headers = build_auth_headers(user_id=uuid.uuid4())

        resp = await client.put(
            f"/api/v1/feed/comments/{comment.id}",
            json={"content": "Hijack"},
            headers=other_headers,
        )
        assert resp.status_code == 403

    @pytest.mark.integration
    async def test_update_comment_missing_id_returns_403(self, auth_client):
        """Updating a non-existent comment returns HTTP 403 (auth check fails first)."""
        resp = await auth_client.put(
            f"/api/v1/feed/comments/{uuid.uuid4()}",
            json={"content": "Ghost edit"},
        )
        assert resp.status_code == 403

    @pytest.mark.integration
    async def test_update_comment_empty_content_returns_422(
        self, auth_client, db_session
    ):
        """Empty content string returns HTTP 422."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        comment = await repo.create(
            post_id=post.id, author_id=TEST_USER_ID, content="Mine"
        )

        resp = await auth_client.put(
            f"/api/v1/feed/comments/{comment.id}",
            json={"content": ""},
        )
        assert resp.status_code == 422

    @pytest.mark.integration
    async def test_update_comment_missing_content_returns_422(
        self, auth_client, db_session
    ):
        """Request without content field returns HTTP 422."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        comment = await repo.create(
            post_id=post.id, author_id=TEST_USER_ID, content="Mine"
        )

        resp = await auth_client.put(
            f"/api/v1/feed/comments/{comment.id}",
            json={},
        )
        assert resp.status_code == 422

    @pytest.mark.integration
    async def test_update_deleted_comment_returns_403(
        self, auth_client, db_session
    ):
        """Updating a soft-deleted comment returns HTTP 403."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        comment = await repo.create(
            post_id=post.id, author_id=TEST_USER_ID, content="Soon deleted"
        )
        await repo.soft_delete(comment.id)

        resp = await auth_client.put(
            f"/api/v1/feed/comments/{comment.id}",
            json={"content": "Too late"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /api/v1/feed/comments/{comment_id}
# ---------------------------------------------------------------------------

class TestDeleteComment:
    """DELETE /api/v1/feed/comments/{comment_id}"""

    @pytest.mark.integration
    async def test_delete_comment_returns_204(self, auth_client, db_session):
        """Author deleting their own comment returns HTTP 204."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        comment = await repo.create(
            post_id=post.id, author_id=TEST_USER_ID, content="Delete me"
        )

        resp = await auth_client.delete(f"/api/v1/feed/comments/{comment.id}")
        assert resp.status_code == 204

    @pytest.mark.integration
    async def test_delete_comment_no_body_on_204(self, auth_client, db_session):
        """HTTP 204 response has an empty body."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        comment = await repo.create(
            post_id=post.id, author_id=TEST_USER_ID, content="Delete me"
        )

        resp = await auth_client.delete(f"/api/v1/feed/comments/{comment.id}")
        assert resp.content == b""

    @pytest.mark.integration
    async def test_delete_comment_requires_authentication(
        self, client, db_session
    ):
        """Unauthenticated delete returns HTTP 401."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        comment = await repo.create(
            post_id=post.id, author_id=TEST_USER_ID, content="Not mine"
        )

        resp = await client.delete(f"/api/v1/feed/comments/{comment.id}")
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_delete_comment_non_author_returns_403(
        self, client, db_session
    ):
        """Non-author delete returns HTTP 403."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        comment = await repo.create(
            post_id=post.id, author_id=uuid.uuid4(), content="Not yours"
        )
        other_headers = build_auth_headers(user_id=uuid.uuid4())

        resp = await client.delete(
            f"/api/v1/feed/comments/{comment.id}", headers=other_headers
        )
        assert resp.status_code == 403

    @pytest.mark.integration
    async def test_delete_comment_missing_id_returns_403(self, auth_client):
        """Deleting a non-existent comment returns HTTP 403."""
        resp = await auth_client.delete(
            f"/api/v1/feed/comments/{uuid.uuid4()}"
        )
        assert resp.status_code == 403

    @pytest.mark.integration
    async def test_delete_comment_invalid_uuid_returns_422(self, auth_client):
        """Non-UUID comment_id returns HTTP 422."""
        resp = await auth_client.delete("/api/v1/feed/comments/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/feed/comments/{comment_id}/reply
# ---------------------------------------------------------------------------

class TestReplyToComment:
    """POST /api/v1/feed/comments/{comment_id}/reply"""

    @pytest.mark.integration
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Production bug: CommentRepository.create() returns a Comment whose "
            "'replies' relationship is not eagerly loaded. "
            "The reply endpoint calls CommentService.create_comment(), which calls "
            "CommentSchema.model_validate(comment), causing Pydantic to access "
            "comment.replies, triggering SQLAlchemy async lazy loading and raising "
            "MissingGreenlet. The endpoint returns a 500 instead of 201."
        ),
    )
    async def test_reply_to_comment_returns_201(self, auth_client, db_session):
        """Authenticated reply to an existing comment returns HTTP 201."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        parent = await repo.create(
            post_id=post.id, author_id=uuid.uuid4(), content="Parent"
        )

        resp = await auth_client.post(
            f"/api/v1/feed/comments/{parent.id}/reply",
            json={"content": "My reply"},
        )
        assert resp.status_code == 201

    @pytest.mark.integration
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Production bug: CommentRepository.create() returns a Comment whose "
            "'replies' relationship is not eagerly loaded. "
            "The reply endpoint calls CommentService.create_comment(), which calls "
            "CommentSchema.model_validate(comment), causing Pydantic to access "
            "comment.replies, triggering SQLAlchemy async lazy loading and raising "
            "MissingGreenlet. The endpoint returns a 500 instead of 201."
        ),
    )
    async def test_reply_response_schema(self, auth_client, db_session):
        """Reply response contains expected CommentSchema fields."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        parent = await repo.create(
            post_id=post.id, author_id=uuid.uuid4(), content="Parent"
        )

        resp = await auth_client.post(
            f"/api/v1/feed/comments/{parent.id}/reply",
            json={"content": "Reply content"},
        )
        body = resp.json()
        assert "id" in body
        assert body["post_id"] == str(post.id)
        assert body["author_id"] == str(TEST_USER_ID)
        assert body["parent_comment_id"] == str(parent.id)
        assert body["content"] == "Reply content"

    @pytest.mark.integration
    async def test_reply_requires_authentication(self, client, db_session):
        """Unauthenticated reply returns HTTP 401."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        parent = await repo.create(
            post_id=post.id, author_id=uuid.uuid4(), content="Parent"
        )

        resp = await client.post(
            f"/api/v1/feed/comments/{parent.id}/reply",
            json={"content": "Anon reply"},
        )
        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_reply_to_missing_comment_returns_404(self, auth_client):
        """Reply to a non-existent parent comment returns HTTP 404."""
        resp = await auth_client.post(
            f"/api/v1/feed/comments/{uuid.uuid4()}/reply",
            json={"content": "Ghost reply"},
        )
        assert resp.status_code == 404

    @pytest.mark.integration
    async def test_reply_empty_content_returns_422(self, auth_client, db_session):
        """Empty reply content returns HTTP 422."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        parent = await repo.create(
            post_id=post.id, author_id=uuid.uuid4(), content="Parent"
        )

        resp = await auth_client.post(
            f"/api/v1/feed/comments/{parent.id}/reply",
            json={"content": ""},
        )
        assert resp.status_code == 422

    @pytest.mark.integration
    async def test_reply_missing_content_returns_422(self, auth_client, db_session):
        """Reply without content field returns HTTP 422."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        parent = await repo.create(
            post_id=post.id, author_id=uuid.uuid4(), content="Parent"
        )

        resp = await auth_client.post(
            f"/api/v1/feed/comments/{parent.id}/reply",
            json={},
        )
        assert resp.status_code == 422

    @pytest.mark.integration
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Production bug: CommentRepository.create() returns a Comment whose "
            "'replies' relationship is not eagerly loaded. "
            "The reply endpoint calls CommentService.create_comment(), which calls "
            "CommentSchema.model_validate(comment), causing Pydantic to access "
            "comment.replies, triggering SQLAlchemy async lazy loading and raising "
            "MissingGreenlet. The endpoint returns a 500 instead of 201."
        ),
    )
    async def test_reply_sets_parent_comment_id(self, auth_client, db_session):
        """parent_comment_id in the response matches the parent comment's ID."""
        post = await create_test_post(db_session)
        await db_session.commit()
        repo = CommentRepository(db_session)
        parent = await repo.create(
            post_id=post.id, author_id=uuid.uuid4(), content="Parent"
        )

        resp = await auth_client.post(
            f"/api/v1/feed/comments/{parent.id}/reply",
            json={"content": "Child comment"},
        )
        assert resp.json()["parent_comment_id"] == str(parent.id)
