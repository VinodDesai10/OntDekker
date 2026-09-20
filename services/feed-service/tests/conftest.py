"""
Feed Service — Test Configuration & Shared Fixtures

Provides the core testing infrastructure for all Feed Service tests:

  - In-memory SQLite database (aiosqlite) — no external DB required.
  - Async SQLAlchemy session with full schema creation/teardown per test.
  - FastAPI dependency overrides for get_db and get_current_user.
  - Async httpx.AsyncClient wired to the FastAPI app.
  - Auth token builder for endpoint tests.

Usage
-----
All fixtures are function-scoped by default so each test starts with a clean
database. Import and use fixtures by name in any test file:

    async def test_example(client, auth_headers):
        response = await client.get("/api/v1/feed/posts")
        assert response.status_code == 200
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator, Dict, Any

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from shared.database import Base
from shared.utils.security import create_jwt_token
from shared.config import get_common_settings

# ─────────────────────────────────────────────────────────────────────────────
# Database fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _dedup_metadata_indexes() -> None:
    """
    Remove duplicate index objects from SQLAlchemy metadata tables.

    Some Feed Service models define the same index twice:
      - once implicitly via  mapped_column(..., index=True)
      - once explicitly via  Index("ix_<table>_<col>", "<col>") in __table_args__

    PostgreSQL silently emits one CREATE INDEX in this case; SQLite raises
    "index already exists".  This helper deduplicates the Table.indexes set
    so SQLite gets the same DDL as PostgreSQL.  It operates on the shared
    metadata singleton and is idempotent.

    This is a test-only workaround — it does NOT modify any production model.
    """
    for table in Base.metadata.tables.values():
        seen: set = set()
        to_remove = []
        for index in list(table.indexes):
            if index.name in seen:
                to_remove.append(index)
            else:
                seen.add(index.name)
        for index in to_remove:
            table.indexes.discard(index)


@pytest_asyncio.fixture()
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Create an in-memory SQLite async engine for the duration of one test.

    Uses aiosqlite so no external PostgreSQL is required.
    All Feed Service models are registered on shared.database.Base, so
    create_all() creates every table in one call.
    """
    # Import models so SQLAlchemy registers them on Base.metadata.
    # This must happen before create_all().
    import app.models  # noqa: F401  — side-effect import

    # Deduplicate indexes before schema creation.  Some models define the same
    # index both via column index=True and an explicit Index() in __table_args__.
    # PostgreSQL tolerates this; SQLite raises OperationalError.
    _dedup_metadata_indexes()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an AsyncSession bound to the in-memory test engine.

    The session is rolled back after each test so tests are fully isolated
    even if they write to the database.
    """
    test_sessionmaker = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with test_sessionmaker() as session:
        yield session
        await session.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app + dependency overrides
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture()
async def app(db_engine: AsyncEngine):
    """
    Return the FastAPI application with test overrides applied:

    1. ``get_db`` → yields an AsyncSession backed by the in-memory engine.
    2. ``app.state.db_sessionmaker`` is set so the production get_db path also
       resolves to the test engine.
    3. ``_verify_community_membership`` is patched to return True so tests that
       create COMMUNITY-visibility posts do not need a running community-service.

    Overrides are cleaned up after the test completes.
    """
    from unittest.mock import patch, AsyncMock
    from app.core.main import app as fastapi_app
    from app.services.post_service import PostService
    from shared.dependencies import get_db

    test_sessionmaker = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def _override_get_db():
        async with test_sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    # Also patch app.state so the lifespan-injected path resolves correctly.
    fastapi_app.state.db_sessionmaker = test_sessionmaker

    # Patch _verify_community_membership so COMMUNITY posts pass membership
    # checks without a real community-service running in the test environment.
    # Also patch _fetch_user_community_ids so list_posts() does not attempt an
    # HTTP call to community-service; returning an empty list is safe because
    # endpoint tests that need community-scoped visibility supply community_id
    # as an explicit query param (scoped feed path) which bypasses the
    # membership enforcement logic.
    with patch(
        "app.services.post_service._verify_community_membership",
        new=AsyncMock(return_value=True),
    ), patch.object(
        PostService,
        "_fetch_user_community_ids",
        new=AsyncMock(return_value=[]),
    ):
        yield fastapi_app

    # Teardown — remove all overrides added during this test.
    fastapi_app.dependency_overrides.pop(get_db, None)


# ─────────────────────────────────────────────────────────────────────────────
# Test user & authentication helpers
# ─────────────────────────────────────────────────────────────────────────────

TEST_USER_ID: uuid.UUID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
TEST_USER_EMAIL: str = "testuser@ontdekker.test"


@pytest.fixture()
def test_user_payload() -> Dict[str, Any]:
    """
    Return a minimal JWT payload dict representing the default test user.

    Matches the shape expected by shared.dependencies.get_current_user.
    """
    return {
        "sub": str(TEST_USER_ID),
        "email": TEST_USER_EMAIL,
        "roles": ["user"],
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
    }


@pytest.fixture()
def auth_token(test_user_payload: Dict[str, Any]) -> str:
    """
    Build a signed JWT for the default test user using the test secret.

    The token is valid for 1 hour and signed with the same secret that
    shared.dependencies.get_current_user validates against.
    """
    settings = get_common_settings()
    return create_jwt_token(
        data={k: v for k, v in test_user_payload.items() if k != "exp"},
        secret_key=settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
        expires_delta=timedelta(hours=1),
    )


@pytest.fixture()
def auth_headers(auth_token: str) -> Dict[str, str]:
    """
    Return HTTP headers dict with a valid Bearer token for the default test user.

    Usage::

        response = await client.post("/api/v1/feed/posts", json=data, headers=auth_headers)
    """
    return {"Authorization": f"Bearer {auth_token}"}


# ─────────────────────────────────────────────────────────────────────────────
# HTTP test client
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """
    Async httpx client wired to the FastAPI test app via ASGITransport.

    Does NOT start a real HTTP server — requests are processed in-process.
    Automatically carries the base_url so relative paths like
    ``/api/v1/feed/posts`` resolve correctly.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# Convenience fixture: authenticated client
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture()
async def auth_client(app, auth_headers) -> AsyncGenerator[AsyncClient, None]:
    """
    Async httpx client pre-configured with a valid Authorization header.

    Use this fixture when every request in a test requires authentication::

        async def test_create_post(auth_client):
            response = await auth_client.post("/api/v1/feed/posts", json={...})
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=auth_headers,
    ) as ac:
        yield ac
