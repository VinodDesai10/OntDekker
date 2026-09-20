"""
Authentication Service — OTP Service (Checkpoint 2, rev 1)

Implements all domain logic for OTP-based email verification.

Responsibilities:
  - generate_otp()    : Produce a cryptographically secure 6-digit OTP.
  - _hash_otp()       : Hash the raw OTP with SHA-256 before persistence.
  - generate()        : Full generation flow: invalidate old → persist new.
  - verify()          : Full verification flow: look up → check expiry/attempts
                        → constant-time hash compare → increment failures or
                        delete on success/exhaustion.

Layer contract (mirrors AuthService conventions):
  - One instance per request, constructed with the current async session.
  - All persistence goes through EmailVerificationOTPRepository only.
  - No email delivery — that belongs to a later checkpoint.
  - No User.is_verified mutation — that belongs to the endpoint integration
    checkpoint. verify() confirms the OTP is correct and returns a structured
    result; the caller decides what to do with it.
  - Uses shared exceptions for all error cases.
  - Uses logging with extra_data for structured log context.

OTP specification:
  - 6-digit zero-padded numeric string (e.g. "083921").
  - Generated with secrets.randbelow(1_000_000) — cryptographically secure CSPRNG.
  - Hashed with SHA-256 before storage; raw value never persisted.
  - Lifetime: settings.OTP_EXPIRE_MINUTES (default: 10 minutes).
  - Max failed attempts: settings.OTP_MAX_ATTEMPTS (default: 5).
    After the attempt that reaches the limit, the record is hard-deleted and
    OTP_MAX_ATTEMPTS_EXCEEDED is returned. Subsequent verify() calls return
    OTP_NOT_FOUND because the record no longer exists.
  - Hash comparison uses hmac.compare_digest() for constant-time equality,
    preventing timing side-channel attacks.
  - One active OTP per user: all previous records are hard-deleted on each
    generate() call.

Verification result:
  OTPVerificationResult is a dataclass (not a Pydantic model — it is an
  internal service result, never serialised to JSON directly). The API layer
  translates it into a response schema when this service is integrated in a
  later checkpoint.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.repositories.auth import EmailVerificationOTPRepository

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants  (sourced from settings so they are env-overridable)
# ---------------------------------------------------------------------------

# Length of the numeric OTP (always 6 digits, zero-padded).
OTP_DIGITS: int = 6


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OTPVerificationResult:
    """
    Structured result returned by OTPService.verify().

    Fields:
      success    — True when the submitted OTP matched and was not expired/exhausted.
      user_id    — The UUID of the user the OTP belongs to (always present).
      message    — Human-readable description of the outcome.
      error_code — Machine-readable code for the API layer (None on success).

    This is an internal domain object. The API layer in a later checkpoint
    will map it to an appropriate HTTP response schema.
    """

    success: bool
    user_id: uuid.UUID
    message: str
    error_code: str | None = None


# ---------------------------------------------------------------------------
# OTPService
# ---------------------------------------------------------------------------

class OTPService:
    """
    Orchestrates OTP generation and verification for email verification.

    One instance per request — constructed with the current async session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._otp_repo = EmailVerificationOTPRepository(session)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def generate_otp() -> str:
        """
        Generate a cryptographically secure 6-digit numeric OTP.

        Uses secrets.randbelow(1_000_000) which draws from the OS CSPRNG.
        The result is zero-padded to always produce exactly 6 digits
        (e.g. 83921 → "083921").

        Returns:
            str: 6-character zero-padded digit string, e.g. "083921".
        """
        raw_int = secrets.randbelow(10 ** OTP_DIGITS)  # 0 ≤ n < 1_000_000
        return str(raw_int).zfill(OTP_DIGITS)

    @staticmethod
    def _hash_otp(raw_otp: str) -> str:
        """
        Compute the SHA-256 hex digest of the raw OTP string.

        Consistent with the project-wide _sha256() helper used by all
        other repositories — token value stored as hexdigest (64 chars).

        Args:
            raw_otp: The plaintext 6-digit OTP string.

        Returns:
            str: 64-character lowercase hex SHA-256 digest.
        """
        return hashlib.sha256(raw_otp.encode()).hexdigest()

    @staticmethod
    def _otp_expires_at() -> datetime:
        """Return the UTC datetime when a freshly generated OTP expires."""
        return datetime.now(timezone.utc) + timedelta(
            minutes=settings.OTP_EXPIRE_MINUTES
        )

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def generate(self, user_id: uuid.UUID) -> str:
        """
        Generate a new OTP for the given user and persist its hash.

        Flow:
          1. Delete all existing OTP records for the user (enforces the
             one-active-OTP-per-user rule and invalidates any previous codes).
          2. Generate a cryptographically secure 6-digit OTP.
          3. Hash the OTP with SHA-256.
          4. Persist the hash with an expiry timestamp (flush — caller's
             transaction commits on HTTP success).
          5. Return the raw OTP to the caller for delivery (email, etc.).

        The raw OTP is returned in memory and never persisted. The caller
        (API layer, email service) is responsible for delivering it securely.
        The raw value must not be logged.

        Args:
            user_id: UUID of the user to generate an OTP for.

        Returns:
            str: The raw 6-digit OTP string (e.g. "083921"). NOT hashed.
        """
        # Step 1: invalidate any previous active OTP for this user
        await self._otp_repo.delete_all_for_user(user_id)

        # Step 2: generate raw OTP in memory
        raw_otp = self.generate_otp()

        # Step 3: hash before persistence — raw value must never be stored
        otp_hash = self._hash_otp(raw_otp)

        # Step 4: persist the hashed record
        await self._otp_repo.create(
            user_id=user_id,
            otp_hash=otp_hash,
            expires_at=self._otp_expires_at(),
        )

        logger.info(
            "OTP generated",
            extra={"extra_data": {"user_id": str(user_id)}},
        )

        # Step 5: return the raw OTP — caller delivers it; we discard it
        return raw_otp

    async def verify(
        self,
        user_id: uuid.UUID,
        raw_otp: str,
    ) -> OTPVerificationResult:
        """
        Verify a submitted OTP against the persisted hash for the user.

        Verification flow:
          1. Look up the active OTP record for the user.
          2. If no record exists → return OTP_NOT_FOUND.
          3. Check expiration → delete stale record and return OTP_EXPIRED.
          4. Check whether max attempts already reached → return
             OTP_MAX_ATTEMPTS_EXCEEDED (record was already deleted on the
             attempt that exhausted the limit).
          5. Compare hashes using hmac.compare_digest() for constant-time
             equality (prevents timing side-channel attacks).
          6a. On mismatch:
              - Increment the attempt counter.
              - If this increment reaches the limit: hard-delete the record
                and return OTP_MAX_ATTEMPTS_EXCEEDED.
              - Otherwise return OTP_INVALID with remaining attempts.
          6b. On match:
              - Hard-delete the OTP record (prevents replay attacks).
              - Return success.

        The caller is responsible for acting on the result (e.g., marking
        the user as verified, returning an HTTP response). This service
        does NOT mutate User.is_verified.

        Args:
            user_id: UUID of the user submitting the OTP.
            raw_otp: The plaintext OTP string submitted by the user.

        Returns:
            OTPVerificationResult with success=True on valid match,
            or success=False with a descriptive error_code on any failure.
        """
        otp_max_attempts = settings.OTP_MAX_ATTEMPTS

        # Step 1: look up the active OTP record
        otp_record = await self._otp_repo.get_active_for_user(user_id)

        # Step 2: no record — never generated, already consumed, or deleted
        # after exhausting attempts
        if otp_record is None:
            logger.info(
                "OTP verification failed: no active OTP",
                extra={"extra_data": {"user_id": str(user_id)}},
            )
            return OTPVerificationResult(
                success=False,
                user_id=user_id,
                message="No active OTP found. Please request a new code.",
                error_code="OTP_NOT_FOUND",
            )

        # Step 3: check expiration — delete stale record before returning
        now = datetime.now(timezone.utc)
        if otp_record.expires_at < now:
            await self._otp_repo.delete(otp_record.id)
            logger.info(
                "OTP verification failed: OTP expired",
                extra={"extra_data": {"user_id": str(user_id)}},
            )
            return OTPVerificationResult(
                success=False,
                user_id=user_id,
                message="OTP has expired. Please request a new code.",
                error_code="OTP_EXPIRED",
            )

        # Step 4: guard against an already-exhausted record (should not
        # normally exist because step 6a deletes on exhaustion, but
        # defended against for safety)
        if otp_record.attempts >= otp_max_attempts:
            logger.info(
                "OTP verification failed: max attempts exceeded",
                extra={"extra_data": {"user_id": str(user_id), "attempts": otp_record.attempts}},
            )
            return OTPVerificationResult(
                success=False,
                user_id=user_id,
                message="Maximum verification attempts exceeded. Please request a new code.",
                error_code="OTP_MAX_ATTEMPTS_EXCEEDED",
            )

        # Step 5: constant-time hash comparison — prevents timing attacks.
        # Both operands are hex strings of equal length (64 chars) so
        # hmac.compare_digest() is an appropriate fit.
        submitted_hash = self._hash_otp(raw_otp)
        hashes_match = hmac.compare_digest(submitted_hash, otp_record.otp_hash)

        if not hashes_match:
            # Step 6a: wrong OTP — increment attempt counter first
            await self._otp_repo.increment_attempts(otp_record.id)
            new_attempts = otp_record.attempts + 1

            if new_attempts >= otp_max_attempts:
                # This was the last permitted attempt — hard-delete the record
                # so it cannot linger in the database unnecessarily.
                await self._otp_repo.delete(otp_record.id)
                logger.info(
                    "OTP verification failed: incorrect OTP, attempts exhausted — record deleted",
                    extra={"extra_data": {"user_id": str(user_id), "attempts": new_attempts}},
                )
                return OTPVerificationResult(
                    success=False,
                    user_id=user_id,
                    message="Incorrect OTP. Maximum attempts reached. Please request a new code.",
                    error_code="OTP_MAX_ATTEMPTS_EXCEEDED",
                )

            logger.info(
                "OTP verification failed: incorrect OTP",
                extra={
                    "extra_data": {
                        "user_id": str(user_id),
                        "attempts": new_attempts,
                        "remaining": otp_max_attempts - new_attempts,
                    }
                },
            )
            return OTPVerificationResult(
                success=False,
                user_id=user_id,
                message="Incorrect OTP. Please try again.",
                error_code="OTP_INVALID",
            )

        # Step 6b: correct OTP — delete the record to prevent replay
        await self._otp_repo.delete(otp_record.id)

        logger.info(
            "OTP verified successfully",
            extra={"extra_data": {"user_id": str(user_id)}},
        )

        return OTPVerificationResult(
            success=True,
            user_id=user_id,
            message="OTP verified successfully.",
            error_code=None,
        )

    async def invalidate(self, user_id: uuid.UUID) -> None:
        """
        Explicitly invalidate (hard-delete) all OTP records for a user.

        Useful when account state changes make any outstanding OTP irrelevant
        (e.g., password reset, account deactivation, forced re-verification).

        Args:
            user_id: UUID of the user whose OTP records should be deleted.
        """
        await self._otp_repo.delete_all_for_user(user_id)
        logger.info(
            "OTP invalidated",
            extra={"extra_data": {"user_id": str(user_id)}},
        )
