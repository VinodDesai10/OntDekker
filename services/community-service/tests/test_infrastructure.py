"""
CP-16E.1 — Community Service Infrastructure Smoke Tests

Verifies that all shared fixtures load and are usable against the Community
Service application.  These tests validate the TEST INFRASTRUCTURE only —
no Community business logic is tested here.

Run with:
    pytest tests/test_infrastructure.py -v
"""

import uuid

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TEST_USER_ID, TEST_OTHER_USER_ID


# ─────────────────────────────────────────────────────────────────────────────
# Synchronous fixture checks (no DB required)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_test_user_payload_shape(test_user_payload):
    """test_user_payload has all required JWT claim fields."""
    assert "sub" in test_user_payload
    assert "email" in test_user_payload
    assert "roles" in test_user_payload
    assert "exp" in test_user_payload


@pytest.mark.unit
def test_test_user_payload_identity(test_user_payload):
    """test_user_payload sub matches the deterministic TEST_USER_ID."""
    assert test_user_payload["sub"] == str(TEST_USER_ID)


@pytest.mark.unit
def test_auth_token_is_jwt(auth_token):
    """auth_token is a well-formed JWT (three dot-separated segments)."""
    parts = auth_token.split(".")
    assert len(parts) == 3, "JWT must have header.payload.signature"


@pytest.mark.unit
def test_auth_headers_format(auth_headers):
    """auth_headers contains a valid Bearer authorization header."""
    assert "Authorization" in auth_headers
    assert auth_headers["Authorization"].startswith("Bearer ")


@pytest.mark.unit
def test_deterministic_test_user_ids():
    """Both deterministic test user IDs are distinct valid UUIDs."""
    assert isinstance(TEST_USER_ID, uuid.UUID)
    assert isinstance(TEST_OTHER_USER_ID, uuid.UUID)
    assert TEST_USER_ID != TEST_OTHER_USER_ID


# ─────────────────────────────────────────────────────────────────────────────
# pytest-asyncio execution
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
async def test_async_execution_works():
    """pytest-asyncio runs async tests correctly (sanity check)."""
    result = await _async_add(1, 1)
    assert result == 2


async def _async_add(a: int, b: int) -> int:
    return a + b


# ─────────────────────────────────────────────────────────────────────────────
# Database engine & session
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
async def test_db_engine_created(db_engine):
    """db_engine fixture yields a non-None async engine."""
    assert db_engine is not None


@pytest.mark.integration
async def test_db_session_is_async_session(db_session):
    """db_session yields an open AsyncSession instance."""
    assert isinstance(db_session, AsyncSession)


@pytest.mark.integration
async def test_db_session_executes_simple_query(db_session):
    """db_session can execute a SELECT 1 against the in-memory database."""
    result = await db_session.execute(text("SELECT 1 AS value"))
    row = result.fetchone()
    assert row is not None
    assert row[0] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Community tables created
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
async def test_community_tables_exist(db_engine):
    """All six Community Service tables are created in the test database."""
    expected_tables = {
        "communities",
        "community_members",
        "join_requests",
        "community_rules",
        "discussions",
        "discussion_comments",
    }

    def _get_table_names(conn):
        return inspect(conn).get_table_names()

    async with db_engine.connect() as conn:
        table_names = await conn.run_sync(_get_table_names)

    missing = expected_tables - set(table_names)
    assert not missing, f"Missing tables: {missing}"


@pytest.mark.integration
async def test_communities_table_columns(db_engine):
    """communities table has the expected core columns."""
    expected_columns = {
        "id", "creator_id", "name", "slug", "description",
        "location", "status", "visibility", "requires_approval",
        "member_count", "is_deleted",
    }

    def _get_columns(conn):
        return {col["name"] for col in inspect(conn).get_columns("communities")}

    async with db_engine.connect() as conn:
        actual_columns = await conn.run_sync(_get_columns)

    missing = expected_columns - actual_columns
    assert not missing, f"Missing columns in communities: {missing}"


@pytest.mark.integration
async def test_community_members_table_columns(db_engine):
    """community_members table has the expected core columns."""
    expected_columns = {"id", "community_id", "user_id", "role", "status"}

    def _get_columns(conn):
        return {col["name"] for col in inspect(conn).get_columns("community_members")}

    async with db_engine.connect() as conn:
        actual_columns = await conn.run_sync(_get_columns)

    missing = expected_columns - actual_columns
    assert not missing, f"Missing columns in community_members: {missing}"


@pytest.mark.integration
async def test_discussions_table_columns(db_engine):
    """discussions table has the expected core columns."""
    expected_columns = {
        "id", "community_id", "author_id", "title", "content",
        "comment_count", "is_deleted",
    }

    def _get_columns(conn):
        return {col["name"] for col in inspect(conn).get_columns("discussions")}

    async with db_engine.connect() as conn:
        actual_columns = await conn.run_sync(_get_columns)

    missing = expected_columns - actual_columns
    assert not missing, f"Missing columns in discussions: {missing}"


@pytest.mark.integration
async def test_discussion_comments_table_columns(db_engine):
    """discussion_comments table has the expected core columns."""
    expected_columns = {
        "id", "discussion_id", "author_id", "content", "is_deleted",
    }

    def _get_columns(conn):
        return {col["name"] for col in inspect(conn).get_columns("discussion_comments")}

    async with db_engine.connect() as conn:
        actual_columns = await conn.run_sync(_get_columns)

    missing = expected_columns - actual_columns
    assert not missing, f"Missing columns in discussion_comments: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# Database isolation
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
async def test_db_session_isolation_write_and_rollback(db_session):
    """
    Writes within a test session do not persist after rollback.

    Inserts a community row directly then verifies it can be read within the
    same session.  The conftest rolls back after the test — a second test
    would not see this row.
    """
    from app.models.community import Community
    from shared.constants.status import CommunityStatus, CommunityVisibility

    community = Community(
        creator_id=TEST_USER_ID,
        name="Isolation Test Community",
        slug="isolation-test-community-abc123",
        status=CommunityStatus.ACTIVE,
        visibility=CommunityVisibility.PUBLIC,
        requires_approval=False,
        member_count=0,
    )
    db_session.add(community)
    await db_session.flush()

    assert community.id is not None

    # Verify the row is readable within this session.
    from sqlalchemy import select
    from app.models.community import Community as Comm
    result = await db_session.execute(
        select(Comm).where(Comm.slug == "isolation-test-community-abc123")
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.name == "Isolation Test Community"
    # Session is rolled back by conftest after this test completes.


@pytest.mark.integration
async def test_db_isolation_second_test_sees_clean_state(db_session):
    """
    This test verifies the isolation test above left no rows behind.

    Because db_engine is function-scoped, each test gets a completely fresh
    in-memory database — isolation is guaranteed by engine scope, not just
    rollback.  This test simply confirms the communities table is empty.
    """
    from sqlalchemy import select
    from app.models.community import Community

    result = await db_session.execute(select(Community))
    rows = result.scalars().all()
    assert rows == [], (
        "communities table should be empty at the start of every test — "
        "db_engine is function-scoped, so each test gets a fresh :memory: database."
    )


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
async def test_app_fixture_is_fastapi(app):
    """app fixture returns a FastAPI application instance."""
    assert isinstance(app, FastAPI)


@pytest.mark.integration
async def test_app_state_has_sessionmaker(app):
    """app.state.db_sessionmaker is set to the test sessionmaker."""
    assert app.state.db_sessionmaker is not None


@pytest.mark.integration
async def test_get_db_override_registered(app):
    """get_db dependency override is present in app.dependency_overrides."""
    from shared.dependencies import get_db
    assert get_db in app.dependency_overrides


# ─────────────────────────────────────────────────────────────────────────────
# HTTP client fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
async def test_client_is_async_client(client):
    """client fixture yields an AsyncClient instance."""
    assert isinstance(client, AsyncClient)


@pytest.mark.integration
async def test_auth_client_has_auth_header(auth_client):
    """auth_client fixture pre-injects an Authorization header."""
    assert "authorization" in auth_client.headers


@pytest.mark.integration
async def test_auth_client_carries_correct_identity(auth_client):
    """
    auth_client token encodes TEST_USER_ID as the subject claim.

    Decodes the JWT from the Authorization header and checks the sub claim.
    """
    import base64
    import json

    auth_header = auth_client.headers["authorization"]
    token = auth_header.split(" ")[1]
    # Base64-decode the payload segment (index 1), add padding as needed.
    payload_b64 = token.split(".")[1]
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    claims = json.loads(base64.urlsafe_b64decode(payload_b64))

    assert claims["sub"] == str(TEST_USER_ID)


# ─────────────────────────────────────────────────────────────────────────────
# Health endpoint
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
async def test_health_endpoint_responds(client):
    """The /health endpoint returns HTTP 200 with the test database connected."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.integration
async def test_health_endpoint_service_name(client):
    """The /health response identifies the service as 'community-service'."""
    response = await client.get("/health")
    body = response.json()
    assert body["service"] == "community-service"


@pytest.mark.integration
async def test_health_endpoint_database_connected(client):
    """The /health response reports the database as 'connected'."""
    response = await client.get("/health")
    body = response.json()
    assert body.get("database") == "connected"


# ─────────────────────────────────────────────────────────────────────────────
# Unauthenticated access
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
async def test_unauthenticated_community_list_returns_200(client):
    """
    GET /api/v1/communities/ is publicly accessible (no auth required).

    The route is registered as "/" relative to the prefix, so the canonical
    URL requires a trailing slash.  FastAPI issues a 307 redirect from the
    slash-free form.

    This validates that the unauthenticated client works and reaches a live
    route — not that the response body is correct (that belongs to endpoint tests).
    """
    # The community list route is registered as GET "/" under the prefix,
    # so the full URL requires the trailing slash.
    response = await client.get("/api/v1/communities/")
    # Public listing should be accessible without authentication.
    assert response.status_code == 200


@pytest.mark.integration
async def test_protected_endpoint_rejects_unauthenticated(client):
    """
    POST /api/v1/communities/ requires authentication and returns 401 without a token.

    The route is registered as POST "/" relative to the prefix; the trailing
    slash is required to reach it directly without a redirect.
    """
    response = await client.post(
        "/api/v1/communities/",
        json={"name": "Test", "visibility": "PUBLIC"},
    )
    assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# Test utility functions (unit-level, no DB)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_utils_build_jwt_token():
    """build_jwt_token produces a signed JWT string."""
    from tests.utils import build_jwt_token
    token = build_jwt_token()
    assert isinstance(token, str)
    assert len(token.split(".")) == 3


@pytest.mark.unit
def test_utils_make_user_payload():
    """make_user_payload returns a dict with all required JWT fields."""
    from tests.utils import make_user_payload
    payload = make_user_payload()
    assert "sub" in payload
    assert "email" in payload
    assert "roles" in payload
    assert "exp" in payload


@pytest.mark.unit
def test_utils_build_auth_headers():
    """build_auth_headers returns an Authorization Bearer header dict."""
    from tests.utils import build_auth_headers
    headers = build_auth_headers()
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")


@pytest.mark.unit
def test_utils_make_community_payload():
    """make_community_payload returns a valid CommunityCreateRequest body."""
    from tests.utils import make_community_payload
    payload = make_community_payload()
    assert "name" in payload
    assert "visibility" in payload
    assert "requires_approval" in payload


@pytest.mark.unit
def test_utils_make_community_update_payload():
    """make_community_update_payload returns only the provided fields."""
    from tests.utils import make_community_update_payload
    payload = make_community_update_payload(name="New Name")
    assert payload == {"name": "New Name"}


@pytest.mark.unit
def test_utils_make_community_update_payload_empty():
    """make_community_update_payload returns an empty dict when called with no args."""
    from tests.utils import make_community_update_payload
    payload = make_community_update_payload()
    assert payload == {}


@pytest.mark.unit
def test_utils_make_membership_payload():
    """make_membership_payload returns a JoinCommunityRequest body."""
    from tests.utils import make_membership_payload
    payload = make_membership_payload()
    assert "message" in payload


@pytest.mark.unit
def test_utils_make_discussion_payload():
    """make_discussion_payload returns a valid DiscussionCreateRequest body."""
    from tests.utils import make_discussion_payload
    payload = make_discussion_payload()
    assert "title" in payload
    assert "content" in payload


@pytest.mark.unit
def test_utils_make_discussion_comment_payload():
    """make_discussion_comment_payload returns a valid DiscussionCommentCreateRequest body."""
    from tests.utils import make_discussion_comment_payload
    payload = make_discussion_comment_payload()
    assert "content" in payload
    assert len(payload["content"]) > 0


@pytest.mark.unit
def test_utils_make_rule_payload():
    """make_rule_payload returns a valid CommunityRuleCreateRequest body."""
    from tests.utils import make_rule_payload
    payload = make_rule_payload()
    assert "title" in payload
    assert "order_index" in payload
    assert payload["order_index"] >= 1


# ─────────────────────────────────────────────────────────────────────────────
# ORM factory helpers
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
async def test_create_test_community_helper(db_session):
    """create_test_community persists a Community row and returns it with an id."""
    from tests.utils import create_test_community

    community = await create_test_community(db_session, creator_id=TEST_USER_ID)
    assert community.id is not None
    assert community.creator_id == TEST_USER_ID
    assert community.slug is not None


@pytest.mark.integration
async def test_create_test_member_helper(db_session):
    """create_test_member persists a CommunityMember linked to a community."""
    from tests.utils import create_test_community, create_test_member

    community = await create_test_community(db_session, creator_id=TEST_USER_ID)
    member = await create_test_member(
        db_session,
        community_id=community.id,
        user_id=TEST_USER_ID,
    )
    assert member.id is not None
    assert member.community_id == community.id
    assert member.user_id == TEST_USER_ID


@pytest.mark.integration
async def test_create_test_discussion_helper(db_session):
    """create_test_discussion persists a Discussion linked to a community."""
    from tests.utils import create_test_community, create_test_discussion

    community = await create_test_community(db_session, creator_id=TEST_USER_ID)
    discussion = await create_test_discussion(
        db_session,
        community_id=community.id,
        author_id=TEST_USER_ID,
    )
    assert discussion.id is not None
    assert discussion.community_id == community.id
    assert discussion.author_id == TEST_USER_ID


@pytest.mark.integration
async def test_create_test_comment_helper(db_session):
    """create_test_comment persists a DiscussionComment linked to a discussion."""
    from tests.utils import (
        create_test_community,
        create_test_discussion,
        create_test_comment,
    )

    community = await create_test_community(db_session, creator_id=TEST_USER_ID)
    discussion = await create_test_discussion(
        db_session, community_id=community.id, author_id=TEST_USER_ID
    )
    comment = await create_test_comment(
        db_session,
        discussion_id=discussion.id,
        author_id=TEST_OTHER_USER_ID,
    )
    assert comment.id is not None
    assert comment.discussion_id == discussion.id
    assert comment.author_id == TEST_OTHER_USER_ID
