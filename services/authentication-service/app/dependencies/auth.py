"""
Authentication Service — FastAPI Dependencies

Service-specific dependency functions that wire the request lifecycle to
the service layer.

These complement the shared dependencies in shared/dependencies.py:
  - shared.dependencies.get_db            — async SQLAlchemy session
  - shared.dependencies.get_current_user  — validates JWT, returns payload

This module adds:
  - get_otp_service          — constructs OTPService with the current session
  - get_auth_service         — constructs AuthService with session + OTP + Email
  - get_current_user_payload — thin alias for the /me endpoint's needs

Checkpoint 4:
  get_auth_service now injects OTPService and EmailService into AuthService
  so that both can be mocked in tests via FastAPI dependency_overrides
  without modifying production code.
"""

from typing import Any, Dict

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.email import get_email_service
from app.services.auth import AuthService
from app.services.email import EmailService
from app.services.otp import OTPService
from shared.dependencies import get_current_user, get_db


async def get_otp_service(
    session: AsyncSession = Depends(get_db),
) -> OTPService:
    """
    Construct an OTPService bound to the current request's DB session.

    A new OTPService instance is created per request — no shared state.
    """
    return OTPService(session=session)


async def get_auth_service(
    session: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
) -> AuthService:
    """
    Construct an AuthService bound to the current request's DB session.

    Checkpoint 4: OTPService and EmailService are wired in here so that
    endpoint tests can override get_email_service (and/or get_otp_service)
    without touching AuthService directly.

    The OTPService is constructed from the same session as AuthService so
    that OTP persistence participates in the same transaction.
    The session is managed by get_db (commit on success, rollback on error).
    A new AuthService instance is created per request — no shared state.
    """
    otp_service = OTPService(session=session)
    return AuthService(
        session=session,
        otp_service=otp_service,
        email_service=email_service,
    )


async def get_current_user_payload(
    payload: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Re-export of shared.dependencies.get_current_user for use on protected
    endpoints in this service.

    Returns the decoded JWT payload dict containing:
      sub, email, roles, iat, exp
    """
    return payload
