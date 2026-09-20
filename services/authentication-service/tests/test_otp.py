"""
Authentication Service — OTP Unit Test Suite (Checkpoint 2)

Test category: [UNIT] — no database required.

All repository calls are replaced with AsyncMock so these tests run
without a live PostgreSQL instance.

Run with:
  PYTHONPATH=../.. pytest tests/test_otp.py -v

Covers:
  - OTP generation (format, length, numeric, zero-padding)
  - OTP uniqueness / randomness
  - OTP hashing (SHA-256, never plaintext)
  - Successful verification
  - Incorrect OTP (wrong value)
  - Expired OTP
  - Maximum attempt enforcement
  - Replacing previous OTP on re-generation
  - Only hashed value stored (raw OTP never persisted)
  - invalidate() removes all OTP records for the user
"""

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(value: str) -> str:
    """Mirror of the project's _sha256 helper for test assertions."""
    return hashlib.sha256(value.encode()).hexdigest()


def _make_otp_record(
    user_id: uuid.UUID,
    raw_otp: str,
    *,
    attempts: int = 0,
    minutes_until_expiry: int = 10,
) -> MagicMock:
    """
    Build a mock EmailVerificationOTP record for use in test stubs.

    Args:
        user_id: owner of the OTP.
        raw_otp: the plaintext OTP (used to pre-compute otp_hash).
        attempts: current failed attempt count.
        minutes_until_expiry: positive = future (valid), negative = past (expired).
    """
    record = MagicMock()
    record.id = uuid.uuid4()
    record.user_id = user_id
    record.otp_hash = _sha256(raw_otp)
    record.attempts = attempts
    record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes_until_expiry)
    return record


def _make_mock_repo() -> AsyncMock:
    """Return a fully-mocked EmailVerificationOTPRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get_active_for_user = AsyncMock(return_value=None)
    repo.increment_attempts = AsyncMock()
    repo.delete = AsyncMock()
    repo.delete_all_for_user = AsyncMock()
    return repo


async def _make_otp_service(mock_repo: AsyncMock):
    """
    Construct an OTPService with its internal repository replaced by the mock.

    Uses object.__setattr__ to bypass any property descriptors and directly
    inject the mock repository after construction.
    """
    from app.services.otp import OTPService

    session = AsyncMock()
    service = OTPService(session=session)
    # Inject the mock repository directly — avoids constructor side-effects
    service._otp_repo = mock_repo
    return service


# ===========================================================================
# TestOTPGeneration — static helper tests (no DB)
# ===========================================================================

class TestOTPGeneration:
    """[UNIT] OTPService.generate_otp() static method."""

    def test_otp_is_six_digits(self):
        from app.services.otp import OTPService
        otp = OTPService.generate_otp()
        assert len(otp) == 6

    def test_otp_is_all_numeric(self):
        from app.services.otp import OTPService
        otp = OTPService.generate_otp()
        assert otp.isdigit(), f"Expected all-numeric OTP, got {otp!r}"

    def test_otp_zero_padded(self):
        """
        Force secrets.randbelow to return a small integer and confirm
        zero-padding produces exactly 6 characters.
        """
        from app.services.otp import OTPService
        with patch("app.services.otp.secrets.randbelow", return_value=7):
            otp = OTPService.generate_otp()
        assert otp == "000007"
        assert len(otp) == 6

    def test_otp_max_value_is_six_digits(self):
        """999999 should remain 6 digits (no zero-padding needed)."""
        from app.services.otp import OTPService
        with patch("app.services.otp.secrets.randbelow", return_value=999999):
            otp = OTPService.generate_otp()
        assert otp == "999999"

    def test_otp_uses_secrets_module(self):
        """
        Confirm that generate_otp() calls secrets.randbelow, not random.randint.
        This ensures CSPRNG usage rather than the Mersenne Twister.
        """
        from app.services.otp import OTPService
        with patch("app.services.otp.secrets.randbelow") as mock_randbelow:
            mock_randbelow.return_value = 123456
            otp = OTPService.generate_otp()
        mock_randbelow.assert_called_once_with(10 ** 6)
        assert otp == "123456"

    def test_consecutive_otps_are_not_identical(self):
        """
        Generate 20 OTPs; the probability all are equal is (10^-6)^19 ≈ 0.
        A non-trivially-random generator would fail this.
        """
        from app.services.otp import OTPService
        otps = {OTPService.generate_otp() for _ in range(20)}
        assert len(otps) > 1, "All 20 generated OTPs were identical — RNG is broken"


# ===========================================================================
# TestOTPHashing — SHA-256 hashing tests
# ===========================================================================

class TestOTPHashing:
    """[UNIT] OTPService._hash_otp() static method."""

    def test_hash_is_sha256_hexdigest(self):
        from app.services.otp import OTPService
        raw = "483921"
        result = OTPService._hash_otp(raw)
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert result == expected

    def test_hash_length_is_64_chars(self):
        """SHA-256 produces 64 hex characters."""
        from app.services.otp import OTPService
        assert len(OTPService._hash_otp("000000")) == 64

    def test_hash_is_not_plaintext(self):
        from app.services.otp import OTPService
        raw = "123456"
        assert OTPService._hash_otp(raw) != raw

    def test_same_otp_same_hash(self):
        """Hashing is deterministic — same input always produces same output."""
        from app.services.otp import OTPService
        assert OTPService._hash_otp("999999") == OTPService._hash_otp("999999")

    def test_different_otps_different_hashes(self):
        from app.services.otp import OTPService
        assert OTPService._hash_otp("111111") != OTPService._hash_otp("222222")


# ===========================================================================
# TestOTPServiceGenerate — OTPService.generate() async flow tests
# ===========================================================================

class TestOTPServiceGenerate:
    """[UNIT] OTPService.generate() — full generation flow (mocked repo)."""

    @pytest.mark.asyncio
    async def test_generate_returns_six_digit_string(self):
        """generate() must return the raw 6-digit OTP string."""
        repo = _make_mock_repo()
        service = await _make_otp_service(repo)

        raw_otp = await service.generate(uuid.uuid4())

        assert isinstance(raw_otp, str)
        assert len(raw_otp) == 6
        assert raw_otp.isdigit()

    @pytest.mark.asyncio
    async def test_generate_deletes_previous_otp_first(self):
        """
        delete_all_for_user must be called BEFORE create,
        enforcing the one-active-OTP-per-user rule.
        """
        repo = _make_mock_repo()
        call_order = []
        repo.delete_all_for_user.side_effect = lambda uid: call_order.append("delete")
        repo.create.side_effect = lambda **_: call_order.append("create") or MagicMock()

        service = await _make_otp_service(repo)
        user_id = uuid.uuid4()
        await service.generate(user_id)

        assert call_order == ["delete", "create"], (
            f"Expected delete before create, got: {call_order}"
        )

    @pytest.mark.asyncio
    async def test_generate_calls_delete_with_correct_user_id(self):
        repo = _make_mock_repo()
        service = await _make_otp_service(repo)
        user_id = uuid.uuid4()

        await service.generate(user_id)

        repo.delete_all_for_user.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_generate_persists_hash_not_raw_otp(self):
        """
        The value passed to repo.create() as otp_hash must be the SHA-256
        digest of the returned raw OTP — never the raw OTP itself.
        """
        repo = _make_mock_repo()
        service = await _make_otp_service(repo)
        user_id = uuid.uuid4()

        raw_otp = await service.generate(user_id)

        # Extract what was passed to repo.create
        _, kwargs = repo.create.call_args
        stored_hash = kwargs["otp_hash"]

        # Verify it is the hash, not the plaintext
        assert stored_hash != raw_otp, "Raw OTP was stored — must store hash only"
        assert stored_hash == _sha256(raw_otp), "Stored hash does not match SHA-256 of raw OTP"

    @pytest.mark.asyncio
    async def test_generate_passes_correct_user_id_to_create(self):
        repo = _make_mock_repo()
        service = await _make_otp_service(repo)
        user_id = uuid.uuid4()

        await service.generate(user_id)

        _, kwargs = repo.create.call_args
        assert kwargs["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_generate_passes_future_expires_at_to_create(self):
        """expires_at must be in the future (approximately 10 minutes from now)."""
        repo = _make_mock_repo()
        service = await _make_otp_service(repo)

        before = datetime.now(timezone.utc)
        await service.generate(uuid.uuid4())
        after = datetime.now(timezone.utc)

        _, kwargs = repo.create.call_args
        expires_at = kwargs["expires_at"]

        # Must be timezone-aware
        assert expires_at.tzinfo is not None

        # Must be in the future relative to the call
        assert expires_at > before

        # Must be approximately 10 minutes in the future (within 5-second tolerance)
        expected_min = before + timedelta(minutes=9, seconds=55)
        expected_max = after + timedelta(minutes=10, seconds=5)
        assert expected_min <= expires_at <= expected_max, (
            f"expires_at {expires_at} is not ~10 minutes from now"
        )

    @pytest.mark.asyncio
    async def test_generate_replaces_previous_otp_on_second_call(self):
        """
        Calling generate() twice for the same user must delete old records
        both times — not accumulate OTPs.
        """
        repo = _make_mock_repo()
        service = await _make_otp_service(repo)
        user_id = uuid.uuid4()

        await service.generate(user_id)
        await service.generate(user_id)

        # delete_all_for_user must have been called exactly twice
        assert repo.delete_all_for_user.call_count == 2
        # Both calls must target the same user
        for c in repo.delete_all_for_user.call_args_list:
            assert c == call(user_id)


# ===========================================================================
# TestOTPServiceVerify — OTPService.verify() async flow tests
# ===========================================================================

class TestOTPServiceVerifySuccess:
    """[UNIT] OTPService.verify() — successful verification."""

    @pytest.mark.asyncio
    async def test_correct_otp_returns_success_true(self):
        user_id = uuid.uuid4()
        raw_otp = "483921"
        record = _make_otp_record(user_id, raw_otp, attempts=0)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        result = await service.verify(user_id, raw_otp)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_correct_otp_returns_correct_user_id(self):
        user_id = uuid.uuid4()
        raw_otp = "483921"
        record = _make_otp_record(user_id, raw_otp)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        result = await service.verify(user_id, raw_otp)

        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_correct_otp_deletes_record_on_success(self):
        """
        After a successful match, the OTP record must be hard-deleted
        to prevent replay attacks.
        """
        user_id = uuid.uuid4()
        raw_otp = "112233"
        record = _make_otp_record(user_id, raw_otp)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        await service.verify(user_id, raw_otp)

        repo.delete.assert_called_once_with(record.id)

    @pytest.mark.asyncio
    async def test_correct_otp_does_not_increment_attempts(self):
        """Successful verification must NOT increment the attempt counter."""
        user_id = uuid.uuid4()
        raw_otp = "654321"
        record = _make_otp_record(user_id, raw_otp)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        await service.verify(user_id, raw_otp)

        repo.increment_attempts.assert_not_called()

    @pytest.mark.asyncio
    async def test_correct_otp_error_code_is_none(self):
        user_id = uuid.uuid4()
        raw_otp = "000000"
        record = _make_otp_record(user_id, raw_otp)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        result = await service.verify(user_id, raw_otp)

        assert result.error_code is None


class TestOTPServiceVerifyIncorrect:
    """[UNIT] OTPService.verify() — wrong OTP submitted."""

    @pytest.mark.asyncio
    async def test_wrong_otp_returns_success_false(self):
        user_id = uuid.uuid4()
        record = _make_otp_record(user_id, "111111")

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        result = await service.verify(user_id, "999999")

        assert result.success is False

    @pytest.mark.asyncio
    async def test_wrong_otp_returns_otp_invalid_error_code(self):
        user_id = uuid.uuid4()
        record = _make_otp_record(user_id, "111111", attempts=0)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        result = await service.verify(user_id, "999999")

        assert result.error_code == "OTP_INVALID"

    @pytest.mark.asyncio
    async def test_wrong_otp_increments_attempts(self):
        user_id = uuid.uuid4()
        record = _make_otp_record(user_id, "111111", attempts=0)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        await service.verify(user_id, "999999")

        repo.increment_attempts.assert_called_once_with(record.id)

    @pytest.mark.asyncio
    async def test_wrong_otp_does_not_delete_record(self):
        """A non-exhausting failed attempt must NOT delete the OTP record."""
        user_id = uuid.uuid4()
        # attempts=2 — well below the limit; this failure will not exhaust it
        record = _make_otp_record(user_id, "111111", attempts=2)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        await service.verify(user_id, "999999")

        repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_hash_comparison_uses_hmac_compare_digest(self):
        """
        Verify that OTP hash comparison goes through hmac.compare_digest()
        rather than a plain == or != operator, preventing timing attacks.
        """
        user_id = uuid.uuid4()
        raw_otp = "123456"
        record = _make_otp_record(user_id, raw_otp, attempts=0)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        with patch("app.services.otp.hmac.compare_digest", wraps=hmac.compare_digest) as mock_cd:
            await service.verify(user_id, raw_otp)

        mock_cd.assert_called_once()


class TestOTPServiceVerifyExpired:
    """[UNIT] OTPService.verify() — expired OTP."""

    @pytest.mark.asyncio
    async def test_expired_otp_returns_success_false(self):
        user_id = uuid.uuid4()
        record = _make_otp_record(user_id, "123456", minutes_until_expiry=-1)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        result = await service.verify(user_id, "123456")

        assert result.success is False

    @pytest.mark.asyncio
    async def test_expired_otp_returns_otp_expired_error_code(self):
        user_id = uuid.uuid4()
        record = _make_otp_record(user_id, "123456", minutes_until_expiry=-5)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        result = await service.verify(user_id, "123456")

        assert result.error_code == "OTP_EXPIRED"

    @pytest.mark.asyncio
    async def test_expired_otp_deletes_stale_record(self):
        """
        An expired OTP record must be hard-deleted so it cannot block
        future OTP generation for the user.
        """
        user_id = uuid.uuid4()
        record = _make_otp_record(user_id, "123456", minutes_until_expiry=-1)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        await service.verify(user_id, "123456")

        repo.delete.assert_called_once_with(record.id)

    @pytest.mark.asyncio
    async def test_expired_otp_does_not_increment_attempts(self):
        """Expiry check happens before attempt counting."""
        user_id = uuid.uuid4()
        record = _make_otp_record(user_id, "123456", minutes_until_expiry=-1)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        await service.verify(user_id, "123456")

        repo.increment_attempts.assert_not_called()

    @pytest.mark.asyncio
    async def test_just_expired_otp_is_rejected(self):
        """An OTP that expired 1 second ago must be rejected."""
        user_id = uuid.uuid4()
        record = _make_otp_record(user_id, "999999")
        # Override expires_at to exactly 1 second in the past
        record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        result = await service.verify(user_id, "999999")

        assert result.success is False
        assert result.error_code == "OTP_EXPIRED"


class TestOTPServiceVerifyMaxAttempts:
    """[UNIT] OTPService.verify() — attempt limit enforcement."""

    @pytest.mark.asyncio
    async def test_fifth_wrong_attempt_returns_max_attempts_exceeded(self):
        """
        The 5th wrong attempt brings the total to OTP_MAX_ATTEMPTS (5).
        The result should reflect exhaustion.
        """
        user_id = uuid.uuid4()
        # attempts=4 — one away from the limit
        record = _make_otp_record(user_id, "111111", attempts=4)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        result = await service.verify(user_id, "999999")

        assert result.success is False
        assert result.error_code == "OTP_MAX_ATTEMPTS_EXCEEDED"

    @pytest.mark.asyncio
    async def test_fifth_wrong_attempt_deletes_record(self):
        """
        When the final permitted attempt is consumed, the OTP record must be
        hard-deleted so it does not linger unnecessarily in the database.
        After deletion, a subsequent verify() will return OTP_NOT_FOUND.
        """
        user_id = uuid.uuid4()
        # attempts=4 — one wrong attempt will reach the limit (5)
        record = _make_otp_record(user_id, "111111", attempts=4)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        await service.verify(user_id, "999999")

        # Record must be deleted after the exhausting attempt
        repo.delete.assert_called_once_with(record.id)

    @pytest.mark.asyncio
    async def test_already_exhausted_otp_returns_max_attempts_exceeded(self):
        """
        An OTP record where attempts >= OTP_MAX_ATTEMPTS should be
        rejected immediately without attempting to match or incrementing.
        """
        user_id = uuid.uuid4()
        record = _make_otp_record(user_id, "111111", attempts=5)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        result = await service.verify(user_id, "111111")

        assert result.success is False
        assert result.error_code == "OTP_MAX_ATTEMPTS_EXCEEDED"

    @pytest.mark.asyncio
    async def test_exhausted_otp_does_not_increment_attempts(self):
        """
        Once the limit is reached, no further DB writes should occur
        for the attempt counter.
        """
        user_id = uuid.uuid4()
        record = _make_otp_record(user_id, "111111", attempts=5)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        await service.verify(user_id, "111111")

        repo.increment_attempts.assert_not_called()

    @pytest.mark.asyncio
    async def test_fourth_wrong_attempt_still_returns_otp_invalid(self):
        """
        Before the limit, a wrong OTP returns OTP_INVALID not
        OTP_MAX_ATTEMPTS_EXCEEDED.
        """
        user_id = uuid.uuid4()
        record = _make_otp_record(user_id, "111111", attempts=3)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        result = await service.verify(user_id, "999999")

        assert result.success is False
        assert result.error_code == "OTP_INVALID"

    @pytest.mark.asyncio
    async def test_max_attempts_check_happens_before_hash_comparison(self):
        """
        Even the correct OTP must be rejected when attempts >= max,
        because the record is treated as exhausted regardless of the value.
        """
        user_id = uuid.uuid4()
        raw_otp = "555555"
        # attempts already at the limit
        record = _make_otp_record(user_id, raw_otp, attempts=5)

        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = record
        service = await _make_otp_service(repo)

        # Submit the correct OTP, but attempts are exhausted
        result = await service.verify(user_id, raw_otp)

        assert result.success is False
        assert result.error_code == "OTP_MAX_ATTEMPTS_EXCEEDED"
        repo.delete.assert_not_called()


class TestOTPServiceVerifyNoRecord:
    """[UNIT] OTPService.verify() — no active OTP for the user."""

    @pytest.mark.asyncio
    async def test_no_active_otp_returns_success_false(self):
        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = None
        service = await _make_otp_service(repo)

        result = await service.verify(uuid.uuid4(), "123456")

        assert result.success is False

    @pytest.mark.asyncio
    async def test_no_active_otp_returns_otp_not_found_code(self):
        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = None
        service = await _make_otp_service(repo)

        result = await service.verify(uuid.uuid4(), "123456")

        assert result.error_code == "OTP_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_no_active_otp_does_not_call_delete_or_increment(self):
        repo = _make_mock_repo()
        repo.get_active_for_user.return_value = None
        service = await _make_otp_service(repo)

        await service.verify(uuid.uuid4(), "123456")

        repo.delete.assert_not_called()
        repo.increment_attempts.assert_not_called()


# ===========================================================================
# TestOTPServiceInvalidate — OTPService.invalidate()
# ===========================================================================

class TestOTPServiceInvalidate:
    """[UNIT] OTPService.invalidate() — explicit OTP invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_calls_delete_all_for_user(self):
        repo = _make_mock_repo()
        service = await _make_otp_service(repo)
        user_id = uuid.uuid4()

        await service.invalidate(user_id)

        repo.delete_all_for_user.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_invalidate_does_not_raise_when_no_otp_exists(self):
        """invalidate() must be safe to call even if no record exists."""
        repo = _make_mock_repo()
        repo.delete_all_for_user.return_value = None
        service = await _make_otp_service(repo)

        # Should not raise
        await service.invalidate(uuid.uuid4())


# ===========================================================================
# TestOTPHashStorageSafety — raw OTP must never be stored
# ===========================================================================

class TestOTPHashStorageSafety:
    """[UNIT] Assert the raw OTP is never passed to any repository method."""

    @pytest.mark.asyncio
    async def test_raw_otp_not_in_create_call_args(self):
        """
        Inspect every argument passed to repo.create() and confirm none
        of them equal the raw OTP that was generated and returned.
        """
        repo = _make_mock_repo()
        service = await _make_otp_service(repo)
        user_id = uuid.uuid4()

        raw_otp = await service.generate(user_id)

        # Flatten all positional and keyword args passed to repo.create
        _, kwargs = repo.create.call_args
        all_stored_values = list(kwargs.values())

        assert raw_otp not in all_stored_values, (
            f"Raw OTP {raw_otp!r} was found in repo.create() call args — "
            "plaintext OTP must never be persisted."
        )

    @pytest.mark.asyncio
    async def test_stored_hash_is_sha256_of_returned_otp(self):
        """
        Verify the stored otp_hash is precisely SHA-256(raw_otp),
        confirming the correct hashing algorithm is applied.
        """
        repo = _make_mock_repo()
        service = await _make_otp_service(repo)

        raw_otp = await service.generate(uuid.uuid4())

        _, kwargs = repo.create.call_args
        assert kwargs["otp_hash"] == _sha256(raw_otp)
