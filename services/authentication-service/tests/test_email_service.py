"""
Authentication Service — Email Service Unit Test Suite (Checkpoint 3)

Test category: [UNIT] — no live SMTP server required.

All smtplib.SMTP calls are replaced with MagicMock/patch so these tests
run fully offline without any external dependencies.

Run with:
  PYTHONPATH=../.. pytest tests/test_email_service.py -v

Covers:
  ── Template tests ──────────────────────────────────────────────────────────
  TestOTPPlainTemplate
    - Contains OTP in output
    - Contains expiration minutes
    - Uses personalised greeting when recipient_name is given
    - Falls back to generic greeting when recipient_name is omitted
    - Includes security notice ("do not share" / "safely ignore")
    - OntDekker branding present

  TestOTPHTMLTemplate
    - Contains OTP in HTML output
    - Contains expiration minutes
    - Uses personalised greeting when recipient_name is given
    - Falls back to generic greeting when recipient_name is omitted
    - Includes OntDekker branding
    - Includes security notice in footer
    - Is a valid (well-formed) HTML skeleton

  ── SMTPEmailService tests ───────────────────────────────────────────────────
  TestSMTPEmailServiceSuccess
    - Sends successfully without recipient_name
    - Sends successfully with recipient_name
    - SMTP connection is opened to configured host + port
    - STARTTLS is invoked when SMTP_USE_TLS is True
    - STARTTLS is NOT invoked when SMTP_USE_TLS is False
    - login() is called with SMTP_USERNAME and SMTP_PASSWORD
    - sendmail() is called with correct from_addr and to_addrs
    - quit() is called after successful send (connection cleanup)

  TestSMTPEmailServiceFailures
    - SMTPAuthenticationError → raises EmailDeliveryException (EMAIL_AUTH_FAILED)
    - SMTPConnectError        → raises EmailDeliveryException (EMAIL_CONNECTION_FAILED)
    - Generic SMTPException   → raises EmailDeliveryException (EMAIL_DELIVERY_FAILED)
    - Unexpected Exception    → raises EmailDeliveryException (EMAIL_DELIVERY_FAILED)
    - quit() is still called when send raises (connection cleanup on error)
    - quit() failure is silently suppressed (does not mask original error)

  ── EmailDeliveryException tests ────────────────────────────────────────────
  TestEmailDeliveryException
    - Default message and error_code
    - Custom message and error_code
    - Is an Exception subclass

  ── EmailService interface tests ────────────────────────────────────────────
  TestEmailServiceInterface
    - SMTPEmailService is a subclass of EmailService
    - Concrete implementation satisfies the abstract contract
    - get_email_service() dependency returns an SMTPEmailService
"""

import smtplib
from unittest.mock import MagicMock, patch, call

import pytest

# Pre-import the module under test at collection time.
# This ensures app.services.email is in sys.modules before any patch() call
# tries to resolve "app.services.email.*" — the patch machinery would otherwise
# attempt to import "app.services" (the package), which triggers __init__.py and
# the full dependency chain.  By importing the leaf module directly here, the
# subsequent patch() calls use the already-cached module object.
import app.services.email as _email_module  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_smtp_email_service():
    """Instantiate SMTPEmailService without triggering any SMTP connection."""
    from app.services.email import SMTPEmailService  # noqa: PLC0415
    return SMTPEmailService()


# ===========================================================================
# TestOTPPlainTemplate
# ===========================================================================

class TestOTPPlainTemplate:
    """[UNIT] render_otp_plain() template rendering."""

    def test_contains_otp(self):
        from app.templates.email import render_otp_plain
        result = render_otp_plain(otp="483921", expiration_minutes=10)
        assert "483921" in result

    def test_contains_expiration_minutes(self):
        from app.templates.email import render_otp_plain
        result = render_otp_plain(otp="000001", expiration_minutes=15)
        assert "15" in result

    def test_personalised_greeting_with_name(self):
        from app.templates.email import render_otp_plain
        result = render_otp_plain(otp="111111", expiration_minutes=10, recipient_name="Alice")
        assert "Alice" in result
        assert "Hello, Alice!" in result

    def test_generic_greeting_without_name(self):
        from app.templates.email import render_otp_plain
        result = render_otp_plain(otp="111111", expiration_minutes=10)
        assert "Hello," in result
        # Should not contain a comma after 'Hello' followed by a name
        assert "Hello, None" not in result

    def test_security_notice_do_not_share(self):
        from app.templates.email import render_otp_plain
        result = render_otp_plain(otp="222222", expiration_minutes=10)
        assert "not share" in result.lower() or "never" in result.lower()

    def test_security_notice_safely_ignore(self):
        from app.templates.email import render_otp_plain
        result = render_otp_plain(otp="333333", expiration_minutes=10)
        assert "safely ignore" in result.lower()

    def test_ontdekker_branding(self):
        from app.templates.email import render_otp_plain
        result = render_otp_plain(otp="444444", expiration_minutes=10)
        assert "OntDekker" in result

    def test_returns_string(self):
        from app.templates.email import render_otp_plain
        result = render_otp_plain(otp="555555", expiration_minutes=10)
        assert isinstance(result, str)
        assert len(result) > 0


# ===========================================================================
# TestOTPHTMLTemplate
# ===========================================================================

class TestOTPHTMLTemplate:
    """[UNIT] render_otp_html() template rendering."""

    def test_contains_otp(self):
        from app.templates.email import render_otp_html
        result = render_otp_html(otp="483921", expiration_minutes=10)
        assert "483921" in result

    def test_contains_expiration_minutes(self):
        from app.templates.email import render_otp_html
        result = render_otp_html(otp="000001", expiration_minutes=15)
        assert "15" in result

    def test_personalised_greeting_with_name(self):
        from app.templates.email import render_otp_html
        result = render_otp_html(otp="111111", expiration_minutes=10, recipient_name="Bob")
        assert "Bob" in result
        assert "Hello, Bob!" in result

    def test_generic_greeting_without_name(self):
        from app.templates.email import render_otp_html
        result = render_otp_html(otp="111111", expiration_minutes=10)
        assert "Hello," in result
        assert "Hello, None" not in result

    def test_ontdekker_branding(self):
        from app.templates.email import render_otp_html
        result = render_otp_html(otp="666666", expiration_minutes=10)
        assert "OntDekker" in result

    def test_security_notice_in_footer(self):
        from app.templates.email import render_otp_html
        result = render_otp_html(otp="777777", expiration_minutes=10)
        assert "safely ignore" in result.lower()

    def test_is_html(self):
        from app.templates.email import render_otp_html
        result = render_otp_html(otp="888888", expiration_minutes=10)
        assert "<!DOCTYPE html>" in result or "<html" in result
        assert "</html>" in result

    def test_contains_body_tags(self):
        from app.templates.email import render_otp_html
        result = render_otp_html(otp="999999", expiration_minutes=10)
        assert "<body" in result
        assert "</body>" in result

    def test_returns_string(self):
        from app.templates.email import render_otp_html
        result = render_otp_html(otp="000000", expiration_minutes=10)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_different_otps_produce_different_output(self):
        from app.templates.email import render_otp_html
        result_a = render_otp_html(otp="111111", expiration_minutes=10)
        result_b = render_otp_html(otp="999999", expiration_minutes=10)
        assert result_a != result_b


# ===========================================================================
# TestSMTPEmailServiceSuccess
# ===========================================================================

class TestSMTPEmailServiceSuccess:
    """[UNIT] SMTPEmailService — successful send scenarios."""

    def _make_mock_smtp(self):
        """Return a fully-mocked smtplib.SMTP instance."""
        mock = MagicMock()
        mock.starttls = MagicMock()
        mock.login = MagicMock()
        mock.sendmail = MagicMock()
        mock.quit = MagicMock()
        return mock

    def test_send_without_recipient_name(self):
        """Sending with no recipient_name completes without error."""
        service = _make_smtp_email_service()
        mock_smtp = self._make_mock_smtp()

        with patch("app.services.email.smtplib.SMTP", return_value=mock_smtp):
            # Should not raise
            service.send_verification_otp(
                email="user@example.com",
                otp="123456",
                expiration_minutes=10,
            )

        mock_smtp.sendmail.assert_called_once()

    def test_send_with_recipient_name(self):
        """Sending with a recipient_name completes without error."""
        service = _make_smtp_email_service()
        mock_smtp = self._make_mock_smtp()

        with patch("app.services.email.smtplib.SMTP", return_value=mock_smtp):
            service.send_verification_otp(
                email="alice@example.com",
                otp="654321",
                expiration_minutes=10,
                recipient_name="Alice",
            )

        mock_smtp.sendmail.assert_called_once()

    def test_smtp_connects_to_configured_host_and_port(self):
        """SMTP() is called with SMTP_HOST and SMTP_PORT from settings."""
        service = _make_smtp_email_service()
        mock_smtp = self._make_mock_smtp()

        with patch("app.services.email.smtplib.SMTP", return_value=mock_smtp) as mock_smtp_cls, \
             patch("app.services.email.settings") as mock_settings:
            mock_settings.SMTP_HOST = "smtp.test.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "user"
            mock_settings.SMTP_PASSWORD = "pass"
            mock_settings.SMTP_FROM_EMAIL = "noreply@ontdekker.com"
            mock_settings.SMTP_FROM_NAME = "OntDekker"
            mock_settings.SMTP_USE_TLS = True

            service.send_verification_otp(
                email="test@example.com",
                otp="000000",
                expiration_minutes=10,
            )

        mock_smtp_cls.assert_called_once_with("smtp.test.com", 587)

    def test_starttls_called_when_use_tls_is_true(self):
        """starttls() is invoked when SMTP_USE_TLS = True."""
        service = _make_smtp_email_service()
        mock_smtp = self._make_mock_smtp()

        with patch("app.services.email.smtplib.SMTP", return_value=mock_smtp), \
             patch("app.services.email.settings") as mock_settings:
            mock_settings.SMTP_HOST = "smtp.test.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "user"
            mock_settings.SMTP_PASSWORD = "pass"
            mock_settings.SMTP_FROM_EMAIL = "noreply@ontdekker.com"
            mock_settings.SMTP_FROM_NAME = "OntDekker"
            mock_settings.SMTP_USE_TLS = True

            service.send_verification_otp(
                email="test@example.com",
                otp="111111",
                expiration_minutes=10,
            )

        mock_smtp.starttls.assert_called_once()

    def test_starttls_not_called_when_use_tls_is_false(self):
        """starttls() is NOT invoked when SMTP_USE_TLS = False."""
        service = _make_smtp_email_service()
        mock_smtp = self._make_mock_smtp()

        with patch("app.services.email.smtplib.SMTP", return_value=mock_smtp), \
             patch("app.services.email.settings") as mock_settings:
            mock_settings.SMTP_HOST = "smtp.test.com"
            mock_settings.SMTP_PORT = 25
            mock_settings.SMTP_USERNAME = "user"
            mock_settings.SMTP_PASSWORD = "pass"
            mock_settings.SMTP_FROM_EMAIL = "noreply@ontdekker.com"
            mock_settings.SMTP_FROM_NAME = "OntDekker"
            mock_settings.SMTP_USE_TLS = False

            service.send_verification_otp(
                email="test@example.com",
                otp="222222",
                expiration_minutes=10,
            )

        mock_smtp.starttls.assert_not_called()

    def test_login_called_with_credentials(self):
        """login() is called with SMTP_USERNAME and SMTP_PASSWORD."""
        service = _make_smtp_email_service()
        mock_smtp = self._make_mock_smtp()

        with patch("app.services.email.smtplib.SMTP", return_value=mock_smtp), \
             patch("app.services.email.settings") as mock_settings:
            mock_settings.SMTP_HOST = "smtp.test.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "smtp_user"
            mock_settings.SMTP_PASSWORD = "smtp_pass"
            mock_settings.SMTP_FROM_EMAIL = "noreply@ontdekker.com"
            mock_settings.SMTP_FROM_NAME = "OntDekker"
            mock_settings.SMTP_USE_TLS = True

            service.send_verification_otp(
                email="test@example.com",
                otp="333333",
                expiration_minutes=10,
            )

        mock_smtp.login.assert_called_once_with("smtp_user", "smtp_pass")

    def test_sendmail_called_with_correct_addresses(self):
        """sendmail() is called with SMTP_FROM_EMAIL and the recipient address."""
        service = _make_smtp_email_service()
        mock_smtp = self._make_mock_smtp()

        with patch("app.services.email.smtplib.SMTP", return_value=mock_smtp), \
             patch("app.services.email.settings") as mock_settings:
            mock_settings.SMTP_HOST = "smtp.test.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "user"
            mock_settings.SMTP_PASSWORD = "pass"
            mock_settings.SMTP_FROM_EMAIL = "noreply@ontdekker.com"
            mock_settings.SMTP_FROM_NAME = "OntDekker"
            mock_settings.SMTP_USE_TLS = True

            service.send_verification_otp(
                email="recipient@example.com",
                otp="444444",
                expiration_minutes=10,
            )

        call_kwargs = mock_smtp.sendmail.call_args
        assert call_kwargs.kwargs.get("from_addr") == "noreply@ontdekker.com" or \
               call_kwargs.args[0] == "noreply@ontdekker.com"
        # to_addrs should contain the recipient
        to_addrs = call_kwargs.kwargs.get("to_addrs") or call_kwargs.args[1]
        assert "recipient@example.com" in to_addrs

    def test_quit_called_after_successful_send(self):
        """quit() is called after a successful send to close the connection."""
        service = _make_smtp_email_service()
        mock_smtp = self._make_mock_smtp()

        with patch("app.services.email.smtplib.SMTP", return_value=mock_smtp):
            service.send_verification_otp(
                email="user@example.com",
                otp="555555",
                expiration_minutes=10,
            )

        mock_smtp.quit.assert_called_once()


# ===========================================================================
# TestSMTPEmailServiceFailures
# ===========================================================================

class TestSMTPEmailServiceFailures:
    """[UNIT] SMTPEmailService — exception handling and propagation."""

    def _make_mock_smtp(self):
        mock = MagicMock()
        mock.starttls = MagicMock()
        mock.login = MagicMock()
        mock.sendmail = MagicMock()
        mock.quit = MagicMock()
        return mock

    def test_smtp_auth_error_raises_email_delivery_exception(self):
        """SMTPAuthenticationError is wrapped in EmailDeliveryException."""
        from app.services.email import EmailDeliveryException
        service = _make_smtp_email_service()
        mock_smtp = self._make_mock_smtp()
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")

        with patch("app.services.email.smtplib.SMTP", return_value=mock_smtp):
            with pytest.raises(EmailDeliveryException) as exc_info:
                service.send_verification_otp(
                    email="user@example.com",
                    otp="123456",
                    expiration_minutes=10,
                )

        assert exc_info.value.error_code == "EMAIL_AUTH_FAILED"

    def test_smtp_connect_error_raises_email_delivery_exception(self):
        """SMTPConnectError is wrapped in EmailDeliveryException."""
        from app.services.email import EmailDeliveryException
        service = _make_smtp_email_service()

        with patch(
            "app.services.email.smtplib.SMTP",
            side_effect=smtplib.SMTPConnectError(421, b"Connection refused"),
        ):
            with pytest.raises(EmailDeliveryException) as exc_info:
                service.send_verification_otp(
                    email="user@example.com",
                    otp="123456",
                    expiration_minutes=10,
                )

        assert exc_info.value.error_code == "EMAIL_CONNECTION_FAILED"

    def test_generic_smtp_exception_raises_email_delivery_exception(self):
        """Any other SMTPException is wrapped in EmailDeliveryException."""
        from app.services.email import EmailDeliveryException
        service = _make_smtp_email_service()
        mock_smtp = self._make_mock_smtp()
        mock_smtp.sendmail.side_effect = smtplib.SMTPException("Generic SMTP error")

        with patch("app.services.email.smtplib.SMTP", return_value=mock_smtp):
            with pytest.raises(EmailDeliveryException) as exc_info:
                service.send_verification_otp(
                    email="user@example.com",
                    otp="123456",
                    expiration_minutes=10,
                )

        assert exc_info.value.error_code == "EMAIL_DELIVERY_FAILED"

    def test_unexpected_exception_raises_email_delivery_exception(self):
        """Any non-SMTP exception is also wrapped in EmailDeliveryException."""
        from app.services.email import EmailDeliveryException
        service = _make_smtp_email_service()

        with patch(
            "app.services.email.smtplib.SMTP",
            side_effect=OSError("Network unreachable"),
        ):
            with pytest.raises(EmailDeliveryException) as exc_info:
                service.send_verification_otp(
                    email="user@example.com",
                    otp="123456",
                    expiration_minutes=10,
                )

        assert exc_info.value.error_code == "EMAIL_DELIVERY_FAILED"

    def test_quit_called_when_send_raises(self):
        """quit() is invoked in the finally block even when sendmail() raises."""
        service = _make_smtp_email_service()
        mock_smtp = self._make_mock_smtp()
        mock_smtp.sendmail.side_effect = smtplib.SMTPException("Send error")

        with patch("app.services.email.smtplib.SMTP", return_value=mock_smtp):
            with pytest.raises(Exception):
                service.send_verification_otp(
                    email="user@example.com",
                    otp="123456",
                    expiration_minutes=10,
                )

        mock_smtp.quit.assert_called_once()

    def test_quit_failure_suppressed_original_error_propagates(self):
        """
        If quit() itself raises, the original EmailDeliveryException still
        propagates — quit() errors are silently suppressed.
        """
        from app.services.email import EmailDeliveryException
        service = _make_smtp_email_service()
        mock_smtp = self._make_mock_smtp()
        mock_smtp.sendmail.side_effect = smtplib.SMTPException("Send error")
        mock_smtp.quit.side_effect = smtplib.SMTPException("Quit also failed")

        with patch("app.services.email.smtplib.SMTP", return_value=mock_smtp):
            with pytest.raises(EmailDeliveryException):
                service.send_verification_otp(
                    email="user@example.com",
                    otp="123456",
                    expiration_minutes=10,
                )

    def test_exception_message_is_descriptive(self):
        """EmailDeliveryException carries a non-empty human-readable message."""
        from app.services.email import EmailDeliveryException
        service = _make_smtp_email_service()
        mock_smtp = self._make_mock_smtp()
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")

        with patch("app.services.email.smtplib.SMTP", return_value=mock_smtp):
            with pytest.raises(EmailDeliveryException) as exc_info:
                service.send_verification_otp(
                    email="user@example.com",
                    otp="123456",
                    expiration_minutes=10,
                )

        assert len(exc_info.value.message) > 0


# ===========================================================================
# TestEmailDeliveryException
# ===========================================================================

class TestEmailDeliveryException:
    """[UNIT] EmailDeliveryException domain exception."""

    def test_default_message_and_error_code(self):
        from app.services.email import EmailDeliveryException
        exc = EmailDeliveryException()
        assert exc.message == "Email delivery failed."
        assert exc.error_code == "EMAIL_DELIVERY_FAILED"

    def test_custom_message_and_error_code(self):
        from app.services.email import EmailDeliveryException
        exc = EmailDeliveryException(
            message="Custom failure.",
            error_code="CUSTOM_CODE",
        )
        assert exc.message == "Custom failure."
        assert exc.error_code == "CUSTOM_CODE"

    def test_is_exception_subclass(self):
        from app.services.email import EmailDeliveryException
        assert issubclass(EmailDeliveryException, Exception)

    def test_str_representation(self):
        from app.services.email import EmailDeliveryException
        exc = EmailDeliveryException(message="Delivery failed.")
        assert "Delivery failed." in str(exc)


# ===========================================================================
# TestEmailServiceInterface
# ===========================================================================

class TestEmailServiceInterface:
    """[UNIT] EmailService abstract base class and DI factory."""

    def test_smtp_email_service_is_subclass_of_email_service(self):
        from app.services.email import EmailService, SMTPEmailService
        assert issubclass(SMTPEmailService, EmailService)

    def test_email_service_is_abstract(self):
        """EmailService itself cannot be instantiated (it is abstract)."""
        from app.services.email import EmailService
        with pytest.raises(TypeError):
            EmailService()  # type: ignore[abstract]

    def test_smtp_email_service_is_concrete(self):
        """SMTPEmailService can be instantiated without error."""
        service = _make_smtp_email_service()
        from app.services.email import SMTPEmailService
        assert isinstance(service, SMTPEmailService)

    def test_get_email_service_returns_smtp_email_service(self):
        """get_email_service() dependency factory returns an SMTPEmailService."""
        from app.dependencies.email import get_email_service
        from app.services.email import SMTPEmailService
        service = get_email_service()
        assert isinstance(service, SMTPEmailService)

    def test_get_email_service_returns_email_service_instance(self):
        """get_email_service() result satisfies the EmailService interface."""
        from app.dependencies.email import get_email_service
        from app.services.email import EmailService
        service = get_email_service()
        assert isinstance(service, EmailService)
