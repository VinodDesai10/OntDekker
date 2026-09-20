"""
CP-16E.4 — Membership Endpoint / API Integration Tests

Tests the full HTTP request → FastAPI router → Service → Repository → SQLite stack
for the Members router (app/api/members.py).

Routes covered
--------------
POST   /api/v1/communities/{community_id}/join
DELETE /api/v1/communities/{community_id}/leave
GET    /api/v1/communities/{community_id}/members
DELETE /api/v1/communities/{community_id}/members/{user_id}
PUT    /api/v1/communities/{community_id}/members/{user_id}/role
GET    /api/v1/communities/{community_id}/join-requests
PUT    /api/v1/communities/join-requests/{request_id}
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from tests.conftest import TEST_USER_ID, TEST_OTHER_USER_ID
from tests.utils import (
    build_auth_headers,
    make_community_payload,
    make_membership_payload,
    create_test_community,
    create_test_member,
)
from shared.constants.status import MemberRole, MembershipStatus, CommunityVisibility

BASE = "/api/v1/communities"


def _other_client(app, user_id=None):
    """Return an AsyncClient context manager using the test-wired app fixture."""
    headers = build_auth_headers(user_id=user_id or TEST_OTHER_USER_ID)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=headers,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# POST /{community_id}/join
# ═══════════════════════════════════════════════════════════════════════════════

class TestJoinCommunity:

    async def test_join_public_community_success(self, app, db_session):
        """Joining a public community returns joined=True and creates membership."""
        from app.repositories import MembershipRepository

        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Join Public")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()

        async with _other_client(app) as c:
            response = await c.post(f"{BASE}/{comm.id}/join", json=make_membership_payload())

        assert response.status_code == 200
        assert response.json()["joined"] is True

        repo = MembershipRepository(db_session)
        member = await repo.get_active_member(comm.id, TEST_OTHER_USER_ID)
        assert member is not None
        assert member.status == MembershipStatus.ACTIVE

    async def test_join_approval_required_community_creates_request(self, app, db_session):
        """Joining approval-required community creates a pending join request."""
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="Join Approval",
            requires_approval=True,
        )
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()

        async with _other_client(app) as c:
            response = await c.post(
                f"{BASE}/{comm.id}/join",
                json=make_membership_payload(message="Please let me in"),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["requested"] is True
        assert "request_id" in data

    async def test_join_private_community_creates_request(self, app, db_session):
        """Joining a PRIVATE community creates a join request."""
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="Join Private",
            visibility=CommunityVisibility.PRIVATE,
        )
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()

        async with _other_client(app) as c:
            response = await c.post(f"{BASE}/{comm.id}/join", json=make_membership_payload())

        assert response.status_code == 200
        assert response.json().get("requested") is True

    async def test_join_unauthenticated(self, db_session, client: AsyncClient):
        """Unauthenticated join attempt returns 401 or 403."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Join Unauth")
        await db_session.commit()
        response = await client.post(f"{BASE}/{comm.id}/join", json=make_membership_payload())
        assert response.status_code in (401, 403)

    async def test_join_community_not_found(self, auth_client: AsyncClient):
        """Joining non-existent community returns 404."""
        response = await auth_client.post(f"{BASE}/{uuid.uuid4()}/join", json=make_membership_payload())
        assert response.status_code == 404

    async def test_join_already_member_conflict(self, app, db_session):
        """Joining a community you are already a member of returns 409."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Join Already Member")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()

        async with _other_client(app) as c:
            response = await c.post(f"{BASE}/{comm.id}/join", json=make_membership_payload())

        assert response.status_code == 409

    async def test_join_member_count_incremented(self, app, db_session):
        """Member count is incremented after successful join."""
        from sqlalchemy import select
        from app.models.community import Community

        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="Join Count Test", member_count=1
        )
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()

        async with _other_client(app) as c:
            await c.post(f"{BASE}/{comm.id}/join", json=make_membership_payload())

        # Re-query from DB to get the value committed by the HTTP request's session
        result = await db_session.execute(
            select(Community.member_count).where(Community.id == comm.id)
        )
        count = result.scalar_one()
        assert count == 2


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE /{community_id}/leave
# ═══════════════════════════════════════════════════════════════════════════════

class TestLeaveCommunity:

    async def test_leave_community_success(self, app, db_session):
        """Active member can leave; 204 returned."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Leave Success")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()

        async with _other_client(app) as c:
            response = await c.delete(f"{BASE}/{comm.id}/leave")

        assert response.status_code == 204

    async def test_leave_sets_status_left(self, app, db_session):
        """After leaving, membership status is LEFT."""
        from app.repositories import MembershipRepository

        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Leave Status")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()

        async with _other_client(app) as c:
            await c.delete(f"{BASE}/{comm.id}/leave")

        repo = MembershipRepository(db_session)
        member = await repo.get_member(comm.id, TEST_OTHER_USER_ID)
        assert member.status == MembershipStatus.LEFT

    async def test_owner_cannot_leave(self, auth_client: AsyncClient, db_session):
        """Community owner cannot leave — returns 400."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Owner Leave Guard")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()
        response = await auth_client.delete(f"{BASE}/{comm.id}/leave")
        assert response.status_code == 400

    async def test_leave_not_member_returns_404(self, auth_client: AsyncClient, db_session):
        """Leaving a community you are not a member of returns 404."""
        comm = await create_test_community(db_session, creator_id=TEST_OTHER_USER_ID, name="Leave Not Member")
        await db_session.commit()
        response = await auth_client.delete(f"{BASE}/{comm.id}/leave")
        assert response.status_code == 404

    async def test_leave_unauthenticated(self, db_session, client: AsyncClient):
        """Unauthenticated leave returns 401 or 403."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Leave Unauth")
        await db_session.commit()
        response = await client.delete(f"{BASE}/{comm.id}/leave")
        assert response.status_code in (401, 403)

    async def test_leave_community_not_found(self, auth_client: AsyncClient):
        """Leaving non-existent community returns 404."""
        response = await auth_client.delete(f"{BASE}/{uuid.uuid4()}/leave")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# GET /{community_id}/members
# ═══════════════════════════════════════════════════════════════════════════════

class TestListMembers:

    async def test_list_members_public_community(self, db_session, client: AsyncClient):
        """Public community member list is accessible without auth."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="List Members Public")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()
        response = await client.get(f"{BASE}/{comm.id}/members")
        assert response.status_code == 200
        data = response.json()
        assert "members" in data
        assert data["total"] >= 1

    async def test_list_members_private_unauthenticated(self, db_session, client: AsyncClient):
        """Private community member list is not visible to unauthenticated users."""
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="List Members Private",
            visibility=CommunityVisibility.PRIVATE,
        )
        await db_session.commit()
        response = await client.get(f"{BASE}/{comm.id}/members")
        assert response.status_code == 403

    async def test_list_members_private_non_member_forbidden(self, app, db_session):
        """Non-member cannot list private community members."""
        third_id = uuid.UUID("c0000000-0000-0000-0000-000000000003")
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="List Members Priv Guard",
            visibility=CommunityVisibility.PRIVATE,
        )
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()

        async with _other_client(app, user_id=third_id) as c:
            response = await c.get(f"{BASE}/{comm.id}/members")
        assert response.status_code == 403

    async def test_list_members_community_not_found(self, client: AsyncClient):
        """Non-existent community returns 404."""
        response = await client.get(f"{BASE}/{uuid.uuid4()}/members")
        assert response.status_code == 404

    async def test_list_members_response_schema(self, db_session, client: AsyncClient):
        """Response has correct pagination schema."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="List Members Schema")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()
        response = await client.get(f"{BASE}/{comm.id}/members")
        data = response.json()
        for field in ["members", "total", "limit", "offset", "has_more"]:
            assert field in data

    async def test_list_members_role_filter(self, db_session, client: AsyncClient):
        """Role filter returns only members with that role."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="List Members Role Filter")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()
        response = await client.get(f"{BASE}/{comm.id}/members?role=OWNER")
        assert response.status_code == 200
        data = response.json()
        for m in data["members"]:
            assert m["role"] == "OWNER"

    async def test_list_members_pagination(self, db_session, client: AsyncClient):
        """Pagination params are respected."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="List Members Paginate")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        for _ in range(3):
            await create_test_member(db_session, community_id=comm.id)
        await db_session.commit()
        response = await client.get(f"{BASE}/{comm.id}/members?limit=2&offset=0")
        assert response.status_code == 200
        assert response.json()["limit"] == 2
        assert len(response.json()["members"]) <= 2


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE /{community_id}/members/{user_id}  — remove member
# ═══════════════════════════════════════════════════════════════════════════════

class TestRemoveMember:

    async def test_owner_can_remove_member(self, auth_client: AsyncClient, db_session):
        """Owner can remove a regular member; 204 returned."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Remove Member Owner")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()
        response = await auth_client.delete(f"{BASE}/{comm.id}/members/{TEST_OTHER_USER_ID}")
        assert response.status_code == 204

    async def test_moderator_can_remove_regular_member(self, app, db_session):
        """Moderator can remove a regular member."""
        third_id = uuid.UUID("c0000000-0000-0000-0000-000000000004")
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Remove Member Mod")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MODERATOR)
        await create_test_member(db_session, community_id=comm.id, user_id=third_id, role=MemberRole.MEMBER)
        await db_session.commit()

        async with _other_client(app) as c:
            response = await c.delete(f"{BASE}/{comm.id}/members/{third_id}")
        assert response.status_code == 204

    async def test_moderator_cannot_remove_owner(self, app, db_session):
        """Moderator cannot remove the owner."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Remove Mod Cannot Remove Owner")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MODERATOR)
        await db_session.commit()

        async with _other_client(app) as c:
            response = await c.delete(f"{BASE}/{comm.id}/members/{TEST_USER_ID}")
        assert response.status_code == 403

    async def test_regular_member_cannot_remove(self, app, db_session):
        """Regular member cannot remove another member."""
        third_id = uuid.UUID("c0000000-0000-0000-0000-000000000005")
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Remove Regular Forbidden")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await create_test_member(db_session, community_id=comm.id, user_id=third_id, role=MemberRole.MEMBER)
        await db_session.commit()

        async with _other_client(app) as c:
            response = await c.delete(f"{BASE}/{comm.id}/members/{third_id}")
        assert response.status_code == 403

    async def test_remove_member_unauthenticated(self, db_session, client: AsyncClient):
        """Unauthenticated remove returns 401 or 403."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Remove Unauth")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()
        response = await client.delete(f"{BASE}/{comm.id}/members/{TEST_OTHER_USER_ID}")
        assert response.status_code in (401, 403)

    async def test_remove_nonexistent_member_returns_404(self, auth_client: AsyncClient, db_session):
        """Removing a user who is not a member returns 404."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Remove Ghost Member")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()
        response = await auth_client.delete(f"{BASE}/{comm.id}/members/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_remove_member_sets_status_removed(self, auth_client: AsyncClient, db_session):
        """After removal, membership status is REMOVED."""
        from app.repositories import MembershipRepository

        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Remove Status Check")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()

        await auth_client.delete(f"{BASE}/{comm.id}/members/{TEST_OTHER_USER_ID}")

        repo = MembershipRepository(db_session)
        member = await repo.get_member(comm.id, TEST_OTHER_USER_ID)
        assert member.status == MembershipStatus.REMOVED


# ═══════════════════════════════════════════════════════════════════════════════
# PUT /{community_id}/members/{user_id}/role
# ═══════════════════════════════════════════════════════════════════════════════

class TestUpdateMemberRole:

    async def test_owner_can_promote_to_moderator(self, auth_client: AsyncClient, db_session):
        """Owner can change a member's role to MODERATOR."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Role Promote")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()

        response = await auth_client.put(
            f"{BASE}/{comm.id}/members/{TEST_OTHER_USER_ID}/role",
            json={"role": "MODERATOR"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "MODERATOR"

    async def test_owner_can_demote_moderator_to_member(self, auth_client: AsyncClient, db_session):
        """Owner can demote a MODERATOR back to MEMBER."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Role Demote")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MODERATOR)
        await db_session.commit()

        response = await auth_client.put(
            f"{BASE}/{comm.id}/members/{TEST_OTHER_USER_ID}/role",
            json={"role": "MEMBER"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "MEMBER"

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Production bug: shared/exceptions.py validation_exception_handler calls "
            "exc.errors() which includes ctx={'error': ValueError(...)}. "
            "JSONResponse cannot serialize ValueError — raises TypeError before "
            "the 422 response is sent. Expected: 422 with serializable error body."
        ),
    )
    async def test_cannot_assign_owner_role_returns_422(self, auth_client: AsyncClient, db_session):
        """OWNER role cannot be assigned via this endpoint — 422.
        Blocked by production bug in shared/exceptions.py:validation_exception_handler."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Role OWNER Block")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()

        response = await auth_client.put(
            f"{BASE}/{comm.id}/members/{TEST_OTHER_USER_ID}/role",
            json={"role": "OWNER"},
        )
        assert response.status_code == 422

    async def test_non_owner_cannot_change_roles(self, app, db_session):
        """Moderator cannot change another member's role."""
        third_id = uuid.UUID("c0000000-0000-0000-0000-000000000006")
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Role Mod Cannot Change")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MODERATOR)
        await create_test_member(db_session, community_id=comm.id, user_id=third_id, role=MemberRole.MEMBER)
        await db_session.commit()

        async with _other_client(app) as c:
            response = await c.put(
                f"{BASE}/{comm.id}/members/{third_id}/role",
                json={"role": "MODERATOR"},
            )
        assert response.status_code == 403

    async def test_role_update_target_not_member(self, auth_client: AsyncClient, db_session):
        """Updating role for non-member returns 404."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Role Update Ghost")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()

        response = await auth_client.put(
            f"{BASE}/{comm.id}/members/{uuid.uuid4()}/role",
            json={"role": "MODERATOR"},
        )
        assert response.status_code == 404

    async def test_role_update_unauthenticated(self, db_session, client: AsyncClient):
        """Unauthenticated role update returns 401 or 403."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="Role Unauth")
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()
        response = await client.put(
            f"{BASE}/{comm.id}/members/{TEST_OTHER_USER_ID}/role",
            json={"role": "MODERATOR"},
        )
        assert response.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /{community_id}/join-requests
# ═══════════════════════════════════════════════════════════════════════════════

class TestListJoinRequests:

    async def test_owner_can_list_join_requests(self, app, auth_client: AsyncClient, db_session):
        """Owner can view pending join requests."""
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="List JR Owner",
            requires_approval=True,
        )
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()

        async with _other_client(app) as c:
            await c.post(f"{BASE}/{comm.id}/join", json={"message": "Please let me in"})

        response = await auth_client.get(f"{BASE}/{comm.id}/join-requests")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_moderator_can_list_join_requests(self, app, db_session):
        """Moderator can view pending join requests."""
        third_id = uuid.UUID("c0000000-0000-0000-0000-000000000007")
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="List JR Mod",
            requires_approval=True,
        )
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MODERATOR)
        await db_session.commit()

        async with _other_client(app, user_id=third_id) as c:
            await c.post(f"{BASE}/{comm.id}/join", json={})

        mod_headers = build_auth_headers(user_id=TEST_OTHER_USER_ID)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers=mod_headers,
        ) as c:
            response = await c.get(f"{BASE}/{comm.id}/join-requests")
        assert response.status_code == 200

    async def test_regular_member_cannot_list_join_requests(self, app, db_session):
        """Regular member cannot view join requests — 403."""
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="List JR Guard",
            requires_approval=True,
        )
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        await db_session.commit()

        async with _other_client(app) as c:
            response = await c.get(f"{BASE}/{comm.id}/join-requests")
        assert response.status_code == 403

    async def test_list_join_requests_unauthenticated(self, db_session, client: AsyncClient):
        """Unauthenticated user cannot list join requests."""
        comm = await create_test_community(db_session, creator_id=TEST_USER_ID, name="List JR Unauth")
        await db_session.commit()
        response = await client.get(f"{BASE}/{comm.id}/join-requests")
        assert response.status_code in (401, 403)

    async def test_list_join_requests_non_member_gets_403(self, auth_client: AsyncClient, db_session):
        """Non-member auth user gets 403 (permission check fires before 404)."""
        # The service checks membership before community existence for this endpoint.
        response = await auth_client.get(f"{BASE}/{uuid.uuid4()}/join-requests")
        assert response.status_code == 403

    async def test_list_join_requests_response_schema(self, auth_client: AsyncClient, db_session):
        """Response has correct pagination schema fields."""
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="List JR Schema",
            requires_approval=True,
        )
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await db_session.commit()
        response = await auth_client.get(f"{BASE}/{comm.id}/join-requests")
        data = response.json()
        for field in ["requests", "total", "limit", "offset", "has_more"]:
            assert field in data


# ═══════════════════════════════════════════════════════════════════════════════
# PUT /join-requests/{request_id}  — approve / reject
# ═══════════════════════════════════════════════════════════════════════════════

class TestActionJoinRequest:

    async def _create_join_request(self, db_session, comm_id, requester_id):
        """Helper: directly insert a PENDING join request."""
        from app.models.membership import JoinRequest
        from shared.constants.status import JoinRequestStatus
        jr = JoinRequest(
            community_id=comm_id,
            requester_id=requester_id,
            message="Let me in",
            status=JoinRequestStatus.PENDING,
            created_by=requester_id,
            updated_by=requester_id,
        )
        db_session.add(jr)
        await db_session.flush()
        await db_session.refresh(jr)
        return jr

    async def test_owner_can_approve_join_request(self, auth_client: AsyncClient, db_session):
        """Owner can approve a join request; requester becomes ACTIVE member."""
        from app.repositories import MembershipRepository

        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="Approve JR",
            requires_approval=True,
        )
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        jr = await self._create_join_request(db_session, comm.id, TEST_OTHER_USER_ID)
        await db_session.commit()

        response = await auth_client.put(
            f"{BASE}/join-requests/{jr.id}",
            json={"action": "approve"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "APPROVED"

        repo = MembershipRepository(db_session)
        member = await repo.get_active_member(comm.id, TEST_OTHER_USER_ID)
        assert member is not None
        assert member.status == MembershipStatus.ACTIVE

    async def test_owner_can_reject_join_request(self, auth_client: AsyncClient, db_session):
        """Owner can reject a join request; status becomes REJECTED."""
        from app.repositories import MembershipRepository

        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="Reject JR",
            requires_approval=True,
        )
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        jr = await self._create_join_request(db_session, comm.id, TEST_OTHER_USER_ID)
        await db_session.commit()

        response = await auth_client.put(
            f"{BASE}/join-requests/{jr.id}",
            json={"action": "reject"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"

        repo = MembershipRepository(db_session)
        member = await repo.get_active_member(comm.id, TEST_OTHER_USER_ID)
        assert member is None

    async def test_regular_member_cannot_action_join_request(self, app, db_session):
        """Regular member cannot approve/reject — 403."""
        third_id = uuid.UUID("c0000000-0000-0000-0000-000000000008")
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="JR Action Guard",
            requires_approval=True,
        )
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_OTHER_USER_ID, role=MemberRole.MEMBER)
        jr = await self._create_join_request(db_session, comm.id, third_id)
        await db_session.commit()

        async with _other_client(app) as c:
            response = await c.put(f"{BASE}/join-requests/{jr.id}", json={"action": "approve"})
        assert response.status_code == 403

    async def test_action_join_request_not_found(self, auth_client: AsyncClient):
        """Actioning non-existent join request returns 404."""
        response = await auth_client.put(
            f"{BASE}/join-requests/{uuid.uuid4()}",
            json={"action": "approve"},
        )
        assert response.status_code == 404

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Production bug: shared/exceptions.py validation_exception_handler calls "
            "exc.errors() which includes ctx={'error': ValueError(...)}. "
            "JSONResponse cannot serialize ValueError — raises TypeError before "
            "the 422 response is sent. Expected: 422 with serializable error body."
        ),
    )
    async def test_action_join_request_invalid_action_returns_422(self, auth_client: AsyncClient, db_session):
        """Invalid action value returns 422.
        Blocked by production bug in shared/exceptions.py:validation_exception_handler."""
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="JR Invalid Action",
            requires_approval=True,
        )
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        jr = await self._create_join_request(db_session, comm.id, TEST_OTHER_USER_ID)
        await db_session.commit()

        response = await auth_client.put(
            f"{BASE}/join-requests/{jr.id}",
            json={"action": "maybe"},
        )
        assert response.status_code == 422

    async def test_action_join_request_unauthenticated(self, db_session, client: AsyncClient):
        """Unauthenticated action returns 401 or 403."""
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="JR Unauth Action",
            requires_approval=True,
        )
        jr = await self._create_join_request(db_session, comm.id, TEST_OTHER_USER_ID)
        await db_session.commit()
        response = await client.put(f"{BASE}/join-requests/{jr.id}", json={"action": "approve"})
        assert response.status_code in (401, 403)

    async def test_already_actioned_request_returns_400(self, auth_client: AsyncClient, db_session):
        """Actioning an already-actioned request returns 400."""
        comm = await create_test_community(
            db_session, creator_id=TEST_USER_ID, name="JR Double Action",
            requires_approval=True,
        )
        await create_test_member(db_session, community_id=comm.id, user_id=TEST_USER_ID, role=MemberRole.OWNER)
        jr = await self._create_join_request(db_session, comm.id, TEST_OTHER_USER_ID)
        await db_session.commit()

        await auth_client.put(f"{BASE}/join-requests/{jr.id}", json={"action": "approve"})
        response = await auth_client.put(f"{BASE}/join-requests/{jr.id}", json={"action": "reject"})
        assert response.status_code == 400
