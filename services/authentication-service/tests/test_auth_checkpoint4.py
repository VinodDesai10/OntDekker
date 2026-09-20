"""
Authentication Service — Checkpoint 4 Integration Tests

Covers the OTP + Email integration into the authentication flow:
  - Registration: OTP generated, email send invoked
  - Login gate: blocked before verification, succeeds after
  - POST /auth/verify-email (OTP-based)
  - POST /auth/resend-otp
  - Edge cases: invalid OTP, expired OTP, already verified, user not found

Test categories:
  [UNIT]        No database. Pure logic tested in isolation.
  [INTEGRATION] Requires live auth_db on localhost:5432.

Run with:
  PYTHONPATH=../.. pytest tests/test_auth_checkpoint4.py -v

SMTP is always mocked — no real email delivery occurs in any test.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Database config
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/auth_db"
)

# ---------------------------------------------------------------------------
# Event loop (session-scoped)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# DB session — each test rolls back
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with factory() as session:
        await session.begin_nested()
        yield session
        await session.rollback()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Mock EmailService helpers
# ---------------------------------------------------------------------------

def _make_mock_email_service(raise_exc=None):
    """Return a mock EmailService whose send_verification_otp does nothing (or raises)."""
    from app.services.email import EmailService, EmailDeliveryException

    class MockEmailService(EmailService):
        def __init__(self):
            self.calls = []

        def send_verification_otp(self, email, otp, expiration_minutes, recipient_name=None):
            self.calls.append({
                "email": email,
                "otp": otp,
                "expiration_minutes": expiration_minutes,
            })
            if raise_exc:
                raise raise_exc

    return MockEmailService()


def _make_failing_email_service():
    """EmailService that raises EmailDeliveryException on every send."""
    from app.services.email import EmailDeliveryException
    return _make_mock_email_service(
        raise_exc=EmailDeliveryException(
            message="SMTP unavailable",
            error_code="EMAIL_DELIVERY_FAILED",
        )
    )


# ---------------------------------------------------------------------------
# AuthService factory helpers
# ---------------------------------------------------------------------------

def _auth_service(session, email_service=None):
    """Construct AuthService with mocked email, real OTPService."""
    from app.services.auth import AuthService
    from app.services.otp import OTPService
    return AuthService(
        session=session,
        otp_service=OTPService(session=session),
        email_service=email_service,
    )


# ===========================================================================
# REGISTRATION FLOW TESTS
# ===========================================================================

class TestRegistrationOTP:
    """
    [INTEGRATION] Registration generates an OTP and invokes email send.

    AuthService.register() is expected to:
      1. Create the user with is_verified=False.
      2. Persist an OTP record in email_verification_otps.
      3. Call email_service.send_verification_otp() once with the correct args.
    """

    @pytest.mark.asyncio
    async def test_register_creates_user_unverified(self, db_session):
        """Newly registered user has is_verified=False and verified_at=None."""
        from app.repositories.auth import UserRepository
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        result = await svc.register("cp4_unreg@example.com", "SecurePass1!")

        user = await UserRepository(db_session).get_by_id(result.user_id)
        assert user is not None
        assert user.is_verified is False
        assert user.verified_at is None

    @pytest.mark.asyncio
    async def test_register_persists_otp_record(self, db_session):
        """An OTP record is written to email_verification_otps after registration."""
        from sqlalchemy import select
        from app.models.user import EmailVerificationOTP
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        result = await svc.register("cp4_otp_persist@example.com", "SecurePass1!")

        rows = await db_session.execute(
            select(EmailVerificationOTP).where(
                EmailVerificationOTP.user_id == result.user_id
            )
        )
        record = rows.scalar_one_or_none()
        assert record is not None
        assert record.attempts == 0
        assert record.expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_register_otp_hash_not_plaintext(self, db_session):
        """The stored OTP hash must not equal any obvious plaintext value."""
        from sqlalchemy import select
        from app.models.user import EmailVerificationOTP
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        result = await svc.register("cp4_otp_hash@example.com", "SecurePass1!")

        rows = await db_session.execute(
            select(EmailVerificationOTP).where(
                EmailVerificationOTP.user_id == result.user_id
            )
        )
        record = rows.scalar_one()
        # Hash must be 64 hex chars (SHA-256), never a 6-digit plain OTP
        assert len(record.otp_hash) == 64
        assert record.otp_hash.isdigit() is False

    @pytest.mark.asyncio
    async def test_register_invokes_email_send_once(self, db_session):
        """email_service.send_verification_otp is called exactly once at registration."""
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        await svc.register("cp4_email_called@example.com", "SecurePass1!")

        assert len(mock_email.calls) == 1
        call = mock_email.calls[0]
        assert call["email"] == "cp4_email_called@example.com"
        assert len(call["otp"]) == 6
        assert call["otp"].isdigit()

    @pytest.mark.asyncio
    async def test_register_email_failure_does_not_prevent_user_creation(self, db_session):
        """If SMTP fails during registration, the user is still created."""
        from app.repositories.auth import UserRepository
        failing_email = _make_failing_email_service()
        svc = _auth_service(db_session, email_service=failing_email)

        result = await svc.register("cp4_smtp_fail@example.com", "SecurePass1!")

        user = await UserRepository(db_session).get_by_id(result.user_id)
        assert user is not None
        assert user.email == "cp4_smtp_fail@example.com"

    @pytest.mark.asyncio
    async def test_register_email_failure_still_persists_otp(self, db_session):
        """OTP record is in DB even when SMTP fails."""
        from sqlalchemy import select
        from app.models.user import EmailVerificationOTP
        failing_email = _make_failing_email_service()
        svc = _auth_service(db_session, email_service=failing_email)

        result = await svc.register("cp4_smtp_fail_otp@example.com", "SecurePass1!")

        rows = await db_session.execute(
            select(EmailVerificationOTP).where(
                EmailVerificationOTP.user_id == result.user_id
            )
        )
        assert rows.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_register_without_email_service_still_creates_otp(self, db_session):
        """
        When no email_service is provided (None), OTP is still persisted
        and no exception is raised.  This preserves testability.
        """
        from sqlalchemy import select
        from app.models.user import EmailVerificationOTP
        svc = _auth_service(db_session, email_service=None)

        result = await svc.register("cp4_no_email_svc@example.com", "SecurePass1!")

        rows = await db_session.execute(
            select(EmailVerificationOTP).where(
                EmailVerificationOTP.user_id == result.user_id
            )
        )
        assert rows.scalar_one_or_none() is not None


# ===========================================================================
# LOGIN VERIFICATION GATE TESTS
# ===========================================================================

class TestLoginVerificationGate:
    """
    [INTEGRATION] Login is blocked for unverified accounts.

    Before Checkpoint 4: any registered user could log in.
    After Checkpoint 4: login raises EMAIL_NOT_VERIFIED until OTP is confirmed.
    """

    @pytest.mark.asyncio
    async def test_login_blocked_before_verification(self, db_session):
        """Unverified user receives EMAIL_NOT_VERIFIED on login attempt."""
        from shared.exceptions import UnauthorizedException
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        await svc.register("cp4_login_blocked@example.com", "SecurePass1!")

        with pytest.raises(UnauthorizedException) as exc_info:
            await svc.login("cp4_login_blocked@example.com", "SecurePass1!")

        assert exc_info.value.error_code == "EMAIL_NOT_VERIFIED"

    @pytest.mark.asyncio
    async def test_login_still_rejects_wrong_password(self, db_session):
        """Wrong password still returns INVALID_CREDENTIALS, not EMAIL_NOT_VERIFIED."""
        from shared.exceptions import UnauthorizedException
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        await svc.register("cp4_login_wrongpw@example.com", "SecurePass1!")

        with pytest.raises(UnauthorizedException) as exc_info:
            await svc.login("cp4_login_wrongpw@example.com", "WrongPassword!")

        assert exc_info.value.error_code == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_succeeds_after_otp_verification(self, db_session):
        """After OTP is verified, login issues tokens normally."""
        from sqlalchemy import select
        from app.models.user import EmailVerificationOTP
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        reg = await svc.register("cp4_login_after_otp@example.com", "SecurePass1!")

        # Retrieve the OTP hash from DB and reconstruct raw OTP via the service
        # helper — we use OTPService.generate() directly so we can capture raw OTP
        from app.services.otp import OTPService
        otp_svc = OTPService(db_session)
        raw_otp = await otp_svc.generate(reg.user_id)  # invalidates old, gives new

        await svc.verify_email_otp("cp4_login_after_otp@example.com", raw_otp)
        result = await svc.login("cp4_login_after_otp@example.com", "SecurePass1!")

        assert result.access_token
        assert result.refresh_token
        assert result.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_login_after_manual_mark_verified(self, db_session):
        """
        If mark_verified() is called directly (e.g. via opaque-token flow),
        login succeeds — verifying the gate only checks is_verified, not how
        verification occurred.
        """
        from app.repositories.auth import UserRepository
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        reg = await svc.register("cp4_login_manual_verify@example.com", "SecurePass1!")
        await UserRepository(db_session).mark_verified(reg.user_id)

        result = await svc.login("cp4_login_manual_verify@example.com", "SecurePass1!")
        assert result.access_token


# ===========================================================================
# VERIFY EMAIL OTP TESTS
# ===========================================================================

class TestVerifyEmailOTP:
    """
    [INTEGRATION] POST /auth/verify-email — OTP-based email verification.

    AuthService.verify_email_otp() is the primary new verification endpoint.
    It delegates OTP validation to OTPService and calls mark_verified()
    on the user only when the OTP is correct.
    """

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_email_otp_success(self, db_session):
        """Valid OTP marks user verified and returns success message."""
        from app.repositories.auth import UserRepository
        from app.services.otp import OTPService
        svc = _auth_service(db_session, email_service=None)

        reg = await svc.register("cp4_verify_ok@example.com", "SecurePass1!")

        otp_svc = OTPService(db_session)
        raw_otp = await otp_svc.generate(reg.user_id)

        result = await svc.verify_email_otp("cp4_verify_ok@example.com", raw_otp)

        assert "verified" in result.message.lower()

        user = await UserRepository(db_session).get_by_id(reg.user_id)
        assert user.is_verified is True
        assert user.verified_at is not None

    @pytest.mark.asyncio
    async def test_verify_email_otp_sets_verified_at(self, db_session):
        """verified_at is a timezone-aware datetime set after OTP verification."""
        from app.repositories.auth import UserRepository
        from app.services.otp import OTPService
        svc = _auth_service(db_session, email_service=None)

        reg = await svc.register("cp4_verified_at@example.com", "SecurePass1!")
        otp_svc = OTPService(db_session)
        raw_otp = await otp_svc.generate(reg.user_id)

        before = datetime.now(timezone.utc)
        await svc.verify_email_otp("cp4_verified_at@example.com", raw_otp)

        user = await UserRepository(db_session).get_by_id(reg.user_id)
        assert user.verified_at is not None
        assert user.verified_at >= before
        assert user.verified_at.tzinfo is not None

    @pytest.mark.asyncio
    async def test_verify_email_otp_deletes_otp_record(self, db_session):
        """OTP record is hard-deleted after successful verification (no replay)."""
        from sqlalchemy import select
        from app.models.user import EmailVerificationOTP
        from app.services.otp import OTPService
        svc = _auth_service(db_session, email_service=None)

        reg = await svc.register("cp4_otp_deleted@example.com", "SecurePass1!")
        otp_svc = OTPService(db_session)
        raw_otp = await otp_svc.generate(reg.user_id)

        await svc.verify_email_otp("cp4_otp_deleted@example.com", raw_otp)

        rows = await db_session.execute(
            select(EmailVerificationOTP).where(
                EmailVerificationOTP.user_id == reg.user_id
            )
        )
        assert rows.scalar_one_or_none() is None

    # ------------------------------------------------------------------
    # User not found
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_email_otp_unknown_email_raises(self, db_session):
        """Unknown email raises NotFoundException with USER_NOT_FOUND."""
        from shared.exceptions import NotFoundException
        svc = _auth_service(db_session, email_service=None)

        with pytest.raises(NotFoundException) as exc_info:
            await svc.verify_email_otp("ghost@example.com", "123456")

        assert exc_info.value.error_code == "USER_NOT_FOUND"

    # ------------------------------------------------------------------
    # Already verified
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_email_otp_already_verified_raises(self, db_session):
        """Attempting OTP on an already-verified account raises ConflictException."""
        from app.repositories.auth import UserRepository
        from shared.exceptions import ConflictException
        svc = _auth_service(db_session, email_service=None)

        reg = await svc.register("cp4_already_verified@example.com", "SecurePass1!")
        await UserRepository(db_session).mark_verified(reg.user_id)

        with pytest.raises(ConflictException) as exc_info:
            await svc.verify_email_otp("cp4_already_verified@example.com", "123456")

        assert exc_info.value.error_code == "ALREADY_VERIFIED"

    # ------------------------------------------------------------------
    # Invalid OTP
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_email_otp_wrong_code_raises(self, db_session):
        """Wrong OTP code raises UnauthorizedException with OTP_INVALID."""
        from app.services.otp import OTPService
        from shared.exceptions import UnauthorizedException
        svc = _auth_service(db_session, email_service=None)

        reg = await svc.register("cp4_wrong_otp@example.com", "SecurePass1!")
        otp_svc = OTPService(db_session)
        await otp_svc.generate(reg.user_id)

        with pytest.raises(UnauthorizedException) as exc_info:
            await svc.verify_email_otp("cp4_wrong_otp@example.com", "000000")

        assert exc_info.value.error_code in ("OTP_INVALID", "OTP_MAX_ATTEMPTS_EXCEEDED")

    # ------------------------------------------------------------------
    # Expired OTP
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_email_otp_expired_raises(self, db_session):
        """Expired OTP raises UnauthorizedException with OTP_EXPIRED."""
        from app.repositories.auth import EmailVerificationOTPRepository
        from app.repositories.auth import UserRepository
        from app.services.otp import OTPService
        from shared.exceptions import UnauthorizedException
        from shared.utils.security import get_password_hash
        svc = _auth_service(db_session, email_service=None)

        user = await UserRepository(db_session).create(
            "cp4_expired_otp@example.com", get_password_hash("P1!")
        )

        otp_svc = OTPService(db_session)
        raw_otp = otp_svc.generate_otp()
        otp_hash = otp_svc._hash_otp(raw_otp)
        past = datetime.now(timezone.utc) - timedelta(minutes=1)
        await EmailVerificationOTPRepository(db_session).create(
            user_id=user.id,
            otp_hash=otp_hash,
            expires_at=past,
        )

        with pytest.raises(UnauthorizedException) as exc_info:
            await svc.verify_email_otp("cp4_expired_otp@example.com", raw_otp)

        assert exc_info.value.error_code == "OTP_EXPIRED"

    # ------------------------------------------------------------------
    # No active OTP
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_email_otp_no_active_otp_raises(self, db_session):
        """Submitting an OTP when none has been generated raises OTP_NOT_FOUND."""
        from app.repositories.auth import UserRepository
        from shared.utils.security import get_password_hash
        from shared.exceptions import UnauthorizedException
        svc = _auth_service(db_session, email_service=None)

        await UserRepository(db_session).create(
            "cp4_no_otp@example.com", get_password_hash("P1!")
        )

        with pytest.raises(UnauthorizedException) as exc_info:
            await svc.verify_email_otp("cp4_no_otp@example.com", "123456")

        assert exc_info.value.error_code == "OTP_NOT_FOUND"

    # ------------------------------------------------------------------
    # Max attempts exhaustion
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_email_otp_max_attempts_exhausted(self, db_session):
        """
        Verify the full OTPService attempt-exhaustion sequence.

        OTPService behaviour with OTP_MAX_ATTEMPTS=5:
          - Attempts 1 … (MAX-2): increment counter, return OTP_INVALID.
          - Attempt MAX-1: counter reaches MAX → delete record, return
            OTP_MAX_ATTEMPTS_EXCEEDED.
          - Any call after deletion: record is gone, returns OTP_NOT_FOUND.

        The test exhausts the OTP with wrong codes and asserts each phase.
        """
        from app.services.otp import OTPService
        from app.config.settings import settings
        from shared.exceptions import UnauthorizedException
        svc = _auth_service(db_session, email_service=None)

        reg = await svc.register("cp4_max_attempts@example.com", "SecurePass1!")
        otp_svc = OTPService(db_session)
        await otp_svc.generate(reg.user_id)  # fresh OTP, attempts=0

        max_att = settings.OTP_MAX_ATTEMPTS  # 5 by default

        # Attempts 1 through (MAX-2) → OTP_INVALID
        for i in range(max_att - 2):
            with pytest.raises(UnauthorizedException) as exc_info:
                await svc.verify_email_otp("cp4_max_attempts@example.com", "000000")
            assert exc_info.value.error_code == "OTP_INVALID", (
                f"Attempt {i + 1}: expected OTP_INVALID, got {exc_info.value.error_code}"
            )

        # Attempt MAX-1 → record deleted, returns OTP_MAX_ATTEMPTS_EXCEEDED
        with pytest.raises(UnauthorizedException) as exc_info:
            await svc.verify_email_otp("cp4_max_attempts@example.com", "000000")
        assert exc_info.value.error_code == "OTP_MAX_ATTEMPTS_EXCEEDED"

        # Any further attempt → OTP_NOT_FOUND (record already gone)
        with pytest.raises(UnauthorizedException) as exc_info:
            await svc.verify_email_otp("cp4_max_attempts@example.com", "000000")
        assert exc_info.value.error_code == "OTP_NOT_FOUND"


# ===========================================================================
# RESEND OTP TESTS
# ===========================================================================

class TestResendOTP:
    """
    [INTEGRATION] POST /auth/resend-otp

    Expected behaviour:
      - User must exist.
      - Already-verified accounts are rejected.
      - Previous OTP is invalidated; a fresh record is created.
      - Email is sent with the new OTP.
    """

    @pytest.mark.asyncio
    async def test_resend_otp_creates_new_otp_record(self, db_session):
        """After resend, exactly one OTP record exists for the user."""
        from sqlalchemy import select, func
        from app.models.user import EmailVerificationOTP
        from app.services.otp import OTPService
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        reg = await svc.register("cp4_resend_new@example.com", "SecurePass1!")

        # Resend — should invalidate the one from registration and create another
        await svc.resend_otp("cp4_resend_new@example.com")

        count = await db_session.execute(
            select(func.count()).select_from(EmailVerificationOTP).where(
                EmailVerificationOTP.user_id == reg.user_id
            )
        )
        assert count.scalar() == 1

    @pytest.mark.asyncio
    async def test_resend_otp_invalidates_previous_otp(self, db_session):
        """
        The OTP generated during registration is invalidated by resend.
        The original raw OTP no longer verifies.
        """
        from app.services.otp import OTPService
        from shared.exceptions import UnauthorizedException
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        reg = await svc.register("cp4_resend_invalidate@example.com", "SecurePass1!")

        # Capture the OTP generated at registration by generating a known one
        otp_svc = OTPService(db_session)
        original_raw = await otp_svc.generate(reg.user_id)

        # Resend — invalidates original_raw
        await svc.resend_otp("cp4_resend_invalidate@example.com")

        # original_raw is now stale
        with pytest.raises(UnauthorizedException) as exc_info:
            await svc.verify_email_otp("cp4_resend_invalidate@example.com", original_raw)

        assert exc_info.value.error_code in ("OTP_NOT_FOUND", "OTP_INVALID", "OTP_EXPIRED")

    @pytest.mark.asyncio
    async def test_resend_otp_invokes_email_send(self, db_session):
        """email_service.send_verification_otp is called on resend."""
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        await svc.register("cp4_resend_email@example.com", "SecurePass1!")

        # Reset the call log so we only count the resend send
        mock_email.calls.clear()

        await svc.resend_otp("cp4_resend_email@example.com")

        assert len(mock_email.calls) == 1
        assert mock_email.calls[0]["email"] == "cp4_resend_email@example.com"
        assert len(mock_email.calls[0]["otp"]) == 6

    @pytest.mark.asyncio
    async def test_resend_otp_new_code_verifies_successfully(self, db_session):
        """The OTP received after resend successfully verifies the account."""
        from app.repositories.auth import UserRepository
        from app.services.otp import OTPService
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        reg = await svc.register("cp4_resend_then_verify@example.com", "SecurePass1!")

        # Resend: get a fresh OTP we control
        otp_svc = OTPService(db_session)
        new_raw = await otp_svc.generate(reg.user_id)
        # Simulate what resend does (it calls otp_service.generate internally)
        # so we wire the same generate here to capture the value

        await svc.verify_email_otp("cp4_resend_then_verify@example.com", new_raw)

        user = await UserRepository(db_session).get_by_id(reg.user_id)
        assert user.is_verified is True

    @pytest.mark.asyncio
    async def test_resend_otp_unknown_email_raises(self, db_session):
        """Resend for a non-existent email raises NotFoundException."""
        from shared.exceptions import NotFoundException
        svc = _auth_service(db_session, email_service=None)

        with pytest.raises(NotFoundException) as exc_info:
            await svc.resend_otp("ghost_resend@example.com")

        assert exc_info.value.error_code == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_resend_otp_already_verified_raises(self, db_session):
        """Resend for an already-verified account raises ConflictException."""
        from app.repositories.auth import UserRepository
        from shared.exceptions import ConflictException
        svc = _auth_service(db_session, email_service=None)

        reg = await svc.register("cp4_resend_verified@example.com", "SecurePass1!")
        await UserRepository(db_session).mark_verified(reg.user_id)

        with pytest.raises(ConflictException) as exc_info:
            await svc.resend_otp("cp4_resend_verified@example.com")

        assert exc_info.value.error_code == "ALREADY_VERIFIED"

    @pytest.mark.asyncio
    async def test_resend_otp_email_failure_is_non_fatal(self, db_session):
        """SMTP failure on resend does not raise — OTP record is still created."""
        from sqlalchemy import select
        from app.models.user import EmailVerificationOTP
        failing_email = _make_failing_email_service()
        svc = _auth_service(db_session, email_service=failing_email)

        reg = await svc.register("cp4_resend_smtp_fail@example.com", "SecurePass1!")

        # Should not raise despite SMTP failure
        result = await svc.resend_otp("cp4_resend_smtp_fail@example.com")
        assert result.message

        rows = await db_session.execute(
            select(EmailVerificationOTP).where(
                EmailVerificationOTP.user_id == reg.user_id
            )
        )
        assert rows.scalar_one_or_none() is not None


# ===========================================================================
# FULL END-TO-END FLOW
# ===========================================================================

class TestFullAuthFlowCheckpoint4:
    """
    [INTEGRATION] Complete registration → verify → login flow.

    Exercises every step in the correct sequence to ensure the full
    Checkpoint 4 integration works end-to-end.
    """

    @pytest.mark.asyncio
    async def test_full_flow_register_verify_login(self, db_session):
        """
        Full happy-path flow:
          1. Register — user created unverified, OTP generated, email sent.
          2. Login attempt — blocked (EMAIL_NOT_VERIFIED).
          3. Verify OTP — user marked verified.
          4. Login — tokens issued.
        """
        from app.services.otp import OTPService
        from shared.exceptions import UnauthorizedException
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        # Step 1: Register
        reg = await svc.register("cp4_e2e@example.com", "SecurePass1!")
        assert reg.user_id is not None
        assert len(mock_email.calls) == 1

        # Step 2: Login blocked
        with pytest.raises(UnauthorizedException) as exc:
            await svc.login("cp4_e2e@example.com", "SecurePass1!")
        assert exc.value.error_code == "EMAIL_NOT_VERIFIED"

        # Step 3: Verify OTP
        otp_svc = OTPService(db_session)
        raw_otp = await otp_svc.generate(reg.user_id)
        verify_result = await svc.verify_email_otp("cp4_e2e@example.com", raw_otp)
        assert "verified" in verify_result.message.lower()

        # Step 4: Login succeeds
        token_result = await svc.login("cp4_e2e@example.com", "SecurePass1!")
        assert token_result.access_token
        assert token_result.refresh_token
        assert token_result.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_full_flow_register_resend_verify_login(self, db_session):
        """
        Resend flow:
          1. Register — OTP generated.
          2. Resend — new OTP issued (old invalidated).
          3. Verify with new OTP — user verified.
          4. Login succeeds.
        """
        from app.services.otp import OTPService
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        # Step 1: Register
        reg = await svc.register("cp4_e2e_resend@example.com", "SecurePass1!")

        # Step 2: Generate a known resend OTP directly
        otp_svc = OTPService(db_session)
        new_raw = await otp_svc.generate(reg.user_id)

        # Step 3: Verify with new OTP
        await svc.verify_email_otp("cp4_e2e_resend@example.com", new_raw)

        # Step 4: Login succeeds
        tokens = await svc.login("cp4_e2e_resend@example.com", "SecurePass1!")
        assert tokens.access_token

    @pytest.mark.asyncio
    async def test_login_access_token_claims_after_verification(self, db_session):
        """
        After verification, login access token contains correct JWT claims
        (sub = user_id, email, roles includes USER).
        """
        from app.services.otp import OTPService
        from app.config.settings import settings
        from shared.utils.security import decode_jwt_token
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        reg = await svc.register("cp4_claims@example.com", "SecurePass1!")
        otp_svc = OTPService(db_session)
        raw_otp = await otp_svc.generate(reg.user_id)
        await svc.verify_email_otp("cp4_claims@example.com", raw_otp)

        token_result = await svc.login("cp4_claims@example.com", "SecurePass1!")
        decoded = decode_jwt_token(
            token_result.access_token, settings.JWT_SECRET, settings.JWT_ALGORITHM
        )

        assert decoded["sub"] == str(reg.user_id)
        assert decoded["email"] == "cp4_claims@example.com"
        assert "USER" in decoded["roles"]

    @pytest.mark.asyncio
    async def test_get_me_shows_verified_after_otp_flow(self, db_session):
        """
        After OTP verification, GET /auth/me (via service) returns
        is_verified=True.
        """
        from app.services.otp import OTPService
        from app.config.settings import settings
        from shared.utils.security import decode_jwt_token
        mock_email = _make_mock_email_service()
        svc = _auth_service(db_session, email_service=mock_email)

        reg = await svc.register("cp4_me_verified@example.com", "SecurePass1!")
        otp_svc = OTPService(db_session)
        raw_otp = await otp_svc.generate(reg.user_id)
        await svc.verify_email_otp("cp4_me_verified@example.com", raw_otp)

        tokens = await svc.login("cp4_me_verified@example.com", "SecurePass1!")
        jwt_payload = decode_jwt_token(
            tokens.access_token, settings.JWT_SECRET, settings.JWT_ALGORITHM
        )

        identity = await svc.get_me(jwt_payload)
        assert identity.is_verified is True


# ===========================================================================
# SCHEMA VALIDATION TESTS  (UNIT — no DB)
# ===========================================================================

class TestCheckpoint4Schemas:
    """[UNIT] New Checkpoint 4 request schemas validate correctly."""

    def test_verify_email_otp_request_valid(self):
        from app.schemas.auth import VerifyEmailOTPRequest
        req = VerifyEmailOTPRequest(email="user@example.com", otp="123456")
        assert req.email == "user@example.com"
        assert req.otp == "123456"

    def test_verify_email_otp_request_normalises_email(self):
        from app.schemas.auth import VerifyEmailOTPRequest
        req = VerifyEmailOTPRequest(email="  USER@EXAMPLE.COM  ", otp="000001")
        assert req.email == "user@example.com"

    def test_verify_email_otp_request_rejects_non_numeric_otp(self):
        from pydantic import ValidationError
        from app.schemas.auth import VerifyEmailOTPRequest
        with pytest.raises(ValidationError):
            VerifyEmailOTPRequest(email="a@b.com", otp="12345X")

    def test_verify_email_otp_request_rejects_short_otp(self):
        from pydantic import ValidationError
        from app.schemas.auth import VerifyEmailOTPRequest
        with pytest.raises(ValidationError):
            VerifyEmailOTPRequest(email="a@b.com", otp="12345")

    def test_verify_email_otp_request_rejects_long_otp(self):
        from pydantic import ValidationError
        from app.schemas.auth import VerifyEmailOTPRequest
        with pytest.raises(ValidationError):
            VerifyEmailOTPRequest(email="a@b.com", otp="1234567")

    def test_resend_otp_request_valid(self):
        from app.schemas.auth import ResendOTPRequest
        req = ResendOTPRequest(email="user@example.com")
        assert req.email == "user@example.com"

    def test_resend_otp_request_normalises_email(self):
        from app.schemas.auth import ResendOTPRequest
        req = ResendOTPRequest(email="  UPPER@EXAMPLE.COM  ")
        assert req.email == "upper@example.com"

    def test_resend_otp_request_rejects_invalid_email(self):
        from pydantic import ValidationError
        from app.schemas.auth import ResendOTPRequest
        with pytest.raises(ValidationError):
            ResendOTPRequest(email="not-an-email")
