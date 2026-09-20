"""
CP-16A Infrastructure Smoke Tests

Verifies that all shared fixtures load and are usable.
These tests are kept minimal — they validate the test infrastructure itself,
not any business logic.

Run with:
    pytest tests/test_infrastructure.py -v
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ─────────────────────────────────────────────────────────────────────────────
# Synchronous fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_test_user_payload_shape(test_user_payload):
    """test_user_payload has the required JWT claim fields."""
    assert "sub" in test_user_payload
    assert "email" in test_user_payload
    assert "roles" in test_user_payload
    assert "exp" in test_user_payload


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


# ─────────────────────────────────────────────────────────────────────────────
# Async database fixtures
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
async def test_db_session_executes_query(db_session):
    """db_session can execute a simple SELECT query against the in-memory DB."""
    from sqlalchemy import text
    result = await db_session.execute(text("SELECT 1 AS value"))
    row = result.fetchone()
    assert row is not None
    assert row[0] == 1


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
async def test_app_fixture_is_fastapi(app):
    """app fixture returns a FastAPI application instance."""
    from fastapi import FastAPI
    assert isinstance(app, FastAPI)


@pytest.mark.integration
async def test_app_state_has_sessionmaker(app):
    """app.state.db_sessionmaker is configured by the test fixture."""
    assert app.state.db_sessionmaker is not None


@pytest.mark.integration
async def test_get_db_override_registered(app):
    """get_db dependency override is present in dependency_overrides."""
    from shared.dependencies import get_db
    assert get_db in app.dependency_overrides


# ─────────────────────────────────────────────────────────────────────────────
# HTTP client fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
async def test_client_is_async_client(client):
    """client fixture yields an AsyncClient."""
    assert isinstance(client, AsyncClient)


@pytest.mark.integration
async def test_auth_client_has_auth_header(auth_client):
    """auth_client fixture pre-injects Authorization header."""
    assert "authorization" in auth_client.headers


@pytest.mark.integration
async def test_health_endpoint_responds(client):
    """The /health endpoint returns HTTP 200 with the test database."""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "feed-service"


# ─────────────────────────────────────────────────────────────────────────────
# Test utilities
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
    """make_user_payload returns a dict with expected JWT fields."""
    from tests.utils import make_user_payload
    payload = make_user_payload()
    assert "sub" in payload
    assert "email" in payload
    assert "roles" in payload


@pytest.mark.unit
def test_utils_build_auth_headers():
    """build_auth_headers returns an Authorization header dict."""
    from tests.utils import build_auth_headers
    headers = build_auth_headers()
    assert headers["Authorization"].startswith("Bearer ")


@pytest.mark.unit
def test_utils_make_post_payload():
    """make_post_payload returns a valid PostCreateRequest body."""
    from tests.utils import make_post_payload
    payload = make_post_payload()
    assert "title" in payload
    assert "tags" in payload
    assert "visibility" in payload


@pytest.mark.unit
def test_utils_make_comment_payload():
    """make_comment_payload returns a valid CommentCreateRequest body."""
    from tests.utils import make_comment_payload
    payload = make_comment_payload()
    assert "content" in payload


@pytest.mark.unit
def test_utils_make_share_payload():
    """make_share_payload returns a dict with share_channel key."""
    from tests.utils import make_share_payload
    payload = make_share_payload()
    assert "share_channel" in payload
