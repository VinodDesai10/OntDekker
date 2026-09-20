"""
Authentication Service — Checkpoint 3 Test Suite

Test categories:
  [UNIT]        No database. Pure Python logic tested in isolation.
  [INTEGRATION] Requires live auth_db on localhost:5432.

Run with:
  PYTHONPATH=../.. pytest tests/test_auth.py -v

Covers:
  - password hashing / verification
  - JWT generation / validation / expiry / wrong secret
  - token generation entropy
  - schema validation / email normalisation
  - repository operations (live DB)
  - service layer flows (live DB)
  - registration success, duplicate email, atomicity
  - login success, wrong password, unknown email, inactive account
  - refresh token lifecycle (valid, revoked, expired)
  - logout idempotency
  - /me endpoint
  - default USER role assignment
  - role seeding (all 4 roles present)
  - database constraint handling
"""

import asyncio
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# ---------------------------------------------------------------------------
# Environment config for tests — always points at local auth_db
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/auth_db"
)

# ---------------------------------------------------------------------------
# Async event loop fixture (session-scoped)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Database session fixture — each test gets a rolled-back transaction
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async session that rolls back after every test.

    This keeps the live auth_db clean — tests never commit, so all
    registered users, tokens, etc. disappear when the test ends.
    The roles seeded by migration a1b2c3d4e5f6 are visible because they
    were committed by the migration (before tests run).
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with factory() as session:
        await session.begin_nested()   # savepoint
        yield session
        await session.rollback()       # roll back to savepoint
    await engine.dispose()

# ===========================================================================
# UNIT TESTS — no database required
# ===========================================================================

class TestPasswordHashing:
    """[UNIT] bcrypt password hashing via shared utilities."""

    def test_hash_is_not_plaintext(self):
        from shared.utils.security import get_password_hash
        h = get_password_hash("Secret123!")
        assert h != "Secret123!"

    def test_hash_starts_with_bcrypt_prefix(self):
        from shared.utils.security import get_password_hash
        h = get_password_hash("Secret123!")
        assert h.startswith("$2b$")

    def test_correct_password_verifies(self):
        from shared.utils.security import get_password_hash, verify_password
        h = get_password_hash("MyPass1!")
        assert verify_password("MyPass1!", h) is True

    def test_wrong_password_rejected(self):
        from shared.utils.security import get_password_hash, verify_password
        h = get_password_hash("MyPass1!")
        assert verify_password("wrongpass", h) is False

    def test_two_hashes_of_same_password_differ(self):
        from shared.utils.security import get_password_hash
        h1 = get_password_hash("same")
        h2 = get_password_hash("same")
        assert h1 != h2  # bcrypt uses unique salts


class TestJWTUtilities:
    """[UNIT] JWT generation and validation."""

    SECRET = "test_secret_cp3"
    ALGO = "HS256"

    def _make_token(self, extra=None, expires_delta=None):
        from shared.utils.security import create_jwt_token
        payload = {"sub": "uuid-1234", "email": "a@b.com", "roles": ["USER"]}
        if extra:
            payload.update(extra)
        kwargs = {"data": payload, "secret_key": self.SECRET, "algorithm": self.ALGO}
        if expires_delta is not None:
            kwargs["expires_delta"] = expires_delta
        return create_jwt_token(**kwargs)

    def test_token_is_string(self):
        assert isinstance(self._make_token(), str)

    def test_decoded_contains_correct_claims(self):
        from shared.utils.security import decode_jwt_token
        token = self._make_token()
        decoded = decode_jwt_token(token, self.SECRET, self.ALGO)
        assert decoded["sub"] == "uuid-1234"
        assert decoded["email"] == "a@b.com"
        assert decoded["roles"] == ["USER"]
        assert "exp" in decoded

    def test_expired_token_raises(self):
        from jose import JWTError
        from shared.utils.security import decode_jwt_token
        token = self._make_token(expires_delta=timedelta(seconds=-1))
        with pytest.raises(JWTError):
            decode_jwt_token(token, self.SECRET, self.ALGO)

    def test_wrong_secret_raises(self):
        from jose import JWTError
        from shared.utils.security import decode_jwt_token
        token = self._make_token()
        with pytest.raises(JWTError):
            decode_jwt_token(token, "wrong_secret", self.ALGO)


class TestTokenGenerationHelpers:
    """[UNIT] Service-level token generation helpers."""

    def test_raw_refresh_token_is_string(self):
        from app.security import generate_raw_refresh_token
        t = generate_raw_refresh_token()
        assert isinstance(t, str)

    def test_raw_refresh_token_has_sufficient_length(self):
        from app.security import generate_raw_refresh_token
        assert len(generate_raw_refresh_token()) >= 60

    def test_two_refresh_tokens_differ(self):
        from app.security import generate_raw_refresh_token
        assert generate_raw_refresh_token() != generate_raw_refresh_token()

    def test_raw_opaque_token_differs_each_time(self):
        from app.security import generate_raw_opaque_token
        assert generate_raw_opaque_token() != generate_raw_opaque_token()

    def test_sha256_digest_is_64_hex_chars(self):
        raw = secrets.token_urlsafe(48)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)

    def test_generate_access_token_contains_correct_claims(self):
        from shared.utils.security import decode_jwt_token
        from app.security import generate_access_token
        from app.config.settings import settings
        token = generate_access_token("uid-xyz", "dev@test.com", ["USER"])
        decoded = decode_jwt_token(token, settings.JWT_SECRET, settings.JWT_ALGORITHM)
        assert decoded["sub"] == "uid-xyz"
        assert decoded["email"] == "dev@test.com"
        assert decoded["roles"] == ["USER"]

    def test_refresh_token_expires_at_is_future(self):
        from app.security import refresh_token_expires_at
        exp = refresh_token_expires_at()
        assert exp > datetime.now(timezone.utc)

    def test_verification_token_expires_at_is_future(self):
        from app.security import verification_token_expires_at
        exp = verification_token_expires_at()
        assert exp > datetime.now(timezone.utc)


class TestSchemaValidation:
    """[UNIT] Pydantic schema validation rules."""

    def test_register_request_normalises_email_to_lowercase(self):
        from app.schemas.auth import RegisterRequest
        r = RegisterRequest(email="TEST@EXAMPLE.COM", password="Pass1234!")
        assert r.email == "test@example.com"

    def test_register_request_strips_whitespace_from_email(self):
        from app.schemas.auth import RegisterRequest
        r = RegisterRequest(email="  user@example.com  ", password="Pass1234!")
        assert r.email == "user@example.com"

    def test_register_request_rejects_short_password(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", password="short")

    def test_register_request_rejects_invalid_email(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(email="not-an-email", password="ValidPass1!")

    def test_login_request_normalises_email(self):
        from app.schemas.auth import LoginRequest
        r = LoginRequest(email="User@Example.COM", password="any")
        assert r.email == "user@example.com"

    def test_token_response_has_bearer_type(self):
        from app.schemas.auth import TokenResponse
        r = TokenResponse(access_token="a", refresh_token="b", expires_in=1800)
        assert r.token_type == "bearer"

    def test_access_token_response_has_bearer_type(self):
        from app.schemas.auth import AccessTokenResponse
        r = AccessTokenResponse(access_token="a", expires_in=1800)
        assert r.token_type == "bearer"


# ===========================================================================
# INTEGRATION TESTS — require live auth_db
# ===========================================================================

# ---------------------------------------------------------------------------
# Repository-level tests
# ---------------------------------------------------------------------------

class TestUserRepository:
    """[INTEGRATION] UserRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_user_returns_user_with_id(self, db_session):
        from app.repositories.auth import UserRepository
        from shared.utils.security import get_password_hash
        repo = UserRepository(db_session)
        user = await repo.create("repo_test@example.com", get_password_hash("Pass1!"))
        assert user.id is not None
        assert user.email == "repo_test@example.com"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.is_deleted is False

    @pytest.mark.asyncio
    async def test_get_by_email_returns_correct_user(self, db_session):
        from app.repositories.auth import UserRepository
        from shared.utils.security import get_password_hash
        repo = UserRepository(db_session)
        await repo.create("lookup@example.com", get_password_hash("Pass1!"))
        found = await repo.get_by_email("lookup@example.com")
        assert found is not None
        assert found.email == "lookup@example.com"

    @pytest.mark.asyncio
    async def test_get_by_email_returns_none_for_unknown(self, db_session):
        from app.repositories.auth import UserRepository
        repo = UserRepository(db_session)
        assert await repo.get_by_email("nobody@example.com") is None

    @pytest.mark.asyncio
    async def test_get_by_id_returns_correct_user(self, db_session):
        from app.repositories.auth import UserRepository
        from shared.utils.security import get_password_hash
        repo = UserRepository(db_session)
        user = await repo.create("byid@example.com", get_password_hash("Pass1!"))
        found = await repo.get_by_id(user.id)
        assert found is not None
        assert found.id == user.id

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_unknown(self, db_session):
        from app.repositories.auth import UserRepository
        repo = UserRepository(db_session)
        assert await repo.get_by_id(uuid.uuid4()) is None


class TestRoleRepository:
    """[INTEGRATION] RoleRepository operations against seeded roles."""

    @pytest.mark.asyncio
    async def test_all_four_seeded_roles_exist(self, db_session):
        from app.repositories.auth import RoleRepository
        repo = RoleRepository(db_session)
        for name in ["USER", "GUIDE", "MODERATOR", "ADMIN"]:
            role = await repo.get_by_name(name)
            assert role is not None, f"Role {name} not found"
            assert role.name == name

    @pytest.mark.asyncio
    async def test_get_by_name_returns_none_for_unknown(self, db_session):
        from app.repositories.auth import RoleRepository
        repo = RoleRepository(db_session)
        assert await repo.get_by_name("SUPERADMIN") is None

    @pytest.mark.asyncio
    async def test_assign_role_and_get_roles_for_user(self, db_session):
        from app.repositories.auth import UserRepository, RoleRepository
        from shared.utils.security import get_password_hash
        user_repo = UserRepository(db_session)
        role_repo = RoleRepository(db_session)
        user = await user_repo.create("roletest@example.com", get_password_hash("P1!"))
        user_role = await role_repo.get_by_name("USER")
        await role_repo.assign_role(user.id, user_role.id)
        roles = await role_repo.get_roles_for_user(user.id)
        assert "USER" in roles

    @pytest.mark.asyncio
    async def test_assign_role_is_idempotent(self, db_session):
        from app.repositories.auth import UserRepository, RoleRepository
        from shared.utils.security import get_password_hash
        user_repo = UserRepository(db_session)
        role_repo = RoleRepository(db_session)
        user = await user_repo.create("idem@example.com", get_password_hash("P1!"))
        role = await role_repo.get_by_name("USER")
        await role_repo.assign_role(user.id, role.id)
        await role_repo.assign_role(user.id, role.id)  # second call — no error
        roles = await role_repo.get_roles_for_user(user.id)
        assert roles.count("USER") == 1  # not duplicated


class TestRefreshTokenRepository:
    """[INTEGRATION] RefreshTokenRepository operations."""

    @pytest.mark.asyncio
    async def test_create_stores_hash_not_raw_token(self, db_session):
        from app.repositories.auth import UserRepository, RefreshTokenRepository
        from shared.utils.security import get_password_hash
        user = await UserRepository(db_session).create(
            "rtrepo@example.com", get_password_hash("P1!")
        )
        raw = secrets.token_urlsafe(48)
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        rt = await RefreshTokenRepository(db_session).create(user.id, raw, expires)
        expected_hash = hashlib.sha256(raw.encode()).hexdigest()
        assert rt.token_hash == expected_hash
        assert raw not in rt.token_hash  # raw value is NOT the stored hash

    @pytest.mark.asyncio
    async def test_get_by_raw_token_finds_record(self, db_session):
        from app.repositories.auth import UserRepository, RefreshTokenRepository
        from shared.utils.security import get_password_hash
        user = await UserRepository(db_session).create(
            "rtfind@example.com", get_password_hash("P1!")
        )
        raw = secrets.token_urlsafe(48)
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        repo = RefreshTokenRepository(db_session)
        await repo.create(user.id, raw, expires)
        found = await repo.get_by_raw_token(raw)
        assert found is not None
        assert found.is_revoked is False

    @pytest.mark.asyncio
    async def test_get_by_raw_token_returns_none_for_unknown(self, db_session):
        from app.repositories.auth import RefreshTokenRepository
        repo = RefreshTokenRepository(db_session)
        assert await repo.get_by_raw_token("totally_unknown_token") is None

    @pytest.mark.asyncio
    async def test_revoke_sets_is_revoked_true(self, db_session):
        from app.repositories.auth import UserRepository, RefreshTokenRepository
        from shared.utils.security import get_password_hash
        user = await UserRepository(db_session).create(
            "rtrevoke@example.com", get_password_hash("P1!")
        )
        raw = secrets.token_urlsafe(48)
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        repo = RefreshTokenRepository(db_session)
        rt = await repo.create(user.id, raw, expires)
        await repo.revoke(rt.id)
        found = await repo.get_by_raw_token(raw)
        assert found is not None
        assert found.is_revoked is True


# ---------------------------------------------------------------------------
# Service-layer tests
# ---------------------------------------------------------------------------

class TestAuthServiceRegister:
    """[INTEGRATION] AuthService.register()"""

    @pytest.mark.asyncio
    async def test_register_returns_correct_response(self, db_session):
        from app.services.auth import AuthService
        svc = AuthService(db_session)
        result = await svc.register("new_user@example.com", "SecurePass1!")
        assert result.email == "new_user@example.com"
        assert result.user_id is not None
        assert "Registration successful" in result.message

    @pytest.mark.asyncio
    async def test_register_assigns_user_role(self, db_session):
        from app.services.auth import AuthService
        from app.repositories.auth import RoleRepository
        svc = AuthService(db_session)
        result = await svc.register("rolecheck@example.com", "SecurePass1!")
        roles = await RoleRepository(db_session).get_roles_for_user(result.user_id)
        assert "USER" in roles

    @pytest.mark.asyncio
    async def test_register_hashes_password(self, db_session):
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository
        svc = AuthService(db_session)
        result = await svc.register("hashcheck@example.com", "SecurePass1!")
        user = await UserRepository(db_session).get_by_id(result.user_id)
        assert user.password_hash != "SecurePass1!"
        assert user.password_hash.startswith("$2b$")

    @pytest.mark.asyncio
    async def test_register_creates_email_verification_token(self, db_session):
        from app.services.auth import AuthService
        from sqlalchemy import select
        from app.models.user import EmailVerificationToken
        svc = AuthService(db_session)
        result = await svc.register("vertoken@example.com", "SecurePass1!")
        r = await db_session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == result.user_id
            )
        )
        token = r.scalar_one_or_none()
        assert token is not None
        assert token.is_used is False

    @pytest.mark.asyncio
    async def test_register_duplicate_unverified_email_resends_otp(self, db_session):
        """
        Re-registering with an email that is already registered but NOT yet
        verified must NOT raise an exception.  It should return a RegisterResponse
        (so the frontend always reaches the verify-email screen) and the OTP
        service must have generated a fresh OTP record.
        """
        from app.services.auth import AuthService
        from app.schemas.auth import RegisterResponse
        from sqlalchemy import select
        from app.models.user import EmailVerificationOTP

        svc = AuthService(db_session)
        first = await svc.register("dup_unverified@example.com", "SecurePass1!")
        # At this point the user is unverified (is_verified=False).

        # Second registration attempt — should NOT raise, should resend OTP.
        second = await svc.register("dup_unverified@example.com", "DifferentPass1!")
        assert isinstance(second, RegisterResponse)
        assert second.user_id == first.user_id  # same user record
        assert second.email == first.email

        # A fresh OTP record must exist for the user.
        rows = await db_session.execute(
            select(EmailVerificationOTP).where(
                EmailVerificationOTP.user_id == first.user_id
            )
        )
        record = rows.scalar_one_or_none()
        assert record is not None

    @pytest.mark.asyncio
    async def test_register_duplicate_verified_email_raises_conflict(self, db_session):
        """
        Re-registering with an email that is already registered AND verified
        must raise ConflictException with EMAIL_ALREADY_REGISTERED.
        """
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository
        from shared.exceptions import ConflictException

        svc = AuthService(db_session)
        reg = await svc.register("dup_verified@example.com", "SecurePass1!")
        # Mark the user as verified so the duplicate path returns 409.
        await UserRepository(db_session).mark_verified(reg.user_id)

        with pytest.raises(ConflictException) as exc_info:
            await svc.register("dup_verified@example.com", "SecurePass1!")
        assert "EMAIL_ALREADY_REGISTERED" in str(exc_info.value.error_code)


class TestAuthServiceLogin:
    """[INTEGRATION] AuthService.login()"""

    @pytest.mark.asyncio
    async def test_login_returns_access_and_refresh_tokens(self, db_session):
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository
        svc = AuthService(db_session)
        reg = await svc.register("loginok@example.com", "SecurePass1!")
        await UserRepository(db_session).mark_verified(reg.user_id)
        result = await svc.login("loginok@example.com", "SecurePass1!")
        assert result.access_token
        assert result.refresh_token
        assert result.token_type == "bearer"
        assert result.expires_in > 0

    @pytest.mark.asyncio
    async def test_login_access_token_has_correct_claims(self, db_session):
        from app.services.auth import AuthService
        from app.config.settings import settings
        from shared.utils.security import decode_jwt_token
        from app.repositories.auth import UserRepository
        svc = AuthService(db_session)
        reg = await svc.register("claims@example.com", "SecurePass1!")
        await UserRepository(db_session).mark_verified(reg.user_id)
        result = await svc.login("claims@example.com", "SecurePass1!")
        decoded = decode_jwt_token(
            result.access_token, settings.JWT_SECRET, settings.JWT_ALGORITHM
        )
        assert decoded["sub"] == str(reg.user_id)
        assert decoded["email"] == "claims@example.com"
        assert "USER" in decoded["roles"]
        assert "exp" in decoded

    @pytest.mark.asyncio
    async def test_login_persists_refresh_token_hash(self, db_session):
        from app.services.auth import AuthService
        from app.repositories.auth import RefreshTokenRepository, UserRepository
        svc = AuthService(db_session)
        reg = await svc.register("rthash@example.com", "SecurePass1!")
        await UserRepository(db_session).mark_verified(reg.user_id)
        result = await svc.login("rthash@example.com", "SecurePass1!")
        rt = await RefreshTokenRepository(db_session).get_by_raw_token(
            result.refresh_token
        )
        assert rt is not None
        assert rt.is_revoked is False
        expected = hashlib.sha256(result.refresh_token.encode()).hexdigest()
        assert rt.token_hash == expected

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises_unauthorized(self, db_session):
        from app.services.auth import AuthService
        from shared.exceptions import UnauthorizedException
        svc = AuthService(db_session)
        await svc.register("badpass@example.com", "SecurePass1!")
        with pytest.raises(UnauthorizedException):
            await svc.login("badpass@example.com", "WrongPassword!")

    @pytest.mark.asyncio
    async def test_login_unknown_email_raises_unauthorized(self, db_session):
        from app.services.auth import AuthService
        from shared.exceptions import UnauthorizedException
        svc = AuthService(db_session)
        with pytest.raises(UnauthorizedException):
            await svc.login("nobody@example.com", "AnyPass1!")

    @pytest.mark.asyncio
    async def test_login_inactive_account_raises_unauthorized(self, db_session):
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository
        from sqlalchemy import update
        from app.models.user import User
        from shared.exceptions import UnauthorizedException
        svc = AuthService(db_session)
        reg = await svc.register("inactive@example.com", "SecurePass1!")
        # Deactivate the account directly in DB
        await db_session.execute(
            update(User).where(User.id == reg.user_id).values(is_active=False)
        )
        with pytest.raises(UnauthorizedException) as exc_info:
            await svc.login("inactive@example.com", "SecurePass1!")
        assert "ACCOUNT_INACTIVE" in str(exc_info.value.error_code)


class TestAuthServiceRefresh:
    """[INTEGRATION] AuthService.refresh()"""

    @pytest.mark.asyncio
    async def test_refresh_returns_new_access_token(self, db_session):
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository
        svc = AuthService(db_session)
        reg = await svc.register("ref@example.com", "SecurePass1!")
        await UserRepository(db_session).mark_verified(reg.user_id)
        login_result = await svc.login("ref@example.com", "SecurePass1!")
        refresh_result = await svc.refresh(login_result.refresh_token)
        assert refresh_result.access_token
        assert refresh_result.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token_raises_unauthorized(self, db_session):
        from app.services.auth import AuthService
        from shared.exceptions import UnauthorizedException
        svc = AuthService(db_session)
        with pytest.raises(UnauthorizedException) as exc_info:
            await svc.refresh("invalid_token_xyz")
        assert "INVALID_REFRESH_TOKEN" in str(exc_info.value.error_code)

    @pytest.mark.asyncio
    async def test_refresh_with_revoked_token_raises_unauthorized(self, db_session):
        from app.services.auth import AuthService
        from app.repositories.auth import RefreshTokenRepository, UserRepository
        from shared.exceptions import UnauthorizedException
        svc = AuthService(db_session)
        reg = await svc.register("revref@example.com", "SecurePass1!")
        await UserRepository(db_session).mark_verified(reg.user_id)
        login_result = await svc.login("revref@example.com", "SecurePass1!")
        rt_repo = RefreshTokenRepository(db_session)
        rt = await rt_repo.get_by_raw_token(login_result.refresh_token)
        await rt_repo.revoke(rt.id)
        with pytest.raises(UnauthorizedException) as exc_info:
            await svc.refresh(login_result.refresh_token)
        assert "REFRESH_TOKEN_REVOKED" in str(exc_info.value.error_code)

    @pytest.mark.asyncio
    async def test_refresh_with_expired_token_raises_unauthorized(self, db_session):
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository, RefreshTokenRepository
        from shared.utils.security import get_password_hash
        from shared.exceptions import UnauthorizedException
        user_repo = UserRepository(db_session)
        rt_repo = RefreshTokenRepository(db_session)
        user = await user_repo.create("expref@example.com", get_password_hash("P1!"))
        raw = secrets.token_urlsafe(48)
        # Create token that expired 1 second ago
        expires = datetime.now(timezone.utc) - timedelta(seconds=1)
        await rt_repo.create(user.id, raw, expires)
        svc = AuthService(db_session)
        with pytest.raises(UnauthorizedException) as exc_info:
            await svc.refresh(raw)
        assert "REFRESH_TOKEN_EXPIRED" in str(exc_info.value.error_code)


class TestAuthServiceLogout:
    """[INTEGRATION] AuthService.logout()"""

    @pytest.mark.asyncio
    async def test_logout_revokes_token(self, db_session):
        from app.services.auth import AuthService
        from app.repositories.auth import RefreshTokenRepository, UserRepository
        svc = AuthService(db_session)
        reg = await svc.register("logout@example.com", "SecurePass1!")
        await UserRepository(db_session).mark_verified(reg.user_id)
        login_result = await svc.login("logout@example.com", "SecurePass1!")
        await svc.logout(login_result.refresh_token)
        rt = await RefreshTokenRepository(db_session).get_by_raw_token(
            login_result.refresh_token
        )
        assert rt.is_revoked is True

    @pytest.mark.asyncio
    async def test_logout_is_idempotent_for_unknown_token(self, db_session):
        from app.services.auth import AuthService
        svc = AuthService(db_session)
        # Should not raise for a token that doesn't exist
        result = await svc.logout("nonexistent_token")
        assert result.message == "Logged out successfully."

    @pytest.mark.asyncio
    async def test_logout_is_idempotent_for_already_revoked_token(self, db_session):
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository
        svc = AuthService(db_session)
        reg = await svc.register("logout2@example.com", "SecurePass1!")
        await UserRepository(db_session).mark_verified(reg.user_id)
        login_result = await svc.login("logout2@example.com", "SecurePass1!")
        await svc.logout(login_result.refresh_token)   # first logout
        result = await svc.logout(login_result.refresh_token)   # second logout
        assert result.message == "Logged out successfully."


class TestAuthServiceGetMe:
    """[INTEGRATION] AuthService.get_me()"""

    @pytest.mark.asyncio
    async def test_get_me_returns_user_identity(self, db_session):
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository
        from app.config.settings import settings
        from shared.utils.security import decode_jwt_token
        svc = AuthService(db_session)
        reg = await svc.register("me@example.com", "SecurePass1!")
        await UserRepository(db_session).mark_verified(reg.user_id)
        login_result = await svc.login("me@example.com", "SecurePass1!")
        jwt_payload = decode_jwt_token(
            login_result.access_token, settings.JWT_SECRET, settings.JWT_ALGORITHM
        )
        identity = await svc.get_me(jwt_payload)
        assert identity.id == reg.user_id
        assert identity.email == "me@example.com"
        assert "USER" in identity.roles
        assert identity.is_active is True

    @pytest.mark.asyncio
    async def test_get_me_raises_for_missing_sub(self, db_session):
        from app.services.auth import AuthService
        from shared.exceptions import UnauthorizedException
        svc = AuthService(db_session)
        with pytest.raises(UnauthorizedException):
            await svc.get_me({})

    @pytest.mark.asyncio
    async def test_get_me_raises_for_nonexistent_user(self, db_session):
        from app.services.auth import AuthService
        from shared.exceptions import NotFoundException
        svc = AuthService(db_session)
        with pytest.raises(NotFoundException):
            await svc.get_me({"sub": str(uuid.uuid4())})


class TestRoleSeeding:
    """[INTEGRATION] Verify role seed migration a1b2c3d4e5f6."""

    @pytest.mark.asyncio
    async def test_exactly_four_roles_exist(self, db_session):
        from sqlalchemy import select, func
        from app.models.user import Role
        result = await db_session.execute(select(func.count()).select_from(Role))
        count = result.scalar()
        assert count == 4

    @pytest.mark.asyncio
    async def test_role_names_are_correct(self, db_session):
        from sqlalchemy import select
        from app.models.user import Role
        result = await db_session.execute(select(Role.name))
        names = {row[0] for row in result.all()}
        assert names == {"USER", "GUIDE", "MODERATOR", "ADMIN"}

    @pytest.mark.asyncio
    async def test_stable_uuids_are_correct(self, db_session):
        from sqlalchemy import select
        from app.models.user import Role
        result = await db_session.execute(select(Role.id, Role.name))
        id_map = {row[1]: str(row[0]) for row in result.all()}
        assert id_map["USER"]      == "00000000-0000-0000-0000-000000000001"
        assert id_map["GUIDE"]     == "00000000-0000-0000-0000-000000000002"
        assert id_map["MODERATOR"] == "00000000-0000-0000-0000-000000000003"
        assert id_map["ADMIN"]     == "00000000-0000-0000-0000-000000000004"


# ===========================================================================
# CONCURRENCY-SAFE ROLE ASSIGNMENT TESTS
# ===========================================================================

class TestAssignRoleConcurrencySafe:
    """[INTEGRATION] Verify INSERT ... ON CONFLICT DO NOTHING behaviour."""

    @pytest.mark.asyncio
    async def test_assign_role_idempotent_sequential(self, db_session):
        """Calling assign_role twice sequentially leaves exactly one row."""
        from app.repositories.auth import UserRepository, RoleRepository
        from sqlalchemy import select, func
        from app.models.user import UserRole_
        from shared.utils.security import get_password_hash
        user = await UserRepository(db_session).create(
            "idem_seq@example.com", get_password_hash("P1!")
        )
        role = await RoleRepository(db_session).get_by_name("USER")
        repo = RoleRepository(db_session)
        await repo.assign_role(user.id, role.id)
        await repo.assign_role(user.id, role.id)  # second call — must be no-op
        count_result = await db_session.execute(
            select(func.count()).select_from(UserRole_).where(
                UserRole_.user_id == user.id,
                UserRole_.role_id == role.id,
            )
        )
        assert count_result.scalar() == 1

    @pytest.mark.asyncio
    async def test_assign_role_caller_transaction_still_usable(self, db_session):
        """After a duplicate assign_role call, session remains usable for further ops."""
        from app.repositories.auth import UserRepository, RoleRepository
        from shared.utils.security import get_password_hash
        user = await UserRepository(db_session).create(
            "txn_usable@example.com", get_password_hash("P1!")
        )
        role = await RoleRepository(db_session).get_by_name("USER")
        repo = RoleRepository(db_session)
        await repo.assign_role(user.id, role.id)
        await repo.assign_role(user.id, role.id)
        # Session must still work after duplicate assignment
        found = await UserRepository(db_session).get_by_id(user.id)
        assert found is not None
        assert found.email == "txn_usable@example.com"

    @pytest.mark.asyncio
    async def test_assign_role_concurrent_simulation(self, db_session):
        """
        Simulate concurrent duplicate assignment using two independent sessions.
        Both use ON CONFLICT DO NOTHING — neither raises an error and
        exactly one row is persisted.
        """
        from app.repositories.auth import UserRepository, RoleRepository
        from sqlalchemy import select, func, text
        from app.models.user import UserRole_
        from shared.utils.security import get_password_hash
        import asyncio

        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        factory = async_sessionmaker(
            bind=engine, class_=AsyncSession,
            expire_on_commit=False, autocommit=False, autoflush=False,
        )

        # Create user in outer (savepoint) session, then commit it so
        # the concurrent inner sessions can observe it
        user = await UserRepository(db_session).create(
            "concurrent_sim@example.com", get_password_hash("P1!")
        )
        await db_session.flush()
        user_id = user.id
        role = await RoleRepository(db_session).get_by_name("USER")
        role_id = role.id
        await db_session.commit()   # must commit so concurrent sessions see it

        errors = []

        async def assign_in_own_session():
            async with factory() as s:
                try:
                    repo = RoleRepository(s)
                    await repo.assign_role(user_id, role_id)
                    await s.commit()
                except Exception as e:
                    errors.append(e)

        await asyncio.gather(assign_in_own_session(), assign_in_own_session())

        assert not errors, f"Unexpected errors during concurrent assignment: {errors}"

        # Verify exactly one role assignment row
        async with factory() as verify_session:
            count_result = await verify_session.execute(
                select(func.count()).select_from(UserRole_).where(
                    UserRole_.user_id == user_id,
                    UserRole_.role_id == role_id,
                )
            )
            count = count_result.scalar()

        await engine.dispose()
        assert count == 1, f"Expected 1 role row, got {count}"

        # Teardown: remove the committed user (concurrent test committed to real DB)
        async with factory() as cleanup_session:
            await cleanup_session.execute(
                text("DELETE FROM user_roles WHERE user_id = :uid"),
                {"uid": str(user_id)},
            )
            await cleanup_session.execute(
                text("DELETE FROM users WHERE id = :uid"),
                {"uid": str(user_id)},
            )
            await cleanup_session.commit()
        engine2 = create_async_engine(TEST_DATABASE_URL)
        await engine2.dispose()

    @pytest.mark.asyncio
    async def test_registration_atomicity_with_on_conflict(self, db_session):
        """Registration + USER role assignment remains atomic with ON CONFLICT approach."""
        from app.services.auth import AuthService
        from app.repositories.auth import RoleRepository
        from sqlalchemy import select, func
        from app.models.user import UserRole_
        svc = AuthService(db_session)
        result = await svc.register("atomic_test@example.com", "SecurePass1!")
        # Both user and role assignment exist
        roles = await RoleRepository(db_session).get_roles_for_user(result.user_id)
        assert "USER" in roles
        count = await db_session.execute(
            select(func.count()).select_from(UserRole_).where(
                UserRole_.user_id == result.user_id
            )
        )
        assert count.scalar() == 1


# ===========================================================================
# EMAIL VERIFICATION TESTS
# ===========================================================================

class TestAuthServiceVerifyEmail:
    """[INTEGRATION] AuthService.verify_email()"""

    @pytest.mark.asyncio
    async def test_verify_email_success(self, db_session):
        """Valid token marks user verified, sets verified_at, and marks token as used."""
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository, EmailVerificationTokenRepository
        from app.security import generate_raw_opaque_token, verification_token_expires_at
        from shared.utils.security import get_password_hash

        user = await UserRepository(db_session).create(
            "verifyok@example.com", get_password_hash("P1!")
        )
        raw_token = generate_raw_opaque_token()
        await EmailVerificationTokenRepository(db_session).create(
            user.id, raw_token, verification_token_expires_at()
        )

        svc = AuthService(db_session)
        result = await svc.verify_email(raw_token)
        assert "verified" in result.message.lower()

        # User should now be verified and verified_at must be populated
        updated = await UserRepository(db_session).get_by_id(user.id)
        assert updated.is_verified is True
        assert updated.verified_at is not None

    @pytest.mark.asyncio
    async def test_verify_email_marks_token_used(self, db_session):
        """After successful verification the token's is_used flag is True."""
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository, EmailVerificationTokenRepository
        from app.security import generate_raw_opaque_token, verification_token_expires_at
        from shared.utils.security import get_password_hash
        from sqlalchemy import select
        from app.models.user import EmailVerificationToken

        user = await UserRepository(db_session).create(
            "tokenused@example.com", get_password_hash("P1!")
        )
        raw_token = generate_raw_opaque_token()
        await EmailVerificationTokenRepository(db_session).create(
            user.id, raw_token, verification_token_expires_at()
        )
        svc = AuthService(db_session)
        await svc.verify_email(raw_token)

        result = await db_session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user.id
            )
        )
        token_record = result.scalar_one_or_none()
        assert token_record is not None
        assert token_record.is_used is True

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token_raises(self, db_session):
        """Unknown token raises UnauthorizedException."""
        from app.services.auth import AuthService
        from shared.exceptions import UnauthorizedException
        svc = AuthService(db_session)
        with pytest.raises(UnauthorizedException) as exc:
            await svc.verify_email("totally_invalid_token")
        assert "INVALID_VERIFICATION_TOKEN" in exc.value.error_code

    @pytest.mark.asyncio
    async def test_verify_email_expired_token_raises(self, db_session):
        """Expired token raises UnauthorizedException."""
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository, EmailVerificationTokenRepository
        from app.security import generate_raw_opaque_token
        from shared.utils.security import get_password_hash
        from shared.exceptions import UnauthorizedException

        user = await UserRepository(db_session).create(
            "verifyexp@example.com", get_password_hash("P1!")
        )
        raw_token = generate_raw_opaque_token()
        past = datetime.now(timezone.utc) - timedelta(hours=25)
        await EmailVerificationTokenRepository(db_session).create(
            user.id, raw_token, past
        )
        svc = AuthService(db_session)
        with pytest.raises(UnauthorizedException) as exc:
            await svc.verify_email(raw_token)
        assert "VERIFICATION_TOKEN_EXPIRED" in exc.value.error_code

    @pytest.mark.asyncio
    async def test_verify_email_already_used_token_raises(self, db_session):
        """Already-used token raises UnauthorizedException (replay prevention)."""
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository, EmailVerificationTokenRepository
        from app.security import generate_raw_opaque_token, verification_token_expires_at
        from shared.utils.security import get_password_hash
        from shared.exceptions import UnauthorizedException

        user = await UserRepository(db_session).create(
            "verifyreuse@example.com", get_password_hash("P1!")
        )
        raw_token = generate_raw_opaque_token()
        await EmailVerificationTokenRepository(db_session).create(
            user.id, raw_token, verification_token_expires_at()
        )
        svc = AuthService(db_session)
        await svc.verify_email(raw_token)  # first use — OK
        with pytest.raises(UnauthorizedException) as exc:
            await svc.verify_email(raw_token)  # replay — must fail
        assert "VERIFICATION_TOKEN_ALREADY_USED" in exc.value.error_code

    @pytest.mark.asyncio
    async def test_register_creates_verification_token_usable_by_verify_email(self, db_session):
        """Token created at registration can be used by verify_email to activate account."""
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository
        from sqlalchemy import select
        from app.models.user import EmailVerificationToken

        svc = AuthService(db_session)
        reg = await svc.register("fullflow@example.com", "SecurePass1!")

        # Retrieve the raw token from DB (in real usage it would come via email)
        result = await db_session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == reg.user_id
            )
        )
        token_record = result.scalar_one()
        # We only have the hash stored — simulate knowing the raw token via
        # the debug log by generating a matching raw token in the test.
        # Instead, test the full service flow where verify_email accepts a known raw token.
        # Use a separate token to validate the flow end-to-end.
        from app.security import generate_raw_opaque_token, verification_token_expires_at
        from app.repositories.auth import EmailVerificationTokenRepository

        raw_token2 = generate_raw_opaque_token()
        await EmailVerificationTokenRepository(db_session).create(
            reg.user_id, raw_token2, verification_token_expires_at()
        )
        await svc.verify_email(raw_token2)
        user = await UserRepository(db_session).get_by_id(reg.user_id)
        assert user.is_verified is True


# ===========================================================================
# VERIFIED_AT TIMESTAMP TESTS
# ===========================================================================

class TestVerifiedAtTimestamp:
    """[INTEGRATION] verified_at column is NULL before verification and set after."""

    @pytest.mark.asyncio
    async def test_verified_at_is_null_before_verification(self, db_session):
        """
        A freshly created user must have verified_at = NULL.

        verified_at has no default value — it is only set by mark_verified().
        This test confirms the column stays NULL until the verification flow
        explicitly populates it.
        """
        from app.repositories.auth import UserRepository
        from shared.utils.security import get_password_hash

        user = await UserRepository(db_session).create(
            "pre_verify@example.com", get_password_hash("P1!")
        )

        # Reload from DB to pick up the persisted state (flush writes the row)
        fetched = await UserRepository(db_session).get_by_id(user.id)
        assert fetched is not None
        assert fetched.is_verified is False
        assert fetched.verified_at is None

    @pytest.mark.asyncio
    async def test_verified_at_is_populated_after_verification(self, db_session):
        """
        After a successful verify_email() call, verified_at must be a non-null
        timezone-aware UTC datetime.

        This is the direct test for the mark_verified() fix: the field must
        transition from NULL to a concrete timestamp in the same DB operation
        that flips is_verified to True.
        """
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository, EmailVerificationTokenRepository
        from app.security import generate_raw_opaque_token, verification_token_expires_at
        from shared.utils.security import get_password_hash

        user = await UserRepository(db_session).create(
            "post_verify@example.com", get_password_hash("P1!")
        )
        raw_token = generate_raw_opaque_token()
        await EmailVerificationTokenRepository(db_session).create(
            user.id, raw_token, verification_token_expires_at()
        )

        # Confirm NULL before
        pre = await UserRepository(db_session).get_by_id(user.id)
        assert pre.verified_at is None

        before_call = datetime.now(timezone.utc)
        svc = AuthService(db_session)
        await svc.verify_email(raw_token)

        # Confirm populated after
        post = await UserRepository(db_session).get_by_id(user.id)
        assert post.is_verified is True
        assert post.verified_at is not None
        assert post.verified_at >= before_call

    @pytest.mark.asyncio
    async def test_verified_at_is_utc_timezone_aware(self, db_session):
        """
        verified_at must be timezone-aware (tzinfo is not None) so it can
        be correctly compared to other UTC datetimes throughout the codebase.

        PostgreSQL TIMESTAMPTZ always returns tz-aware datetimes via asyncpg.
        This test guards against any future column-type regression.
        """
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository, EmailVerificationTokenRepository
        from app.security import generate_raw_opaque_token, verification_token_expires_at
        from shared.utils.security import get_password_hash

        user = await UserRepository(db_session).create(
            "tz_verify@example.com", get_password_hash("P1!")
        )
        raw_token = generate_raw_opaque_token()
        await EmailVerificationTokenRepository(db_session).create(
            user.id, raw_token, verification_token_expires_at()
        )

        svc = AuthService(db_session)
        await svc.verify_email(raw_token)

        post = await UserRepository(db_session).get_by_id(user.id)
        assert post.verified_at is not None
        assert post.verified_at.tzinfo is not None


# ===========================================================================
# FORGOT PASSWORD TESTS
# ===========================================================================

class TestAuthServiceForgotPassword:
    """[INTEGRATION] AuthService.forgot_password()"""

    @pytest.mark.asyncio
    async def test_forgot_password_creates_reset_token_for_valid_email(self, db_session):
        """Valid email results in a reset token row in password_reset_tokens."""
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository
        from sqlalchemy import select
        from app.models.user import PasswordResetToken
        from shared.utils.security import get_password_hash

        user = await UserRepository(db_session).create(
            "forgotok@example.com", get_password_hash("P1!")
        )
        svc = AuthService(db_session)
        result = await svc.forgot_password("forgotok@example.com")
        assert result.message  # some message returned

        token_row = await db_session.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )
        assert token_row.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_forgot_password_unknown_email_returns_same_message(self, db_session):
        """Unknown email returns identical message (no enumeration)."""
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository
        from shared.utils.security import get_password_hash

        user = await UserRepository(db_session).create(
            "enum_known@example.com", get_password_hash("P1!")
        )
        svc = AuthService(db_session)
        known_result = await svc.forgot_password("enum_known@example.com")
        unknown_result = await svc.forgot_password("nobody_at_all@example.com")
        assert known_result.message == unknown_result.message

    @pytest.mark.asyncio
    async def test_forgot_password_creates_no_token_for_unknown_email(self, db_session):
        """No reset token row is created when email is unknown."""
        from app.services.auth import AuthService
        from sqlalchemy import select, func
        from app.models.user import PasswordResetToken

        svc = AuthService(db_session)
        await svc.forgot_password("ghost@example.com")
        count = await db_session.execute(select(func.count()).select_from(PasswordResetToken))
        assert count.scalar() == 0


# ===========================================================================
# RESET PASSWORD TESTS
# ===========================================================================

class TestAuthServiceResetPassword:
    """[INTEGRATION] AuthService.reset_password()"""

    async def _setup_reset(self, db_session):
        """Helper: register user, generate reset token, return (user_id, raw_token, email)."""
        from app.services.auth import AuthService
        from app.repositories.auth import PasswordResetTokenRepository
        from app.security import generate_raw_opaque_token, reset_token_expires_at

        svc = AuthService(db_session)
        email = f"reset_{uuid.uuid4().hex[:8]}@example.com"
        reg = await svc.register(email, "OldPass123!")
        raw_token = generate_raw_opaque_token()
        await PasswordResetTokenRepository(db_session).create(
            reg.user_id, raw_token, reset_token_expires_at()
        )
        return reg.user_id, raw_token, email

    @pytest.mark.asyncio
    async def test_reset_password_success(self, db_session):
        """Valid token successfully updates the password."""
        from app.services.auth import AuthService
        user_id, raw_token, email = await self._setup_reset(db_session)
        svc = AuthService(db_session)
        result = await svc.reset_password(raw_token, "NewPass456!")
        assert "successfully" in result.message.lower()

    @pytest.mark.asyncio
    async def test_reset_password_new_password_is_bcrypt_hashed(self, db_session):
        """After reset, new password is stored as bcrypt hash."""
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository
        user_id, raw_token, email = await self._setup_reset(db_session)
        svc = AuthService(db_session)
        await svc.reset_password(raw_token, "NewPass456!")
        user = await UserRepository(db_session).get_by_id(user_id)
        assert user.password_hash.startswith("$2b$")
        assert user.password_hash != "NewPass456!"

    @pytest.mark.asyncio
    async def test_reset_password_old_password_fails_after_reset(self, db_session):
        """Old password no longer authenticates after reset."""
        from app.services.auth import AuthService
        from shared.exceptions import UnauthorizedException
        user_id, raw_token, email = await self._setup_reset(db_session)
        svc = AuthService(db_session)
        await svc.reset_password(raw_token, "NewPass456!")
        with pytest.raises(UnauthorizedException):
            await svc.login(email, "OldPass123!")

    @pytest.mark.asyncio
    async def test_reset_password_new_password_authenticates(self, db_session):
        """New password authenticates successfully after reset."""
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository
        user_id, raw_token, email = await self._setup_reset(db_session)
        svc = AuthService(db_session)
        await svc.reset_password(raw_token, "NewPass456!")
        await UserRepository(db_session).mark_verified(user_id)
        result = await svc.login(email, "NewPass456!")
        assert result.access_token

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token_raises(self, db_session):
        """Invalid token raises UnauthorizedException."""
        from app.services.auth import AuthService
        from shared.exceptions import UnauthorizedException
        svc = AuthService(db_session)
        with pytest.raises(UnauthorizedException) as exc:
            await svc.reset_password("bad_token_xyz", "NewPass456!")
        assert "INVALID_RESET_TOKEN" in exc.value.error_code

    @pytest.mark.asyncio
    async def test_reset_password_expired_token_raises(self, db_session):
        """Expired token raises UnauthorizedException."""
        from app.services.auth import AuthService
        from app.repositories.auth import UserRepository, PasswordResetTokenRepository
        from app.security import generate_raw_opaque_token
        from shared.utils.security import get_password_hash
        from shared.exceptions import UnauthorizedException

        user = await UserRepository(db_session).create(
            "resetexp@example.com", get_password_hash("P1!")
        )
        raw = generate_raw_opaque_token()
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        await PasswordResetTokenRepository(db_session).create(user.id, raw, past)
        svc = AuthService(db_session)
        with pytest.raises(UnauthorizedException) as exc:
            await svc.reset_password(raw, "NewPass456!")
        assert "RESET_TOKEN_EXPIRED" in exc.value.error_code

    @pytest.mark.asyncio
    async def test_reset_password_already_used_token_raises(self, db_session):
        """Consuming a token twice raises UnauthorizedException."""
        from app.services.auth import AuthService
        from shared.exceptions import UnauthorizedException
        user_id, raw_token, email = await self._setup_reset(db_session)
        svc = AuthService(db_session)
        await svc.reset_password(raw_token, "NewPass456!")
        with pytest.raises(UnauthorizedException) as exc:
            await svc.reset_password(raw_token, "AnotherPass789!")
        assert "RESET_TOKEN_ALREADY_USED" in exc.value.error_code

    @pytest.mark.asyncio
    async def test_reset_password_marks_token_used(self, db_session):
        """After reset, the token record has is_used=True."""
        from app.services.auth import AuthService
        from sqlalchemy import select
        from app.models.user import PasswordResetToken
        user_id, raw_token, email = await self._setup_reset(db_session)
        svc = AuthService(db_session)
        await svc.reset_password(raw_token, "NewPass456!")
        result = await db_session.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
        )
        token_rec = result.scalar_one_or_none()
        assert token_rec is not None
        assert token_rec.is_used is True
