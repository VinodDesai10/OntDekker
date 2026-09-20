"""
Authentication Service — Service Layer

Business logic for all authentication flows.

Layer contract:
  - Receives validated data from the API layer (Pydantic-validated).
  - Calls repositories for all persistence.
  - Uses shared exceptions for all error cases.
  - Never constructs HTTP responses (no Request/Response objects here).
  - Never accesses the database directly — only through repositories.
  - Transactions are managed by the FastAPI get_db dependency (commit on
    success, rollback on exception). Repositories use flush() for
    intermediate writes within the same transaction.

Phase 1 scope:
  - register()           — create user + assign USER role + create email
                           verification token + generate OTP + send OTP email
  - login()              — verify credentials, check email verified, issue
                           access + refresh tokens
  - refresh()            — validate refresh token, issue new access token
  - logout()             — revoke a refresh token
  - get_me()             — return current user identity from a validated JWT
  - verify_email()       — opaque-token-based verify-email (GET endpoint)
  - verify_email_otp()   — OTP-based verify-email (POST endpoint, Checkpoint 4)
  - resend_otp()         — invalidate previous OTP, generate new one, send email
  - forgot_password()    — generate password reset token
  - reset_password()     — validate reset token and update password
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.auth import (
    EmailVerificationTokenRepository,
    PasswordResetTokenRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from app.schemas.auth import (
    AccessTokenResponse,
    MessageResponse,
    RegisterResponse,
    TokenResponse,
    UserIdentityResponse,
)
from app.security import (
    access_token_expires_at,
    generate_access_token,
    generate_raw_opaque_token,
    generate_raw_refresh_token,
    refresh_token_expires_at,
    reset_token_expires_at,
    verification_token_expires_at,
)
from app.services.email import EmailDeliveryException, EmailService
from app.services.otp import OTPService
from shared.constants.roles import UserRole
from shared.exceptions import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from shared.utils.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)

# The role automatically assigned to every newly registered user.
DEFAULT_ROLE = UserRole.USER.value


class AuthService:
    """
    Orchestrates all authentication business workflows.

    One instance per request — constructed in the API dependency with the
    current async session.

    Checkpoint 4: OTPService and EmailService are injected at construction
    time so they can be mocked in tests without touching production code.
    """

    def __init__(
        self,
        session: AsyncSession,
        otp_service: Optional[OTPService] = None,
        email_service: Optional[EmailService] = None,
    ) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._roles = RoleRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._verification_tokens = EmailVerificationTokenRepository(session)
        self._reset_tokens = PasswordResetTokenRepository(session)
        self._otp_service = otp_service or OTPService(session)
        self._email_service = email_service  # None = email send skipped

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def register(self, email: str, password: str) -> RegisterResponse:
        """
        Create a new user account and assign the default USER role.

        Checkpoint 4 additions (on top of existing Phase 1 flow):
          6. Generate an OTP for email verification.
          7. Send the OTP via EmailService after the DB transaction completes
             (non-transactional send — user record is always created even if
             SMTP delivery fails, consistent with the existing architecture
             that does not roll back on email failure).

        Full flow:
          1. Hash the password.
          2. Insert the user row (flush).
          3. Look up the USER role (must exist from seed migration).
          4. Assign the USER role to the new user (flush).
          5. Create an email verification token (flush).
          6. Generate and persist an OTP hash (flush).
          7. DB transaction commits (handled by get_db).
          8. Send OTP email asynchronously (fire-and-forget on failure — the
             user can request a resend; we never roll back an already-committed
             user record because email delivery failed).
        """
        # Step 1: hash password first (outside the transaction flush)
        hashed = get_password_hash(password)

        # Step 2: insert user — IntegrityError if email already exists.
        # Before attempting the INSERT, check whether the email is already
        # taken so we can distinguish unverified vs. verified duplicates
        # without relying on a post-rollback query (which is unreliable
        # in savepoint-based test sessions).
        existing_user = await self._users.get_by_email(email)

        if existing_user is not None:
            if not existing_user.is_verified:
                # User registered but never verified — treat this as a resend
                # request.  Generate a fresh OTP (invalidates the old one) and
                # send it, then return the same RegisterResponse shape so the
                # frontend always navigates to the verify-email screen.
                from app.config.settings import settings as _settings
                raw_otp = await self._otp_service.generate(user_id=existing_user.id)

                logger.info(
                    "Re-registration for unverified account — OTP resent",
                    extra={"extra_data": {"user_id": str(existing_user.id), "email": email}},
                )

                if self._email_service is not None:
                    await _send_otp_email_safe(
                        email_service=self._email_service,
                        email=email,
                        otp=raw_otp,
                        expiration_minutes=_settings.OTP_EXPIRE_MINUTES,
                        context="re-registration",
                    )

                return RegisterResponse(
                    message=(
                        "This email is already registered but not yet verified. "
                        "A new verification code has been sent to your inbox."
                    ),
                    user_id=existing_user.id,
                    email=existing_user.email,
                )

            # User is already fully verified — reject with 409.
            raise ConflictException(
                message="An account with this email address already exists.",
                error_code="EMAIL_ALREADY_REGISTERED",
            )

        try:
            user = await self._users.create(email=email, password_hash=hashed)
        except IntegrityError:
            # Extremely unlikely race condition: another request registered
            # the same email between our SELECT above and this INSERT.
            # Roll back and return a generic conflict — the user can log in
            # or retry registration to reach the OTP screen.
            await self._session.rollback()
            raise ConflictException(
                message="An account with this email address already exists.",
                error_code="EMAIL_ALREADY_REGISTERED",
            )

        # Step 3: look up the USER role (seeded by migration a1b2c3d4e5f6)
        user_role = await self._roles.get_by_name(DEFAULT_ROLE)
        if user_role is None:
            logger.error(
                "System role USER not found — run 'alembic upgrade head' to seed roles."
            )
            raise ConflictException(
                message="System configuration error: USER role is missing.",
                error_code="SYSTEM_ROLE_MISSING",
            )

        # Step 4: assign USER role — atomic with user creation
        await self._roles.assign_role(user_id=user.id, role_id=user_role.id)

        # Step 5: generate and persist an email verification token (opaque)
        raw_verification = generate_raw_opaque_token()
        await self._verification_tokens.create(
            user_id=user.id,
            raw_token=raw_verification,
            expires_at=verification_token_expires_at(),
        )

        # Step 6: generate and persist an OTP (hash stored, raw returned)
        from app.config.settings import settings
        raw_otp = await self._otp_service.generate(user_id=user.id)

        logger.info(
            "User registered",
            extra={"extra_data": {"user_id": str(user.id), "email": email}},
        )

        # Step 7: DB transaction commits when the request handler returns.
        # Step 8: Attempt email delivery after the DB flush.
        # Email send is fire-and-forget on failure — a committed user record
        # must never be rolled back because SMTP fails. The user can use
        # POST /auth/resend-otp to get a new code if the first one is lost.
        if self._email_service is not None:
            await _send_otp_email_safe(
                email_service=self._email_service,
                email=email,
                otp=raw_otp,
                expiration_minutes=settings.OTP_EXPIRE_MINUTES,
                context="registration",
            )

        return RegisterResponse(
            message="Registration successful. Please verify your email address.",
            user_id=user.id,
            email=user.email,
        )

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate a user and issue access + refresh tokens.

        Checkpoint 4 addition:
          After credential check but before token issuance, the account's
          email verification status is checked. Unverified users receive a
          specific 401 with error_code=EMAIL_NOT_VERIFIED.

        Returns 401 for all credential failures — never distinguishes
        "email not found" from "wrong password" to avoid user enumeration.
        """
        user = await self._users.get_by_email(email)

        # Unified 401 for unknown email OR wrong password
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedException(
                message="Invalid email or password.",
                error_code="INVALID_CREDENTIALS",
            )

        if not user.is_active:
            raise UnauthorizedException(
                message="This account has been deactivated.",
                error_code="ACCOUNT_INACTIVE",
            )

        # Checkpoint 4: gate on email verification BEFORE issuing tokens
        if not user.is_verified:
            raise UnauthorizedException(
                message=(
                    "Email address not verified. "
                    "Please check your inbox for the verification code or "
                    "use POST /auth/resend-otp to request a new one."
                ),
                error_code="EMAIL_NOT_VERIFIED",
            )

        # Load roles for JWT claims
        role_names = await self._roles.get_roles_for_user(user.id)

        # Generate access token (short-lived JWT)
        access_token = generate_access_token(
            user_id=str(user.id),
            email=user.email,
            roles=role_names,
        )

        # Generate and persist refresh token (opaque, hashed)
        raw_refresh = generate_raw_refresh_token()
        await self._refresh_tokens.create(
            user_id=user.id,
            raw_token=raw_refresh,
            expires_at=refresh_token_expires_at(),
        )

        logger.info(
            "User logged in",
            extra={"extra_data": {"user_id": str(user.id)}},
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            token_type="bearer",
            expires_in=_minutes_to_seconds(),
        )

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    async def refresh(self, raw_refresh_token: str) -> AccessTokenResponse:
        """
        Validate a refresh token and issue a new access token.

        Returns 401 for all invalid token states to avoid leaking information.
        """
        token_record = await self._refresh_tokens.get_by_raw_token(raw_refresh_token)

        if token_record is None:
            raise UnauthorizedException(
                message="Invalid refresh token.",
                error_code="INVALID_REFRESH_TOKEN",
            )

        if token_record.is_revoked:
            raise UnauthorizedException(
                message="Refresh token has been revoked.",
                error_code="REFRESH_TOKEN_REVOKED",
            )

        if token_record.expires_at < datetime.now(timezone.utc):
            raise UnauthorizedException(
                message="Refresh token has expired.",
                error_code="REFRESH_TOKEN_EXPIRED",
            )

        user = await self._users.get_by_id(token_record.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedException(
                message="Account is no longer active.",
                error_code="ACCOUNT_INACTIVE",
            )

        role_names = await self._roles.get_roles_for_user(user.id)

        access_token = generate_access_token(
            user_id=str(user.id),
            email=user.email,
            roles=role_names,
        )

        return AccessTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=_minutes_to_seconds(),
        )

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    async def logout(self, raw_refresh_token: str) -> MessageResponse:
        """
        Revoke a refresh token.

        Idempotent — revoking an already-revoked or non-existent token
        returns success (no information leaked about token validity).
        """
        token_record = await self._refresh_tokens.get_by_raw_token(raw_refresh_token)

        if token_record is not None and not token_record.is_revoked:
            await self._refresh_tokens.revoke(token_record.id)

        logger.info("Refresh token revoked")

        return MessageResponse(message="Logged out successfully.")

    # ------------------------------------------------------------------
    # Me (current identity)
    # ------------------------------------------------------------------

    async def get_me(self, jwt_payload: Dict[str, Any]) -> UserIdentityResponse:
        """
        Return the identity of the currently authenticated user from a
        validated JWT payload.
        """
        user_id_str = jwt_payload.get("sub")
        if not user_id_str:
            raise UnauthorizedException(
                message="Invalid token claims.",
                error_code="INVALID_TOKEN_CLAIMS",
            )

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise UnauthorizedException(
                message="Invalid token subject.",
                error_code="INVALID_TOKEN_SUBJECT",
            )

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundException(
                message="User not found.",
                error_code="USER_NOT_FOUND",
            )

        role_names = await self._roles.get_roles_for_user(user.id)

        return UserIdentityResponse(
            id=user.id,
            email=user.email,
            is_verified=user.is_verified,
            is_active=user.is_active,
            roles=role_names,
            created_at=user.created_at,
        )

    # ------------------------------------------------------------------
    # Verify Email (opaque token — existing GET endpoint)
    # ------------------------------------------------------------------

    async def verify_email(self, raw_token: str) -> MessageResponse:
        """
        Validate an email verification token and mark the user verified.

        This is the existing Phase 1 opaque-token flow for GET /auth/verify-email.
        It is preserved unchanged. The new OTP flow is in verify_email_otp().
        """
        token_record = await self._verification_tokens.get_by_raw_token(raw_token)

        if token_record is None:
            raise UnauthorizedException(
                message="Invalid or expired verification token.",
                error_code="INVALID_VERIFICATION_TOKEN",
            )

        if token_record.is_used:
            raise UnauthorizedException(
                message="This verification token has already been used.",
                error_code="VERIFICATION_TOKEN_ALREADY_USED",
            )

        if token_record.expires_at < datetime.now(timezone.utc):
            raise UnauthorizedException(
                message="Verification token has expired.",
                error_code="VERIFICATION_TOKEN_EXPIRED",
            )

        await self._verification_tokens.mark_used(token_record.id)
        await self._users.mark_verified(token_record.user_id)

        logger.info(
            "Email verified (opaque token)",
            extra={"extra_data": {"user_id": str(token_record.user_id)}},
        )

        return MessageResponse(message="Email verified successfully. Your account is now active.")

    # ------------------------------------------------------------------
    # Verify Email OTP (Checkpoint 4 — POST endpoint)
    # ------------------------------------------------------------------

    async def verify_email_otp(self, email: str, raw_otp: str) -> MessageResponse:
        """
        Verify a 6-digit OTP submitted for email verification.

        Checkpoint 4 — POST /auth/verify-email.

        Flow:
          1. Look up the user by email.
          2. Handle not-found / already-verified edge cases.
          3. Delegate OTP validation to OTPService.verify().
          4. On success: mark the user verified via UserRepository.mark_verified().
          5. Return appropriate response or raise the correct error.

        Error codes returned (mapped from OTPVerificationResult.error_code):
          OTP_NOT_FOUND              → 401 (no active OTP)
          OTP_EXPIRED                → 401
          OTP_INVALID                → 401 (wrong code, attempts remaining)
          OTP_MAX_ATTEMPTS_EXCEEDED  → 401
          USER_NOT_FOUND             → 404
          ALREADY_VERIFIED           → 409 (already verified, no action needed)

        OTPService is responsible for all OTP state mutations. This method
        only calls mark_verified() on success, consistent with the OTPService
        contract: "The caller decides what to do with the result."
        """
        user = await self._users.get_by_email(email)

        if user is None:
            raise NotFoundException(
                message="No account found with this email address.",
                error_code="USER_NOT_FOUND",
            )

        if user.is_verified:
            raise ConflictException(
                message="This email address has already been verified.",
                error_code="ALREADY_VERIFIED",
            )

        # Delegate OTP validation entirely to OTPService
        result = await self._otp_service.verify(
            user_id=user.id,
            raw_otp=raw_otp,
        )

        if not result.success:
            # Map OTPVerificationResult error_code to the appropriate HTTP exception
            _otp_error_to_exception(result.error_code, result.message)

        # OTP matched — mark the user as verified
        await self._users.mark_verified(user.id)

        logger.info(
            "Email verified via OTP",
            extra={"extra_data": {"user_id": str(user.id), "email": email}},
        )

        return MessageResponse(
            message="Email verified successfully. Your account is now active."
        )

    # ------------------------------------------------------------------
    # Resend OTP (Checkpoint 4)
    # ------------------------------------------------------------------

    async def resend_otp(self, email: str) -> MessageResponse:
        """
        Resend a verification OTP to the given email address.

        Checkpoint 4 — POST /auth/resend-otp.

        Flow:
          1. Look up user by email.
          2. Reject if user not found.
          3. Reject if already verified.
          4. Invalidate any previous OTP and generate a new one via OTPService.
             (OTPService.generate() already performs invalidate-then-create
             atomically, so no separate invalidate call is needed.)
          5. Send the OTP email.

        No cooldown — no cooldown mechanism exists anywhere in the codebase,
        and the specification explicitly states not to invent one.
        """
        from app.config.settings import settings

        user = await self._users.get_by_email(email)

        if user is None:
            raise NotFoundException(
                message="No account found with this email address.",
                error_code="USER_NOT_FOUND",
            )

        if user.is_verified:
            raise ConflictException(
                message="This email address has already been verified.",
                error_code="ALREADY_VERIFIED",
            )

        # OTPService.generate() invalidates existing OTPs then creates a new one
        raw_otp = await self._otp_service.generate(user_id=user.id)

        logger.info(
            "OTP resend requested",
            extra={"extra_data": {"user_id": str(user.id), "email": email}},
        )

        # Send the OTP email — fire-and-forget on failure so the
        # OTP record (already committed via flush) is not wasted.
        if self._email_service is not None:
            await _send_otp_email_safe(
                email_service=self._email_service,
                email=email,
                otp=raw_otp,
                expiration_minutes=settings.OTP_EXPIRE_MINUTES,
                context="resend",
            )

        return MessageResponse(
            message="A new verification code has been sent to your email address."
        )

    # ------------------------------------------------------------------
    # Forgot Password
    # ------------------------------------------------------------------

    async def forgot_password(self, email: str) -> MessageResponse:
        """
        Generate a password reset token for the given email address.

        Security: always returns the same success message whether or not
        the email exists in the database, preventing account enumeration.
        """
        user = await self._users.get_by_email(email)

        if user is not None and user.is_active:
            raw_reset = generate_raw_opaque_token()
            await self._reset_tokens.create(
                user_id=user.id,
                raw_token=raw_reset,
                expires_at=reset_token_expires_at(),
            )

        return MessageResponse(
            message="If an account with that email exists, a password reset link has been sent."
        )

    # ------------------------------------------------------------------
    # Reset Password
    # ------------------------------------------------------------------

    async def reset_password(self, raw_token: str, new_password: str) -> MessageResponse:
        """
        Validate a reset token and update the user's password.
        """
        token_record = await self._reset_tokens.get_by_raw_token(raw_token)

        if token_record is None:
            raise UnauthorizedException(
                message="Invalid or expired password reset token.",
                error_code="INVALID_RESET_TOKEN",
            )

        if token_record.is_used:
            raise UnauthorizedException(
                message="This password reset token has already been used.",
                error_code="RESET_TOKEN_ALREADY_USED",
            )

        if token_record.expires_at < datetime.now(timezone.utc):
            raise UnauthorizedException(
                message="Password reset token has expired.",
                error_code="RESET_TOKEN_EXPIRED",
            )

        new_hash = get_password_hash(new_password)
        await self._users.update_password(token_record.user_id, new_hash)
        await self._reset_tokens.mark_used(token_record.id)

        logger.info(
            "Password reset completed",
            extra={"extra_data": {"user_id": str(token_record.user_id)}},
        )

        return MessageResponse(message="Password updated successfully.")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _minutes_to_seconds() -> int:
    """Convert ACCESS_TOKEN_EXPIRE_MINUTES to seconds for the expires_in field."""
    from app.config.settings import settings
    return settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _otp_error_to_exception(error_code: str | None, message: str) -> None:
    """
    Raise the appropriate shared exception for a failed OTPVerificationResult.

    All OTP errors map to UnauthorizedException (401) — they are all forms
    of credential rejection.

    This function always raises; return type is None only to satisfy the
    type checker at the call site.
    """
    raise UnauthorizedException(
        message=message,
        error_code=error_code or "OTP_INVALID",
    )


async def _send_otp_email_safe(
    email_service: "EmailService",
    email: str,
    otp: str,
    expiration_minutes: int,
    context: str,
) -> None:
    """
    Attempt to send an OTP email, suppressing delivery failures.

    The send is fire-and-forget: if SMTP delivery fails, the error is
    logged but not re-raised. The caller's transaction has already been
    committed (or will be committed — the OTP record is already flushed).
    The user can request a resend via POST /auth/resend-otp.

    SMTPEmailService.send_verification_otp() is a blocking synchronous
    call (smtplib). It is run in the default thread-pool executor so it
    does not block the event loop.

    Args:
        email_service:      Concrete EmailService implementation.
        email:              Recipient email address.
        otp:                Raw OTP string (never logged).
        expiration_minutes: TTL shown in the email body.
        context:            Log context label ("registration" or "resend").
    """
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None,
            lambda: email_service.send_verification_otp(
                email=email,
                otp=otp,
                expiration_minutes=expiration_minutes,
                recipient_name=None,
            ),
        )
        logger.info(
            "OTP email dispatched",
            extra={"extra_data": {"context": context, "recipient": email}},
        )
    except EmailDeliveryException as exc:
        # Log and continue — OTP record is already persisted.
        logger.warning(
            "OTP email delivery failed — user can request resend",
            extra={
                "extra_data": {
                    "context": context,
                    "recipient": email,
                    "error_code": exc.error_code,
                    "error": exc.message,
                }
            },
        )
    except Exception as exc:
        logger.warning(
            "Unexpected error during OTP email dispatch",
            extra={
                "extra_data": {
                    "context": context,
                    "recipient": email,
                    "error": str(exc),
                }
            },
        )
