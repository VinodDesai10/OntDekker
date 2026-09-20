"""
CP-16E.4 — Community Endpoint / API Integration Tests

Tests the full HTTP request → FastAPI router → Service → Repository → SQLite stack
for the Communities router (app/api/communities.py) and the Media router
(app/api/media.py, auth/404 only — MinIO not available in test environment).

Routes covered
--------------
POST   /api/v1/communities/
GET    /api/v1/communities/
GET    /api/v1/communities/{community_id}
PUT    /api/v1/communities/{community_id}
DELETE /api/v1/communities/{community_id}
GET    /api/v1/communities/{community_id}/rules
POST   /api/v1/communities/{community_id}/rules
PUT    /api/v1/communities/rules/{rule_id}
DELETE /api/v1/communities/rules/{rule_id}
POST   /api/v1/communities/{community_id}/logo/upload-url   (auth/404 only)
PUT    /api/v1/communities/{community_id}/logo              (auth/404 only)
POST   /api/v1/communities/{community_id}/banner/upload-url (auth/404 only)
PUT    /api/v1/communities/{community_id}/banner            (auth/404 only)
"""

import uuid
import pytest
from httpx import AsyncClient

from tests.conftest import TEST_USER_ID, TEST_OTHER_USER_ID
from tests.utils import (
    build_auth_headers,
    make_community_payload,
    make_community_update_payload,
    make_rule_payload,
    create_test_community,
    create_test_member,
)
from shared.constants.status import CommunityVisibility, MemberRole, MembershipStatus

BASE = "/api/v1/communities"


# ═══════════════════════════════════════════════════════════════════════════════
# POST /  — create community
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateCommunity:

    async def test_create_community_success(self, auth_client: AsyncClient):
        """Authenticated user can create a community; 201 returned with full schema."""
        payload = make_community_payload(name="Alpine Explorers")
        response = await auth_client.post(f"{BASE}/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Alpine Explorers"
        assert "id" in data
        assert "slug" in data
        assert data["creator_id"] == str(TEST_USER_ID)
        assert data["visibility"] == "PUBLIC"
        assert data["requires_approval"] is False
        assert data["is_deleted"] is False

    async def test_create_community_unauthenticated(self, client: AsyncClient):
        """Unauthenticated request to create community returns 401 or 403."""
        payload = make_community_payload(name="No Auth Community")
        response = await client.post(f"{BASE}/", json=payload)
        assert response.status_code in (401, 403)

    async def test_create_community_private(self, auth_client: AsyncClient):
        """Can create a private community."""
        payload = make_community_payload(
            name="Secret Hikers",
            visibility="PRIVATE",
            requires_approval=True,
        )
        response = await auth_client.post(f"{BASE}/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["visibility"] == "PRIVATE"
        assert data["requires_approval"] is True

    async def test_create_community_name_too_short(self, auth_client: AsyncClient):
        """Name shorter than 3 chars is rejected with 422."""
        payload = make_community_payload(name="Hi")
        response = await auth_client.post(f"{BASE}/", json=payload)
        assert response.status_code == 422

    async def test_create_community_name_missing(self, auth_client: AsyncClient):
        """Missing name field returns 422."""
        response = await auth_client.post(f"{BASE}/", json={"description": "no name"})
        assert response.status_code == 422

    async def test_create_community_duplicate_name_allowed_unique_slug(self, auth_client: AsyncClient):
        """Same name creates two communities with distinct slugs (names are not unique)."""
        payload = make_community_payload(name="Duplicate Community Test")
        r1 = await auth_client.post(f"{BASE}/", json=payload)
        assert r1.status_code == 201
        r2 = await auth_client.post(f"{BASE}/", json=payload)
        assert r2.status_code == 201
        # Slugs must be distinct even though names are the same
        assert r1.json()["slug"] != r2.json()["slug"]

    async def test_create_community_with_location(self, auth_client: AsyncClient):
        """Location field is persisted correctly."""
        payload = make_community_payload(name="Dutch Cyclists", location="Amsterdam, NL")
        response = await auth_client.post(f"{BASE}/", json=payload)
        assert response.status_code == 201
        assert response.json()["location"] == "Amsterdam, NL"

    async def test_create_community_creator_is_owner(self, auth_client: AsyncClient, db_session):
        """After creation, the creator should be an active OWNER member."""
        from app.repositories import MembershipRepository
        payload = make_community_payload(name="Ownership Check Community")
        response = await auth_client.post(f"{BASE}/", json=payload)
        assert response.status_code == 201
        community_id = uuid.UUID(response.json()["id"])
        repo = MembershipRepository(db_session)
        member = await repo.get_active_member(community_id, TEST_USER_ID)
        assert member is not None
        assert member.role == MemberRole.OWNER


# ═══════════════════════════════════════════════════════════════════════════════
# GET /  — list communities
# ═══════════════════════════════════════════════════════════════════════════════

class TestListCommunities:

    async def test_list_communities_empty(self, client: AsyncClient):
        """Empty DB returns empty list with total=0."""
        response = await client.get(f"{BASE}/")
        assert response.status_code == 200
        data = response.json()
        assert data["communities"] == []
        assert data["total"] == 0

    async def test_list_communities_returns_created(self, auth_client: AsyncClient, client: AsyncClient):
        """Created community appears in the list."""
        await auth_client.post(f"{BASE}/", json=make_community_payload(name="Listed Community"))
        response = await client.get(f"{BASE}/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        names = [c["name"] for c in data["communities"]]
        assert "Listed Community" in names

    async def test_list_communities_pagination(self, auth_client: AsyncClient, client: AsyncClient):
        """Pagination params limit and offset work correctly."""
        for i in range(5):
            await auth_client.post(f"{BASE}/", json=make_community_payload(name=f"Paginate Community {i}"))
        r1 = await client.get(f"{BASE}/?limit=2&offset=0")
        assert r1.status_code == 200
        d1 = r1.json()
        assert len(d1["communities"]) <= 2
        assert d1["limit"] == 2
        assert d1["offset"] == 0

    async def test_list_communities_search(self, auth_client: AsyncClient, client: AsyncClient):
        """Search by name returns matching communities."""
        await auth_client.post(f"{BASE}/", json=make_community_payload(name="Unique Search XYZ"))
        response = await client.get(f"{BASE}/?search=Unique+Search+XYZ")
        assert response.status_code == 200
        data = response.json()
        assert any("Unique Search XYZ" in c["name"] for c in data["communities"])

    async def test_list_communities_visibility_filter(self, auth_client: AsyncClient, client: AsyncClient):
        """Visibility filter returns only matching communities."""
        await auth_client.post(f"{BASE}/", json=make_community_payload(name="Public Vis Comm", visibility="PUBLIC"))
        response = await client.get(f"{BASE}/?visibility=PUBLIC")
        assert response.status_code == 200
        data = response.json()
        for c in data["communities"]:
            assert c["visibility"] == "PUBLIC"

    async def test_list_communities_response_schema(self, auth_client: AsyncClient, client: AsyncClient):
        """Response contains expected top-level fields."""
        await auth_client.post(f"{BASE}/", json=make_community_payload(name="Schema Check Comm"))
        response = await client.get(f"{BASE}/")
        assert response.status_code == 200
        data = response.json()
        assert "communities" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data


# ═══════════════════════════════════════════════════════════════════════════════
# GET /{community_id}  — get community by ID
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetCommunity:

    async def test_get_community_success(self, auth_client: AsyncClient, client: AsyncClient):
        """Existing public community can be fetched by ID."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Fetchable Comm"))
        community_id = create_resp.json()["id"]
        response = await client.get(f"{BASE}/{community_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == community_id
        assert data["name"] == "Fetchable Comm"

    async def test_get_community_not_found(self, client: AsyncClient):
        """Non-existent community ID returns 404."""
        fake_id = uuid.uuid4()
        response = await client.get(f"{BASE}/{fake_id}")
        assert response.status_code == 404

    async def test_get_community_private_unauthenticated(self, auth_client: AsyncClient, client: AsyncClient):
        """Private community is not accessible to unauthenticated users."""
        create_resp = await auth_client.post(
            f"{BASE}/", json=make_community_payload(name="Secret Community", visibility="PRIVATE")
        )
        community_id = create_resp.json()["id"]
        response = await client.get(f"{BASE}/{community_id}")
        assert response.status_code == 403

    async def test_get_community_private_non_member(self, auth_client: AsyncClient, client: AsyncClient):
        """Private community is not accessible to a non-member authenticated user."""
        create_resp = await auth_client.post(
            f"{BASE}/", json=make_community_payload(name="Members Only", visibility="PRIVATE")
        )
        community_id = create_resp.json()["id"]
        other_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        response = await client.get(f"{BASE}/{community_id}", headers=other_headers)
        assert response.status_code == 403

    async def test_get_community_private_member_can_access(self, auth_client: AsyncClient, db_session):
        """Private community member can access it."""
        create_resp = await auth_client.post(
            f"{BASE}/", json=make_community_payload(name="Private Access OK", visibility="PRIVATE")
        )
        assert create_resp.status_code == 201
        community_id = uuid.UUID(create_resp.json()["id"])
        # Add another user as an active member directly
        await create_test_member(db_session, community_id=community_id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()
        other_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        from httpx import AsyncClient as AC, ASGITransport
        from app.core.main import app as fastapi_app
        async with AC(transport=ASGITransport(app=fastapi_app), base_url="http://testserver", headers=other_headers) as c:
            response = await c.get(f"{BASE}/{community_id}")
        assert response.status_code == 200

    async def test_get_community_includes_is_member_for_auth_user(self, auth_client: AsyncClient):
        """Creator gets is_member=True in their own community."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Member Flag Comm"))
        community_id = create_resp.json()["id"]
        response = await auth_client.get(f"{BASE}/{community_id}")
        assert response.status_code == 200
        assert response.json()["is_member"] is True

    async def test_get_community_schema_fields(self, auth_client: AsyncClient):
        """Response includes all expected schema fields."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Schema Fields Comm"))
        community_id = create_resp.json()["id"]
        response = await auth_client.get(f"{BASE}/{community_id}")
        data = response.json()
        for field in ["id", "name", "slug", "creator_id", "status", "visibility",
                      "requires_approval", "member_count", "is_deleted",
                      "rules", "is_member", "created_at", "updated_at"]:
            assert field in data, f"Missing field: {field}"


# ═══════════════════════════════════════════════════════════════════════════════
# PUT /{community_id}  — update community
# ═══════════════════════════════════════════════════════════════════════════════

class TestUpdateCommunity:

    async def test_update_community_success(self, auth_client: AsyncClient):
        """Owner can update community name."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Old Name"))
        community_id = create_resp.json()["id"]
        response = await auth_client.put(
            f"{BASE}/{community_id}", json=make_community_update_payload(name="New Name")
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    async def test_update_community_unauthenticated(self, auth_client: AsyncClient, client: AsyncClient):
        """Unauthenticated update returns 401 or 403."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Unauth Update"))
        community_id = create_resp.json()["id"]
        response = await client.put(f"{BASE}/{community_id}", json=make_community_update_payload(name="Hacked"))
        assert response.status_code in (401, 403)

    async def test_update_community_non_owner_forbidden(self, auth_client: AsyncClient):
        """Non-owner authenticated user cannot update the community."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Owner Guard Comm"))
        community_id = create_resp.json()["id"]
        other_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        from httpx import AsyncClient as AC, ASGITransport
        from app.core.main import app as fastapi_app
        async with AC(transport=ASGITransport(app=fastapi_app), base_url="http://testserver", headers=other_headers) as c:
            response = await c.put(f"{BASE}/{community_id}", json=make_community_update_payload(name="Stolen"))
        assert response.status_code == 403

    async def test_update_community_not_found(self, auth_client: AsyncClient):
        """Update on non-existent community returns 404."""
        response = await auth_client.put(f"{BASE}/{uuid.uuid4()}", json=make_community_update_payload(name="Ghost"))
        assert response.status_code == 404

    async def test_update_community_description(self, auth_client: AsyncClient):
        """Description can be updated independently."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Desc Updater"))
        community_id = create_resp.json()["id"]
        response = await auth_client.put(
            f"{BASE}/{community_id}",
            json=make_community_update_payload(description="Updated description text."),
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Updated description text."

    async def test_update_community_visibility(self, auth_client: AsyncClient):
        """Owner can change visibility from PUBLIC to PRIVATE."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Vis Changer"))
        community_id = create_resp.json()["id"]
        response = await auth_client.put(
            f"{BASE}/{community_id}",
            json=make_community_update_payload(visibility="PRIVATE"),
        )
        assert response.status_code == 200
        assert response.json()["visibility"] == "PRIVATE"


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE /{community_id}  — delete community
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeleteCommunity:

    async def test_delete_community_success(self, auth_client: AsyncClient):
        """Owner can soft-delete a community; 204 returned."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="To Be Deleted"))
        community_id = create_resp.json()["id"]
        response = await auth_client.delete(f"{BASE}/{community_id}")
        assert response.status_code == 204

    async def test_delete_community_unauthenticated(self, auth_client: AsyncClient, client: AsyncClient):
        """Unauthenticated delete returns 401 or 403."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Delete Unauth"))
        community_id = create_resp.json()["id"]
        response = await client.delete(f"{BASE}/{community_id}")
        assert response.status_code in (401, 403)

    async def test_delete_community_non_owner_forbidden(self, auth_client: AsyncClient):
        """Non-owner cannot delete the community."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Delete Guard"))
        community_id = create_resp.json()["id"]
        other_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        from httpx import AsyncClient as AC, ASGITransport
        from app.core.main import app as fastapi_app
        async with AC(transport=ASGITransport(app=fastapi_app), base_url="http://testserver", headers=other_headers) as c:
            response = await c.delete(f"{BASE}/{community_id}")
        assert response.status_code == 403

    async def test_delete_community_not_found(self, auth_client: AsyncClient):
        """Delete on non-existent community returns 404."""
        response = await auth_client.delete(f"{BASE}/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_delete_community_is_soft_delete(self, auth_client: AsyncClient, db_session):
        """After soft-delete the community still exists in DB with is_deleted=True."""
        from app.repositories import CommunityRepository
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Soft Delete Test"))
        community_id = uuid.UUID(create_resp.json()["id"])
        await auth_client.delete(f"{BASE}/{community_id}")
        repo = CommunityRepository(db_session)
        community = await repo.get_by_id(community_id, include_deleted=True)
        assert community is not None
        assert community.is_deleted is True


# ═══════════════════════════════════════════════════════════════════════════════
# GET /{community_id}/rules  — list rules
# ═══════════════════════════════════════════════════════════════════════════════

class TestListRules:

    async def test_list_rules_empty(self, auth_client: AsyncClient, client: AsyncClient):
        """New community has no rules."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="No Rules Comm"))
        community_id = create_resp.json()["id"]
        response = await client.get(f"{BASE}/{community_id}/rules")
        assert response.status_code == 200
        data = response.json()
        assert data["rules"] == []
        assert data["total"] == 0

    async def test_list_rules_not_found(self, client: AsyncClient):
        """Rules for non-existent community returns 404."""
        response = await client.get(f"{BASE}/{uuid.uuid4()}/rules")
        assert response.status_code == 404

    async def test_list_rules_after_adding(self, auth_client: AsyncClient):
        """Rules appear in the listing after being added."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Rules Listed Comm"))
        community_id = create_resp.json()["id"]
        await auth_client.post(f"{BASE}/{community_id}/rules", json=make_rule_payload(title="Be kind", order_index=1))
        await auth_client.post(f"{BASE}/{community_id}/rules", json=make_rule_payload(title="No spam", order_index=2))
        response = await auth_client.get(f"{BASE}/{community_id}/rules")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        titles = [r["title"] for r in data["rules"]]
        assert "Be kind" in titles
        assert "No spam" in titles


# ═══════════════════════════════════════════════════════════════════════════════
# POST /{community_id}/rules  — add rule
# ═══════════════════════════════════════════════════════════════════════════════

class TestAddRule:

    async def test_add_rule_owner_success(self, auth_client: AsyncClient):
        """Community owner can add a rule; 201 returned."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Rule Owner Comm"))
        community_id = create_resp.json()["id"]
        response = await auth_client.post(
            f"{BASE}/{community_id}/rules",
            json=make_rule_payload(title="No trolling", order_index=1),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "No trolling"
        assert data["order_index"] == 1
        assert "id" in data
        assert str(data["community_id"]) == community_id

    async def test_add_rule_moderator_success(self, auth_client: AsyncClient, db_session):
        """Moderator can add a rule."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Rule Mod Comm"))
        community_id = uuid.UUID(create_resp.json()["id"])
        await create_test_member(db_session, community_id=community_id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MODERATOR)
        await db_session.commit()
        mod_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        from httpx import AsyncClient as AC, ASGITransport
        from app.core.main import app as fastapi_app
        async with AC(transport=ASGITransport(app=fastapi_app), base_url="http://testserver", headers=mod_headers) as c:
            response = await c.post(f"{BASE}/{community_id}/rules", json=make_rule_payload(title="Mod rule", order_index=1))
        assert response.status_code == 201

    async def test_add_rule_regular_member_forbidden(self, auth_client: AsyncClient, db_session):
        """Regular member cannot add a rule."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Rule Member Guard"))
        community_id = uuid.UUID(create_resp.json()["id"])
        await create_test_member(db_session, community_id=community_id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()
        member_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        from httpx import AsyncClient as AC, ASGITransport
        from app.core.main import app as fastapi_app
        async with AC(transport=ASGITransport(app=fastapi_app), base_url="http://testserver", headers=member_headers) as c:
            response = await c.post(f"{BASE}/{community_id}/rules", json=make_rule_payload())
        assert response.status_code == 403

    async def test_add_rule_unauthenticated(self, auth_client: AsyncClient, client: AsyncClient):
        """Unauthenticated user cannot add a rule."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Rule Unauth"))
        community_id = create_resp.json()["id"]
        response = await client.post(f"{BASE}/{community_id}/rules", json=make_rule_payload())
        assert response.status_code in (401, 403)

    async def test_add_rule_community_not_found(self, auth_client: AsyncClient):
        """Adding rule to non-existent community returns 404."""
        response = await auth_client.post(f"{BASE}/{uuid.uuid4()}/rules", json=make_rule_payload())
        assert response.status_code == 404

    async def test_add_rule_title_too_short(self, auth_client: AsyncClient):
        """Rule title shorter than 3 chars is rejected with 422."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Rule Short Title"))
        community_id = create_resp.json()["id"]
        response = await auth_client.post(
            f"{BASE}/{community_id}/rules",
            json=make_rule_payload(title="AB"),
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# PUT /rules/{rule_id}  — update rule
# ═══════════════════════════════════════════════════════════════════════════════

class TestUpdateRule:

    async def test_update_rule_owner_success(self, auth_client: AsyncClient):
        """Owner can update a rule."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Rule Update Comm"))
        community_id = create_resp.json()["id"]
        add_resp = await auth_client.post(
            f"{BASE}/{community_id}/rules",
            json=make_rule_payload(title="Original Rule"),
        )
        rule_id = add_resp.json()["id"]
        response = await auth_client.put(
            f"{BASE}/rules/{rule_id}",
            json={"title": "Updated Rule Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Rule Title"

    async def test_update_rule_non_member_forbidden(self, auth_client: AsyncClient):
        """Non-member cannot update a rule."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Rule Update Guard"))
        community_id = create_resp.json()["id"]
        add_resp = await auth_client.post(
            f"{BASE}/{community_id}/rules",
            json=make_rule_payload(title="Protected Rule"),
        )
        rule_id = add_resp.json()["id"]
        other_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        from httpx import AsyncClient as AC, ASGITransport
        from app.core.main import app as fastapi_app
        async with AC(transport=ASGITransport(app=fastapi_app), base_url="http://testserver", headers=other_headers) as c:
            response = await c.put(f"{BASE}/rules/{rule_id}", json={"title": "Stolen Rule"})
        assert response.status_code == 403

    async def test_update_rule_not_found(self, auth_client: AsyncClient):
        """Update on non-existent rule returns 404."""
        response = await auth_client.put(f"{BASE}/rules/{uuid.uuid4()}", json={"title": "Ghost Rule"})
        assert response.status_code == 404

    async def test_update_rule_unauthenticated(self, auth_client: AsyncClient, client: AsyncClient):
        """Unauthenticated update returns 401 or 403."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Rule Unauth Update"))
        community_id = create_resp.json()["id"]
        add_resp = await auth_client.post(
            f"{BASE}/{community_id}/rules",
            json=make_rule_payload(title="Unauth Rule"),
        )
        rule_id = add_resp.json()["id"]
        response = await client.put(f"{BASE}/rules/{rule_id}", json={"title": "Hacked"})
        assert response.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE /rules/{rule_id}  — delete rule
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeleteRule:

    async def test_delete_rule_owner_success(self, auth_client: AsyncClient):
        """Owner can delete a rule; 204 returned."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Rule Delete Comm"))
        community_id = create_resp.json()["id"]
        add_resp = await auth_client.post(
            f"{BASE}/{community_id}/rules",
            json=make_rule_payload(title="To Be Removed"),
        )
        rule_id = add_resp.json()["id"]
        response = await auth_client.delete(f"{BASE}/rules/{rule_id}")
        assert response.status_code == 204

    async def test_delete_rule_disappears_from_listing(self, auth_client: AsyncClient):
        """Deleted rule no longer appears in list."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Rule Remove List"))
        community_id = create_resp.json()["id"]
        add_resp = await auth_client.post(
            f"{BASE}/{community_id}/rules",
            json=make_rule_payload(title="Ephemeral Rule"),
        )
        rule_id = add_resp.json()["id"]
        await auth_client.delete(f"{BASE}/rules/{rule_id}")
        list_resp = await auth_client.get(f"{BASE}/{community_id}/rules")
        titles = [r["title"] for r in list_resp.json()["rules"]]
        assert "Ephemeral Rule" not in titles

    async def test_delete_rule_non_member_forbidden(self, auth_client: AsyncClient):
        """Non-member cannot delete a rule."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Rule Del Guard"))
        community_id = create_resp.json()["id"]
        add_resp = await auth_client.post(
            f"{BASE}/{community_id}/rules",
            json=make_rule_payload(title="Guard Rule"),
        )
        rule_id = add_resp.json()["id"]
        other_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        from httpx import AsyncClient as AC, ASGITransport
        from app.core.main import app as fastapi_app
        async with AC(transport=ASGITransport(app=fastapi_app), base_url="http://testserver", headers=other_headers) as c:
            response = await c.delete(f"{BASE}/rules/{rule_id}")
        assert response.status_code == 403

    async def test_delete_rule_not_found(self, auth_client: AsyncClient):
        """Delete on non-existent rule returns 404."""
        response = await auth_client.delete(f"{BASE}/rules/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_delete_rule_unauthenticated(self, auth_client: AsyncClient, client: AsyncClient):
        """Unauthenticated delete returns 401 or 403."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Rule Del Unauth"))
        community_id = create_resp.json()["id"]
        add_resp = await auth_client.post(
            f"{BASE}/{community_id}/rules",
            json=make_rule_payload(title="Unauth Del Rule"),
        )
        rule_id = add_resp.json()["id"]
        response = await client.delete(f"{BASE}/rules/{rule_id}")
        assert response.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# Media endpoints — auth/404 only (MinIO not available in test environment)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMediaEndpointsAuthAndNotFound:
    """
    Media endpoints require MinIO for presigned URL generation.
    These tests verify authentication enforcement and 404 handling only.
    Presigned URL generation (which contacts MinIO) is NOT tested.
    """

    async def test_logo_upload_url_unauthenticated(self, auth_client: AsyncClient, client: AsyncClient):
        """Logo upload URL endpoint requires authentication."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Logo Unauth Comm"))
        community_id = create_resp.json()["id"]
        payload = {"filename": "logo.jpg", "content_type": "image/jpeg"}
        response = await client.post(f"{BASE}/{community_id}/logo/upload-url", json=payload)
        assert response.status_code in (401, 403)

    async def test_banner_upload_url_unauthenticated(self, auth_client: AsyncClient, client: AsyncClient):
        """Banner upload URL endpoint requires authentication."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Banner Unauth Comm"))
        community_id = create_resp.json()["id"]
        payload = {"filename": "banner.png", "content_type": "image/png"}
        response = await client.post(f"{BASE}/{community_id}/banner/upload-url", json=payload)
        assert response.status_code in (401, 403)

    async def test_set_logo_unauthenticated(self, auth_client: AsyncClient, client: AsyncClient):
        """Set logo endpoint requires authentication."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Set Logo Unauth"))
        community_id = create_resp.json()["id"]
        response = await client.put(
            f"{BASE}/{community_id}/logo",
            json={"object_key": "communities/fake/logo/test.jpg"},
        )
        assert response.status_code in (401, 403)

    async def test_set_banner_unauthenticated(self, auth_client: AsyncClient, client: AsyncClient):
        """Set banner endpoint requires authentication."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Set Banner Unauth"))
        community_id = create_resp.json()["id"]
        response = await client.put(
            f"{BASE}/{community_id}/banner",
            json={"object_key": "communities/fake/banner/test.jpg"},
        )
        assert response.status_code in (401, 403)

    async def test_logo_upload_url_non_owner_forbidden(self, auth_client: AsyncClient, db_session):
        """Non-owner cannot get logo upload URL — 403 before MinIO is contacted."""
        create_resp = await auth_client.post(f"{BASE}/", json=make_community_payload(name="Logo Owner Guard"))
        community_id = uuid.UUID(create_resp.json()["id"])
        await create_test_member(db_session, community_id=community_id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()
        other_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        from httpx import AsyncClient as AC, ASGITransport
        from app.core.main import app as fastapi_app
        async with AC(transport=ASGITransport(app=fastapi_app), base_url="http://testserver", headers=other_headers) as c:
            response = await c.post(
                f"{BASE}/{community_id}/logo/upload-url",
                json={"filename": "logo.jpg", "content_type": "image/jpeg"},
            )
        assert response.status_code == 403

    async def test_logo_upload_url_community_not_found(self, auth_client: AsyncClient):
        """Logo upload URL for non-existent community returns 404."""
        response = await auth_client.post(
            f"{BASE}/{uuid.uuid4()}/logo/upload-url",
            json={"filename": "logo.jpg", "content_type": "image/jpeg"},
        )
        assert response.status_code == 404

    async def test_banner_upload_url_community_not_found(self, auth_client: AsyncClient):
        """Banner upload URL for non-existent community returns 404."""
        response = await auth_client.post(
            f"{BASE}/{uuid.uuid4()}/banner/upload-url",
            json={"filename": "banner.jpg", "content_type": "image/jpeg"},
        )
        assert response.status_code == 404
