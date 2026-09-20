"""
CP-16E.4 — Discussion Endpoint / API Integration Tests

Tests the full HTTP request → FastAPI router → Service → Repository → SQLite stack
for the Discussions router (app/api/discussions.py).

Routes covered
--------------
GET    /api/v1/communities/{community_id}/discussions
POST   /api/v1/communities/{community_id}/discussions
GET    /api/v1/communities/discussions/{discussion_id}
PUT    /api/v1/communities/discussions/{discussion_id}
DELETE /api/v1/communities/discussions/{discussion_id}
POST   /api/v1/communities/discussions/{discussion_id}/comments
GET    /api/v1/communities/discussions/{discussion_id}/comments
PUT    /api/v1/communities/discussions/comments/{comment_id}
DELETE /api/v1/communities/discussions/comments/{comment_id}
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from tests.conftest import TEST_USER_ID, TEST_OTHER_USER_ID
from tests.utils import (
    build_auth_headers,
    make_community_payload,
    make_discussion_payload,
    make_discussion_comment_payload,
    create_test_community,
    create_test_member,
    create_test_discussion,
    create_test_comment,
)
from shared.constants.status import MemberRole, CommunityVisibility

BASE = "/api/v1/communities"


def _other_client(fastapi_app, user_id=None):
    headers = build_auth_headers(user_id=user_id or TEST_OTHER_USER_ID)
    return AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://testserver",
        headers=headers,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GET /{community_id}/discussions  — list discussions
# ═══════════════════════════════════════════════════════════════════════════════

class TestListDiscussions:

    async def test_list_discussions_empty(self, db_session, client: AsyncClient):
        """Community with no discussions returns empty list."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="List Disc Empty")
        await db_session.commit()
        response = await client.get(f"{BASE}/{comm.id}/discussions")
        assert response.status_code == 200
        data = response.json()
        assert data["discussions"] == []
        assert data["total"] == 0

    async def test_list_discussions_community_not_found(self, client: AsyncClient):
        """Non-existent community returns 404."""
        response = await client.get(f"{BASE}/{uuid.uuid4()}/discussions")
        assert response.status_code == 404

    async def test_list_discussions_returns_created(self, auth_client: AsyncClient, db_session, client: AsyncClient):
        """Created discussion appears in the listing."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="List Disc Has One")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()

        await auth_client.post(
            f"{BASE}/{comm.id}/discussions",
            json=make_discussion_payload(title="Visible Discussion"),
        )
        response = await client.get(f"{BASE}/{comm.id}/discussions")
        assert response.status_code == 200
        titles = [d["title"] for d in response.json()["discussions"]]
        assert "Visible Discussion" in titles

    async def test_list_discussions_response_schema(self, db_session, client: AsyncClient):
        """Response has correct pagination fields."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="List Disc Schema")
        await db_session.commit()
        response = await client.get(f"{BASE}/{comm.id}/discussions")
        data = response.json()
        for field in ["discussions", "total", "limit", "offset", "has_more"]:
            assert field in data

    async def test_list_discussions_private_community_requires_membership(self, db_session, client: AsyncClient):
        """Listing discussions on private community without auth returns 403."""
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="List Disc Private",
            visibility=CommunityVisibility.PRIVATE,
        )
        await db_session.commit()
        response = await client.get(f"{BASE}/{comm.id}/discussions")
        assert response.status_code == 403

    async def test_list_discussions_pagination(self, auth_client: AsyncClient, db_session, client: AsyncClient):
        """Pagination params are respected."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="List Disc Paginate")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()
        for i in range(5):
            await auth_client.post(
                f"{BASE}/{comm.id}/discussions",
                json=make_discussion_payload(title=f"Discussion {i}"),
            )
        response = await client.get(f"{BASE}/{comm.id}/discussions?limit=2&offset=0")
        assert response.status_code == 200
        assert response.json()["limit"] == 2
        assert len(response.json()["discussions"]) <= 2


# ═══════════════════════════════════════════════════════════════════════════════
# POST /{community_id}/discussions  — create discussion
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateDiscussion:

    async def test_member_can_create_discussion(self, auth_client: AsyncClient, db_session):
        """Active member can create a discussion; 201 returned."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Create Disc OK")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()
        response = await auth_client.post(
            f"{BASE}/{comm.id}/discussions",
            json=make_discussion_payload(title="Great Hike Routes"),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Great Hike Routes"
        assert str(data["author_id"]) == str(TEST_USER_ID)
        assert str(data["community_id"]) == str(comm.id)

    async def test_non_member_cannot_create_discussion(self, app, db_session):
        """Non-member gets 403."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Create Disc Non-Member")
        await db_session.commit()
        async with _other_client(app) as c:
            response = await c.post(
                f"{BASE}/{comm.id}/discussions",
                json=make_discussion_payload(),
            )
        assert response.status_code == 403

    async def test_unauthenticated_cannot_create_discussion(self, db_session, client: AsyncClient):
        """Unauthenticated request returns 401 or 403."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Create Disc Unauth")
        await db_session.commit()
        response = await client.post(
            f"{BASE}/{comm.id}/discussions",
            json=make_discussion_payload(),
        )
        assert response.status_code in (401, 403)

    async def test_create_discussion_community_not_found(self, auth_client: AsyncClient):
        """Non-member creating discussion in non-existent community gets 403.
        The service's _require_active_member fires before the community existence
        check returns 404, so the authenticated non-member sees 403."""
        response = await auth_client.post(
            f"{BASE}/{uuid.uuid4()}/discussions",
            json=make_discussion_payload(),
        )
        assert response.status_code == 403

    async def test_create_discussion_title_too_short(self, auth_client: AsyncClient, db_session):
        """Title shorter than 3 chars returns 422."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Create Disc Short Title")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()
        response = await auth_client.post(
            f"{BASE}/{comm.id}/discussions",
            json=make_discussion_payload(title="Hi"),
        )
        assert response.status_code == 422

    async def test_create_discussion_schema_fields(self, auth_client: AsyncClient, db_session):
        """Response includes expected schema fields."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Create Disc Fields")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()
        response = await auth_client.post(
            f"{BASE}/{comm.id}/discussions",
            json=make_discussion_payload(title="Fields Check"),
        )
        data = response.json()
        for field in ["id", "community_id", "author_id", "title", "content",
                      "comment_count", "is_deleted", "created_at", "updated_at"]:
            assert field in data


# ═══════════════════════════════════════════════════════════════════════════════
# GET /discussions/{discussion_id}  — get discussion
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetDiscussion:

    async def test_get_discussion_success(self, auth_client: AsyncClient, db_session, client: AsyncClient):
        """Existing discussion can be fetched by ID."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Get Disc Comm")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/{comm.id}/discussions",
            json=make_discussion_payload(title="Fetchable Discussion"),
        )
        disc_id = create_resp.json()["id"]
        response = await client.get(f"{BASE}/discussions/{disc_id}")
        assert response.status_code == 200
        assert response.json()["id"] == disc_id

    async def test_get_discussion_not_found(self, client: AsyncClient):
        """Non-existent discussion returns 404."""
        response = await client.get(f"{BASE}/discussions/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_get_discussion_private_community_unauthenticated(self, db_session, client: AsyncClient):
        """Discussion in private community not visible without auth."""
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="Get Disc Private",
            visibility=CommunityVisibility.PRIVATE,
        )
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        response = await client.get(f"{BASE}/discussions/{disc.id}")
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# PUT /discussions/{discussion_id}  — update discussion
# ═══════════════════════════════════════════════════════════════════════════════

class TestUpdateDiscussion:

    async def test_author_can_update_own_discussion(self, auth_client: AsyncClient, db_session):
        """Author can update their own discussion."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Update Disc Author")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/{comm.id}/discussions",
            json=make_discussion_payload(title="Original Title"),
        )
        disc_id = create_resp.json()["id"]
        response = await auth_client.put(
            f"{BASE}/discussions/{disc_id}",
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    async def test_moderator_can_update_any_discussion(self, auth_client: AsyncClient, db_session):
        """Moderator can update any discussion in the community."""
        from app.core.main import app as fastapi_app

        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Update Disc Mod")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MODERATOR)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/{comm.id}/discussions",
            json=make_discussion_payload(title="Author Title"),
        )
        disc_id = create_resp.json()["id"]

        mod_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app),
            base_url="http://testserver",
            headers=mod_headers,
        ) as c:
            response = await c.put(f"{BASE}/discussions/{disc_id}", json={"title": "Mod Edited"})
        assert response.status_code == 200

    async def test_non_author_non_mod_cannot_update(self, app, db_session):
        """Non-author, non-moderator gets 403."""
        third_id = uuid.UUID("c0000000-0000-0000-0000-000000000009")
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Update Disc Guard")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await create_test_member(db_session, community_id=comm.id, user_id=third_id, role=MemberRole.MEMBER)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()

        async with _other_client(app) as c:
            response = await c.put(f"{BASE}/discussions/{disc.id}", json={"title": "Stolen"})
        assert response.status_code == 403

    async def test_update_discussion_not_found(self, auth_client: AsyncClient):
        """Update on non-existent discussion returns 404."""
        response = await auth_client.put(
            f"{BASE}/discussions/{uuid.uuid4()}",
            json={"title": "Ghost"},
        )
        assert response.status_code == 404

    async def test_update_discussion_unauthenticated(self, db_session, client: AsyncClient):
        """Unauthenticated update returns 401 or 403."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Update Disc Unauth")
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        response = await client.put(f"{BASE}/discussions/{disc.id}", json={"title": "Hacked"})
        assert response.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE /discussions/{discussion_id}  — delete discussion
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeleteDiscussion:

    async def test_author_can_delete_own_discussion(self, auth_client: AsyncClient, db_session):
        """Author can delete their own discussion; 204 returned."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Delete Disc Author")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/{comm.id}/discussions",
            json=make_discussion_payload(title="To Delete"),
        )
        disc_id = create_resp.json()["id"]
        response = await auth_client.delete(f"{BASE}/discussions/{disc_id}")
        assert response.status_code == 204

    async def test_moderator_can_delete_any_discussion(self, auth_client: AsyncClient, db_session):
        """Moderator can delete any discussion."""
        from app.core.main import app as fastapi_app

        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Delete Disc Mod")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MODERATOR)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/{comm.id}/discussions",
            json=make_discussion_payload(title="Mod Will Delete"),
        )
        disc_id = create_resp.json()["id"]

        mod_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app),
            base_url="http://testserver",
            headers=mod_headers,
        ) as c:
            response = await c.delete(f"{BASE}/discussions/{disc_id}")
        assert response.status_code == 204

    async def test_non_author_regular_member_cannot_delete(self, app, db_session):
        """Regular non-author member cannot delete a discussion."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Delete Disc Guard")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()

        async with _other_client(app) as c:
            response = await c.delete(f"{BASE}/discussions/{disc.id}")
        assert response.status_code == 403

    async def test_delete_discussion_not_found(self, auth_client: AsyncClient):
        """Delete on non-existent discussion returns 404."""
        response = await auth_client.delete(f"{BASE}/discussions/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_delete_discussion_is_soft_delete(self, auth_client: AsyncClient, db_session):
        """Deleted discussion still exists in DB with is_deleted=True."""
        from app.repositories import DiscussionRepository

        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Delete Disc Soft")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/{comm.id}/discussions",
            json=make_discussion_payload(title="Soft Delete Check"),
        )
        disc_id = uuid.UUID(create_resp.json()["id"])
        await auth_client.delete(f"{BASE}/discussions/{disc_id}")
        repo = DiscussionRepository(db_session)
        disc = await repo.get_discussion_by_id(disc_id, include_deleted=True)
        assert disc is not None
        assert disc.is_deleted is True

    async def test_delete_discussion_unauthenticated(self, db_session, client: AsyncClient):
        """Unauthenticated delete returns 401 or 403."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Delete Disc Unauth")
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        response = await client.delete(f"{BASE}/discussions/{disc.id}")
        assert response.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# POST /discussions/{discussion_id}/comments  — create comment
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateComment:

    async def test_member_can_create_comment(self, auth_client: AsyncClient, db_session):
        """Active member can add a comment; 201 returned."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Create Comment OK")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        response = await auth_client.post(
            f"{BASE}/discussions/{disc.id}/comments",
            json=make_discussion_comment_payload(content="Great post!"),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Great post!"
        assert str(data["author_id"]) == str(TEST_USER_ID)
        assert str(data["discussion_id"]) == str(disc.id)

    async def test_non_member_cannot_create_comment(self, app, db_session):
        """Non-member gets 403 when trying to comment."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Create Comment Non-Member")
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        async with _other_client(app) as c:
            response = await c.post(
                f"{BASE}/discussions/{disc.id}/comments",
                json=make_discussion_comment_payload(),
            )
        assert response.status_code == 403

    async def test_unauthenticated_cannot_create_comment(self, db_session, client: AsyncClient):
        """Unauthenticated request returns 401 or 403."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Create Comment Unauth")
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        response = await client.post(
            f"{BASE}/discussions/{disc.id}/comments",
            json=make_discussion_comment_payload(),
        )
        assert response.status_code in (401, 403)

    async def test_create_comment_discussion_not_found(self, auth_client: AsyncClient):
        """Commenting on non-existent discussion returns 404."""
        response = await auth_client.post(
            f"{BASE}/discussions/{uuid.uuid4()}/comments",
            json=make_discussion_comment_payload(),
        )
        assert response.status_code == 404

    async def test_create_comment_empty_content_rejected(self, auth_client: AsyncClient, db_session):
        """Empty content is rejected with 422."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Create Comment Empty")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        response = await auth_client.post(
            f"{BASE}/discussions/{disc.id}/comments",
            json={"content": ""},
        )
        assert response.status_code == 422

    async def test_create_comment_increments_comment_count(self, auth_client: AsyncClient, db_session):
        """Adding a comment increments the discussion's comment_count."""
        from sqlalchemy import select
        from app.models.discussion import Discussion

        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Create Comment Count")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID, comment_count=0)
        await db_session.commit()
        await auth_client.post(
            f"{BASE}/discussions/{disc.id}/comments",
            json=make_discussion_comment_payload(),
        )
        # Re-query from DB to get the value committed by the HTTP request's session
        result = await db_session.execute(
            select(Discussion.comment_count).where(Discussion.id == disc.id)
        )
        count = result.scalar_one()
        assert count == 1


# ═══════════════════════════════════════════════════════════════════════════════
# GET /discussions/{discussion_id}/comments  — list comments
# ═══════════════════════════════════════════════════════════════════════════════

class TestListComments:

    async def test_list_comments_empty(self, db_session, client: AsyncClient):
        """Discussion with no comments returns empty list."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="List Comments Empty")
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        response = await client.get(f"{BASE}/discussions/{disc.id}/comments")
        assert response.status_code == 200
        data = response.json()
        assert data["comments"] == []
        assert data["total"] == 0

    async def test_list_comments_returns_added(self, auth_client: AsyncClient, db_session, client: AsyncClient):
        """Added comment appears in the listing."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="List Comments Has One")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        await auth_client.post(
            f"{BASE}/discussions/{disc.id}/comments",
            json=make_discussion_comment_payload(content="Hello world"),
        )
        response = await client.get(f"{BASE}/discussions/{disc.id}/comments")
        assert response.status_code == 200
        contents = [c["content"] for c in response.json()["comments"]]
        assert "Hello world" in contents

    async def test_list_comments_discussion_not_found(self, client: AsyncClient):
        """Non-existent discussion returns 404."""
        response = await client.get(f"{BASE}/discussions/{uuid.uuid4()}/comments")
        assert response.status_code == 404

    async def test_list_comments_private_community_unauthenticated(self, db_session, client: AsyncClient):
        """Comments on a private community discussion are blocked without auth."""
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="List Comments Private",
            visibility=CommunityVisibility.PRIVATE,
        )
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        response = await client.get(f"{BASE}/discussions/{disc.id}/comments")
        assert response.status_code == 403

    async def test_list_comments_response_schema(self, db_session, client: AsyncClient):
        """Response has correct pagination fields."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="List Comments Schema")
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        response = await client.get(f"{BASE}/discussions/{disc.id}/comments")
        data = response.json()
        for field in ["comments", "total", "limit", "offset", "has_more"]:
            assert field in data

    async def test_list_comments_pagination(self, auth_client: AsyncClient, db_session, client: AsyncClient):
        """Pagination params are respected."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="List Comments Paginate")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        for i in range(4):
            await auth_client.post(
                f"{BASE}/discussions/{disc.id}/comments",
                json=make_discussion_comment_payload(content=f"Comment {i}"),
            )
        response = await client.get(f"{BASE}/discussions/{disc.id}/comments?limit=2&offset=0")
        assert response.status_code == 200
        assert response.json()["limit"] == 2
        assert len(response.json()["comments"]) <= 2


# ═══════════════════════════════════════════════════════════════════════════════
# PUT /discussions/comments/{comment_id}  — update comment
# ═══════════════════════════════════════════════════════════════════════════════

class TestUpdateComment:

    async def test_author_can_update_own_comment(self, auth_client: AsyncClient, db_session):
        """Author can update their own comment."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Update Comment Author")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/discussions/{disc.id}/comments",
            json=make_discussion_comment_payload(content="Original comment"),
        )
        comment_id = create_resp.json()["id"]
        response = await auth_client.put(
            f"{BASE}/discussions/comments/{comment_id}",
            json={"content": "Updated comment"},
        )
        assert response.status_code == 200
        assert response.json()["content"] == "Updated comment"

    async def test_moderator_can_update_any_comment(self, auth_client: AsyncClient, db_session):
        """Moderator can update any comment."""
        from app.core.main import app as fastapi_app

        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Update Comment Mod")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MODERATOR)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/discussions/{disc.id}/comments",
            json=make_discussion_comment_payload(content="Mod Will Edit"),
        )
        comment_id = create_resp.json()["id"]

        mod_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app),
            base_url="http://testserver",
            headers=mod_headers,
        ) as c:
            response = await c.put(
                f"{BASE}/discussions/comments/{comment_id}",
                json={"content": "Mod edited"},
            )
        assert response.status_code == 200

    async def test_non_author_regular_member_cannot_update_comment(self, auth_client: AsyncClient, db_session):
        """Regular member (non-author) cannot update another's comment."""
        from app.core.main import app as fastapi_app

        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Update Comment Guard")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/discussions/{disc.id}/comments",
            json=make_discussion_comment_payload(content="Owner comment"),
        )
        comment_id = create_resp.json()["id"]

        async with _other_client(fastapi_app) as c:
            response = await c.put(
                f"{BASE}/discussions/comments/{comment_id}",
                json={"content": "Stolen edit"},
            )
        assert response.status_code == 403

    async def test_update_comment_not_found(self, auth_client: AsyncClient):
        """Update on non-existent comment returns 404."""
        response = await auth_client.put(
            f"{BASE}/discussions/comments/{uuid.uuid4()}",
            json={"content": "Ghost edit"},
        )
        assert response.status_code == 404

    async def test_update_comment_unauthenticated(self, db_session, client: AsyncClient):
        """Unauthenticated update returns 401 or 403."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Update Comment Unauth")
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        comment = await create_test_comment(db_session, discussion_id=disc.id, author_id=TEST_USER_ID)
        await db_session.commit()
        response = await client.put(
            f"{BASE}/discussions/comments/{comment.id}",
            json={"content": "Hacked"},
        )
        assert response.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE /discussions/comments/{comment_id}  — delete comment
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeleteComment:

    async def test_author_can_delete_own_comment(self, auth_client: AsyncClient, db_session):
        """Author can delete their own comment; 204 returned."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Delete Comment Author")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/discussions/{disc.id}/comments",
            json=make_discussion_comment_payload(content="To delete"),
        )
        comment_id = create_resp.json()["id"]
        response = await auth_client.delete(f"{BASE}/discussions/comments/{comment_id}")
        assert response.status_code == 204

    async def test_moderator_can_delete_any_comment(self, auth_client: AsyncClient, db_session):
        """Moderator can delete any comment."""
        from app.core.main import app as fastapi_app

        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Delete Comment Mod")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MODERATOR)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/discussions/{disc.id}/comments",
            json=make_discussion_comment_payload(content="Mod will delete"),
        )
        comment_id = create_resp.json()["id"]

        mod_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app),
            base_url="http://testserver",
            headers=mod_headers,
        ) as c:
            response = await c.delete(f"{BASE}/discussions/comments/{comment_id}")
        assert response.status_code == 204

    async def test_non_author_regular_member_cannot_delete_comment(self, auth_client: AsyncClient, db_session):
        """Regular member cannot delete another's comment."""
        from app.core.main import app as fastapi_app

        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Delete Comment Guard")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/discussions/{disc.id}/comments",
            json=make_discussion_comment_payload(content="Owner comment"),
        )
        comment_id = create_resp.json()["id"]

        async with _other_client(fastapi_app) as c:
            response = await c.delete(f"{BASE}/discussions/comments/{comment_id}")
        assert response.status_code == 403

    async def test_delete_comment_not_found(self, auth_client: AsyncClient):
        """Delete on non-existent comment returns 404."""
        response = await auth_client.delete(f"{BASE}/discussions/comments/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_delete_comment_is_soft_delete(self, auth_client: AsyncClient, db_session):
        """Deleted comment still exists in DB with is_deleted=True."""
        from app.repositories import DiscussionRepository

        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Delete Comment Soft")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/discussions/{disc.id}/comments",
            json=make_discussion_comment_payload(content="Soft delete check"),
        )
        comment_id = uuid.UUID(create_resp.json()["id"])
        await auth_client.delete(f"{BASE}/discussions/comments/{comment_id}")
        repo = DiscussionRepository(db_session)
        comment = await repo.get_comment_by_id(comment_id, include_deleted=True)
        assert comment is not None
        assert comment.is_deleted is True

    async def test_delete_comment_decrements_comment_count(self, auth_client: AsyncClient, db_session):
        """Deleting a comment decrements the discussion's comment_count."""
        from app.repositories import DiscussionRepository

        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Delete Comment Count")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID, comment_count=0)
        await db_session.commit()
        create_resp = await auth_client.post(
            f"{BASE}/discussions/{disc.id}/comments",
            json=make_discussion_comment_payload(content="Will be removed"),
        )
        comment_id = create_resp.json()["id"]
        await auth_client.delete(f"{BASE}/discussions/comments/{comment_id}")

        repo = DiscussionRepository(db_session)
        updated = await repo.get_discussion_by_id(disc.id)
        assert updated.comment_count == 0

    async def test_delete_comment_unauthenticated(self, db_session, client: AsyncClient):
        """Unauthenticated delete returns 401 or 403."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Delete Comment Unauth")
        disc = await create_test_discussion(db_session, community_id=comm.id, author_id=TEST_USER_ID)
        comment = await create_test_comment(db_session, discussion_id=disc.id, author_id=TEST_USER_ID)
        await db_session.commit()
        response = await client.delete(f"{BASE}/discussions/comments/{comment.id}")
        assert response.status_code in (401, 403)
