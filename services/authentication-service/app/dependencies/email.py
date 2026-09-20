"""
Authentication Service — Email Service Dependency

Provides the FastAPI dependency function that supplies an EmailService
instance to route handlers and other dependencies.

The function returns a concrete SMTPEmailService by default.
In tests, callers can override this dependency using FastAPI's
dependency_overrides mechanism to inject a mock or stub implementation
without touching production code.

Usage in an endpoint:
    from app.dependencies.email import get_email_service
    from app.services.email import EmailService

    @router.post("/some-route")
    async def some_route(
        email_service: EmailService = Depends(get_email_service),
    ):
        email_service.send_verification_otp(...)

Override in tests:
    app.dependency_overrides[get_email_service] = lambda: MockEmailService()
"""

from app.services.email import EmailService, SMTPEmailService


def get_email_service() -> EmailService:
    """
    Construct and return an SMTPEmailService instance.

    No request-scoped state is required — SMTPEmailService opens a fresh
    SMTP connection on each send_verification_otp() call and closes it
    before returning.

    Returns:
        EmailService: A production-ready SMTPEmailService instance.
    """
    return SMTPEmailService()
