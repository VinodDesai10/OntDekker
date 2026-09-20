"""
Authentication Service — Security Utilities

Service-specific helpers that sit on top of the shared security utilities.
These functions know about the service's settings (TTL values, secret key)
and generate tokens with the correct claims for the OntDekker JWT contract.

Shared utilities used (NOT redefined here):
  shared.utils.security.get_password_hash   — bcrypt password hashing
  shared.utils.security.verify_password     — bcrypt password verification
  shared.utils.security.create_jwt_token    — JWT encode
  shared.utils.security.decode_jwt_token    — JWT decode

JWT claims contract (from 03-microservices.md):
  sub    — user UUID string
  email  — user email address
  roles  — list of role name strings
  iat    — issued-at timestamp (added by create_jwt_token)
  exp    — expiry timestamp (added by create_jwt_token)
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import List

from app.config.settings import settings
from shared.utils.security import create_jwt_token


def generate_access_token(
    user_id: str,
    email: str,
    roles: List[str],
) -> str:
    """
    Create a signed JWT access token with the documented claims.

    TTL is controlled by settings.ACCESS_TOKEN_EXPIRE_MINUTES.
    Secret and algorithm come from settings (inherited from CommonSettings).
    """
    payload = {
        "sub": user_id,
        "email": email,
        "roles": roles,
    }
    return create_jwt_token(
        data=payload,
        secret_key=settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def generate_raw_refresh_token() -> str:
    """
    Generate a cryptographically secure, high-entropy opaque refresh token.

    Uses secrets.token_urlsafe(48) → 64 URL-safe base64 characters.
    This value is returned to the client; only its SHA-256 hash is stored.
    """
    return secrets.token_urlsafe(48)


def generate_raw_opaque_token() -> str:
    """
    Generate a cryptographically secure opaque token for email verification
    and password reset flows.

    Same entropy source as refresh tokens.  The raw value is sent via email;
    only its SHA-256 hash is stored in the database.
    """
    return secrets.token_urlsafe(48)


def access_token_expires_at() -> datetime:
    """Return the UTC datetime when a new access token will expire."""
    return datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )


def refresh_token_expires_at() -> datetime:
    """Return the UTC datetime when a new refresh token will expire."""
    return datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )


def verification_token_expires_at() -> datetime:
    """Email verification tokens expire after 24 hours."""
    return datetime.now(timezone.utc) + timedelta(hours=24)


def reset_token_expires_at() -> datetime:
    """Password reset tokens expire after 1 hour."""
    return datetime.now(timezone.utc) + timedelta(hours=1)
