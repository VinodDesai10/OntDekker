"""
Authentication Service — Pydantic Schemas

Request validation and response serialization for all auth endpoints.

Security rules enforced here:
  - password_hash and token_hash are NEVER exposed in any response.
  - JWT claims (sub, email, roles) are the only identity fields in token responses.
  - Email is normalised to lowercase before any DB interaction.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """POST /auth/register"""

    email: EmailStr = Field(..., description="Valid email address.")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password — minimum 8 characters.",
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class LoginRequest(BaseModel):
    """POST /auth/login"""

    email: EmailStr = Field(..., description="Registered email address.")
    password: str = Field(..., description="Account password.")

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class RefreshRequest(BaseModel):
    """POST /auth/refresh"""

    refresh_token: str = Field(..., description="Opaque refresh token string.")


class LogoutRequest(BaseModel):
    """POST /auth/logout"""

    refresh_token: str = Field(..., description="Refresh token to revoke.")


class ForgotPasswordRequest(BaseModel):
    """POST /auth/forgot-password"""

    email: EmailStr = Field(..., description="Email address for the account.")

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    """POST /auth/reset-password"""

    token: str = Field(..., description="Password reset token from email.")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password — minimum 8 characters.",
    )


class VerifyEmailRequest(BaseModel):
    """Query parameter schema for GET /auth/verify-email"""

    token: str = Field(..., description="Email verification token.")


class VerifyEmailOTPRequest(BaseModel):
    """POST /auth/verify-email — OTP-based email verification."""

    email: EmailStr = Field(..., description="The email address being verified.")
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit numeric OTP code from the verification email.",
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class ResendOTPRequest(BaseModel):
    """POST /auth/resend-otp — request a fresh OTP email."""

    email: EmailStr = Field(..., description="Email address for the account.")

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class UserIdentityResponse(BaseModel):
    """
    Represents a user's public identity — returned by /auth/me and
    embedded in other responses.

    Never contains password_hash, token_hash, or raw tokens.
    """

    id: uuid.UUID
    email: str
    is_verified: bool
    is_active: bool
    roles: List[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """
    Returned by /auth/login.

    Contains:
      - access_token  : short-lived JWT (Bearer token for API requests)
      - refresh_token : opaque high-entropy string for session renewal
      - token_type    : always "bearer"
      - expires_in    : access token TTL in seconds (informational)
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token TTL in seconds.")


class AccessTokenResponse(BaseModel):
    """Returned by /auth/refresh — new access token only."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MessageResponse(BaseModel):
    """Generic success message for endpoints that have no data payload."""

    message: str


class RegisterResponse(BaseModel):
    """Returned by POST /auth/register on success (HTTP 201)."""

    message: str
    user_id: uuid.UUID
    email: str
