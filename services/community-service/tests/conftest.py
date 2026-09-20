"""
Community Service — Test Configuration & Shared Fixtures

Provides the core testing infrastructure for all Community Service tests:

  - In-memory SQLite database (aiosqlite) — no external PostgreSQL required.
  - Async SQLAlchemy session with full schema creation/teardown per test.
  - FastAPI dependency override for get_db.
  - Async httpx.AsyncClient wired to the FastAPI app via ASGITransport.
  - Auth token builder for endpoint tests.

Session Architecture
--------------------
Each test gets its own isolated function-scoped engine + session.

  db_engine  →  creates schema, yields engine, drops schema on teardown
  db_session →  opens a session bound to the test engine, rolls back after test
  app        →  overrides get_db with a fresh session from the test engine
  client     →  unauthenticated AsyncClient for the test app
  auth_client →  AsyncClient pre-loaded with an Authorization Bearer header

Fixtures are function-scoped by default.  Each test starts with a clean
in-memory database — no shared-session contamination between tests.

Duplicate Index Workaround
--------------------------
CommunityMember.user_id is indexed twice:
  - implicitly via mapped_column(..., index=True)
  - explicitly via Index("ix_community_members_user_id", "user_id") in __table_args__

PostgreSQL silently deduplicates this; SQLite raises "index already exists".
_dedup_metadata_indexes() removes the duplicates from Base.metadata before
create_all() runs.  This is a test-only workaround — production code is untouched.
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
# Duplicate-index deduplication helper
# ─────────────────────────────────────────────────────────────────────────────

def _dedup_metadata_indexes() -> None:
    """
    Remove duplicate index objects from SQLAlchemy metadata tables.

    CommunityMember defines the same index twice:
      - once implicitly via  mapped_column(..., index=True)  on user_id
      - once explicitly via  Index("ix_community_members_user_id", "user_id")
        in __table_args__

    PostgreSQL tolerates this; SQLite raises "index already exists" on
    create_all().  This helper deduplicates the Table.indexes set so SQLite
    produces the same schema as PostgreSQL.

    Operates on the shared metadata singleton and is idempotent.
    This is a test-only workaround — no production model is modified.
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


# ─────────────────────────────────────────────────────────────────────────────
# Database fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture()
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Create an in-memory SQLite async engine scoped to one test.

    Imports all Community Service models so SQLAlchemy registers them on
    Base.metadata, then calls create_all() to build the full schema.
    Drops the schema and disposes the engine after the test.
    """
    # Side-effect import: registers all Community models on Base.metadata.
    import app.models  # noqa: F401

    # Deduplicate indexes before schema creation.
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

    The session is rolled back after each test.  This ensures complete
    isolation: writes from one test never persist into the next, even
    when tests share the same in-process SQLite file (they don't — each
    db_engine fixture creates a fresh :memory: database).
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
    Return the FastAPI application with the test database wired in.

    Two complementary overrides are applied:

    1. ``get_db`` dependency is replaced with a function that yields an
       AsyncSession backed by the in-memory test engine.  Each request
       within a single test gets its own session that commits on success
       and rolls back on error.

    2. ``app.state.db_sessionmaker`` is set to the test sessionmaker so
       the production lifespan path (which reads from app.state) also
       resolves to the test engine.

    Both overrides are removed after the test completes.
    """
    from app.core.main import app as fastapi_app
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
    fastapi_app.state.db_sessionmaker = test_sessionmaker

    yield fastapi_app

    fastapi_app.dependency_overrides.pop(get_db, None)


# ─────────────────────────────────────────────────────────────────────────────
# Test user & authentication helpers
# ─────────────────────────────────────────────────────────────────────────────

# Deterministic UUID for the default test user.
# Use a distinct value from the Feed Service test user (a0000…0001) so tests
# across services are distinguishable in logs.
TEST_USER_ID: uuid.UUID = uuid.UUID("c0000000-0000-0000-0000-000000000001")
TEST_USER_EMAIL: str = "community_test@ontdekker.test"

# A second deterministic user for membership/ownership tests.
TEST_OTHER_USER_ID: uuid.UUID = uuid.UUID("c0000000-0000-0000-0000-000000000002")
TEST_OTHER_USER_EMAIL: str = "community_other@ontdekker.test"


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
    Build a signed JWT for the default test user using the shared JWT secret.

    Signed with the same secret that shared.dependencies.get_current_user
    validates against.
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
    Return an HTTP headers dict with a valid Bearer token for the default test user.

    Usage::

        response = await client.post(
            "/api/v1/communities",
            json=payload,
            headers=auth_headers,
        )
    """
    return {"Authorization": f"Bearer {auth_token}"}


# ─────────────────────────────────────────────────────────────────────────────
# HTTP test clients
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """
    Unauthenticated async httpx client wired to the FastAPI test app.

    Requests are processed in-process via ASGITransport — no real HTTP server
    is started.  Use this for public endpoints or when you supply auth headers
    per-request.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


@pytest_asyncio.fixture()
async def auth_client(app, auth_headers) -> AsyncGenerator[AsyncClient, None]:
    """
    Authenticated async httpx client pre-configured with an Authorization header.

    Every request sent via this client carries a valid Bearer token for the
    default test user (TEST_USER_ID).  Use this when all requests in a test
    require authentication::

        async def test_create_community(auth_client):
            response = await auth_client.post("/api/v1/communities", json={...})
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=auth_headers,
    ) as ac:
        yield ac
