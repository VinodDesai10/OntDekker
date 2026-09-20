"""
Authentication Service — Email Service (Checkpoint 3)

Defines the EmailService abstraction and the SMTPEmailService concrete
implementation.

Architecture:
  EmailService (ABC)        — public interface that the auth layer will program to.
  SMTPEmailService          — production implementation backed by smtplib SMTP.

Design decisions:
  - The abstract interface decouples callers from the transport mechanism.
    A stub or mock implementation can replace SMTPEmailService in tests
    without touching the call sites.
  - OTPService does NOT directly contain SMTP logic — it will call
    EmailService.send_verification_otp() once the endpoint integration
    checkpoint wires everything together.
  - send_verification_otp() is synchronous at the SMTP level (smtplib is
    blocking). It is designed to run in a thread-pool executor when called
    from an async context. The dependency injection layer handles that.
  - Template rendering is pure string interpolation — no third-party template
    engine is added, keeping dependencies minimal and consistent with the
    existing project.
  - All failures raise EmailDeliveryException (a domain exception defined
    here). Callers must not silently swallow it.
  - Credentials are sourced exclusively from settings. Raw values are never
    logged.

Usage (future endpoint checkpoint):
    email_service = get_email_service()           # from DI
    await email_service.send_verification_otp(
        email="user@example.com",
        otp="083921",
        expiration_minutes=10,
        recipient_name="Alice",
    )
"""

import logging
import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config.settings import settings
from app.templates.email import render_otp_html, render_otp_plain

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain exception
# ---------------------------------------------------------------------------

class EmailDeliveryException(Exception):
    """
    Raised when the email service fails to deliver a message.

    Wraps the underlying SMTP error so callers receive a consistent
    service-level exception regardless of the transport used.

    Attributes:
        message   — human-readable failure description.
        error_code — machine-readable code for upstream exception handling.
    """

    def __init__(
        self,
        message: str = "Email delivery failed.",
        error_code: str = "EMAIL_DELIVERY_FAILED",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class EmailService(ABC):
    """
    Abstract base class defining the email delivery interface.

    All callers in the authentication layer (endpoints, other services)
    must program to this interface, never to SMTPEmailService directly.
    This makes the delivery mechanism swappable without changing call sites.
    """

    @abstractmethod
    def send_verification_otp(
        self,
        email: str,
        otp: str,
        expiration_minutes: int,
        recipient_name: Optional[str] = None,
    ) -> None:
        """
        Build and send an OTP verification email to the given address.

        The method is intentionally synchronous (smtplib is blocking).
        Callers in async contexts should run it via
        asyncio.get_event_loop().run_in_executor() or FastAPI's
        BackgroundTasks mechanism.

        Args:
            email:              Recipient email address.
            otp:                Plaintext 6-digit OTP to embed in the email.
                                Never persisted or logged by this method.
            expiration_minutes: Number of minutes before the OTP expires.
                                Shown in the email body to guide the user.
            recipient_name:     Optional display name for personalisation.
                                Falls back to a generic greeting when omitted.

        Raises:
            EmailDeliveryException: If the message cannot be sent for any
                reason (auth failure, connection error, SMTP rejection, etc.).
        """
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# SMTP implementation
# ---------------------------------------------------------------------------

class SMTPEmailService(EmailService):
    """
    Production email service backed by smtplib SMTP.

    Reads all configuration from app.config.settings:
      SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
      SMTP_FROM_EMAIL, SMTP_FROM_NAME, SMTP_USE_TLS.

    Connection lifecycle per call:
      1. Open a new SMTP connection.
      2. Issue STARTTLS (when SMTP_USE_TLS is True).
      3. Authenticate with username / password.
      4. Send the message.
      5. Quit — connection closed even when an exception is raised.

    A fresh connection is opened per call rather than maintaining a
    long-lived connection, which avoids stale-connection issues in a
    process that may stay idle for extended periods.
    """

    def send_verification_otp(
        self,
        email: str,
        otp: str,
        expiration_minutes: int,
        recipient_name: Optional[str] = None,
    ) -> None:
        """
        Send an OTP verification email via SMTP.

        Builds a multipart/alternative message containing both a plain-text
        and an HTML version. Clients that support HTML will render the richer
        version; others fall back to plain text.

        Args:
            email:              Recipient email address.
            otp:                Plaintext 6-digit OTP (never logged).
            expiration_minutes: Expiry window shown to the user.
            recipient_name:     Optional first name for greeting personalisation.

        Raises:
            EmailDeliveryException: Wraps SMTPAuthenticationError,
                SMTPConnectError, SMTPException, or any unexpected error
                encountered during delivery.
        """
        subject = "Verify your OntDekker email"

        # Render both versions of the email body from templates.
        html_body = render_otp_html(
            otp=otp,
            expiration_minutes=expiration_minutes,
            recipient_name=recipient_name,
        )
        plain_body = render_otp_plain(
            otp=otp,
            expiration_minutes=expiration_minutes,
            recipient_name=recipient_name,
        )

        # Build the MIME message.
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = email

        # Attach plain text first; HTML second — the last attachment wins
        # for clients that support it (RFC 2046 §5.1.4).
        message.attach(MIMEText(plain_body, "plain", "utf-8"))
        message.attach(MIMEText(html_body, "html", "utf-8"))

        smtp: Optional[smtplib.SMTP] = None

        try:
            logger.info(
                "Sending OTP email",
                extra={
                    "extra_data": {
                        "recipient": email,
                        "smtp_host": settings.SMTP_HOST,
                        "smtp_port": settings.SMTP_PORT,
                        # OTP intentionally omitted from logs.
                    }
                },
            )

            # Step 1: open connection
            smtp = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)

            # Step 2: upgrade to TLS when configured
            if settings.SMTP_USE_TLS:
                smtp.starttls()

            # Step 3: authenticate
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

            # Step 4: send
            smtp.sendmail(
                from_addr=settings.SMTP_FROM_EMAIL,
                to_addrs=[email],
                msg=message.as_string(),
            )

            logger.info(
                "OTP email sent successfully",
                extra={"extra_data": {"recipient": email}},
            )

        except smtplib.SMTPAuthenticationError as exc:
            logger.error(
                "SMTP authentication failed",
                extra={
                    "extra_data": {
                        "recipient": email,
                        "smtp_host": settings.SMTP_HOST,
                        "error": str(exc),
                    }
                },
            )
            raise EmailDeliveryException(
                message="Email delivery failed: SMTP authentication error.",
                error_code="EMAIL_AUTH_FAILED",
            ) from exc

        except smtplib.SMTPConnectError as exc:
            logger.error(
                "SMTP connection failed",
                extra={
                    "extra_data": {
                        "recipient": email,
                        "smtp_host": settings.SMTP_HOST,
                        "smtp_port": settings.SMTP_PORT,
                        "error": str(exc),
                    }
                },
            )
            raise EmailDeliveryException(
                message="Email delivery failed: could not connect to SMTP server.",
                error_code="EMAIL_CONNECTION_FAILED",
            ) from exc

        except smtplib.SMTPException as exc:
            logger.error(
                "SMTP error during email delivery",
                extra={
                    "extra_data": {
                        "recipient": email,
                        "error": str(exc),
                    }
                },
            )
            raise EmailDeliveryException(
                message="Email delivery failed: SMTP error.",
                error_code="EMAIL_DELIVERY_FAILED",
            ) from exc

        except Exception as exc:
            logger.error(
                "Unexpected error during email delivery",
                extra={
                    "extra_data": {
                        "recipient": email,
                        "error": str(exc),
                    }
                },
            )
            raise EmailDeliveryException(
                message="Email delivery failed due to an unexpected error.",
                error_code="EMAIL_DELIVERY_FAILED",
            ) from exc

        finally:
            # Step 5: always close the connection, even on failure.
            if smtp is not None:
                try:
                    smtp.quit()
                except smtplib.SMTPException:
                    # quit() can raise if the connection is already broken.
                    # Suppress — the real error was already raised above.
                    pass
