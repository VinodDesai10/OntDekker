"""
Authentication Service — API Router

Public endpoints documented in 03-microservices.md:

  POST   /auth/register          — create new account (HTTP 201)
  POST   /auth/login             — authenticate, receive tokens (HTTP 200)
  POST   /auth/refresh           — exchange refresh token for new access token (HTTP 200)
  POST   /auth/logout            — revoke refresh token (HTTP 200)
  GET    /auth/me                — return current user identity (HTTP 200) [requires JWT]
  GET    /auth/verify-email      — mark email as verified via opaque token (HTTP 200)
  POST   /auth/verify-email      — verify email using a 6-digit OTP (HTTP 200) [Checkpoint 4]
  POST   /auth/resend-otp        — request a new OTP verification code (HTTP 200) [Checkpoint 4]
  POST   /auth/forgot-password   — generate password reset token (HTTP 200)
  POST   /auth/reset-password    — update password (HTTP 200)

API prefix resolution:
  team_guidelines.md: "All public endpoints must utilize the gateway prefix
  standard: /api/v1/{service-name}/*. Traefik strips the prefix before
  forwarding to the microservice port."

  The service name is "authentication-service".
  External URL:  /api/v1/authentication/auth/register
  Internal path: /auth/register   ← what FastAPI declares

  This router is mounted at /auth in main.py.
  Traefik strips /api/v1/authentication before forwarding.

Phase 1 / Checkpoint 4 status of each endpoint:
  /register      — IMPLEMENTED + Checkpoint 4 (OTP generated, email sent)
  /login         — IMPLEMENTED + Checkpoint 4 (email verification gate)
  /refresh       — IMPLEMENTED
  /logout        — IMPLEMENTED
  /me            — IMPLEMENTED
  /verify-email  — GET: opaque token (Phase 1); POST: OTP (Checkpoint 4)
  /resend-otp    — IMPLEMENTED (Checkpoint 4)
  /forgot-password  — IMPLEMENTED
  /reset-password   — IMPLEMENTED
"""

import logging

from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_auth_service, get_current_user_payload
from app.schemas.auth import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResendOTPRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserIdentityResponse,
    VerifyEmailOTPRequest,
)
from app.services.auth import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    """
    Create a new user account.

    - Email is normalised to lowercase.
    - Password is bcrypt-hashed before storage.
    - The USER role is assigned atomically in the same transaction.
    - An email verification token is generated and an OTP is sent via email.
    - Returns 409 if the email is already registered.
    """
    return await service.register(email=body.email, password=body.password)


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive access + refresh tokens",
)
async def login(
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Verify credentials and issue tokens.

    - Returns 401 for unknown email or wrong password (no enumeration).
    - Returns 401 with EMAIL_NOT_VERIFIED if the account has not been
      verified yet — user must complete OTP verification first.
    - Returns 401 if the account is inactive.
    - access_token: short-lived JWT (Bearer).
    - refresh_token: opaque high-entropy string, persisted as SHA-256 hash.
    """
    return await service.login(email=body.email, password=body.password)


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange a valid refresh token for a new access token",
)
async def refresh(
    body: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> AccessTokenResponse:
    """
    Validate the refresh token and return a new access token.

    - Returns 401 if the token is invalid, revoked, or expired.
    """
    return await service.refresh(raw_refresh_token=body.refresh_token)


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke a refresh token",
)
async def logout(
    body: LogoutRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """
    Revoke the provided refresh token.

    - Idempotent: revoking an already-revoked or unknown token returns 200.
    """
    return await service.logout(raw_refresh_token=body.refresh_token)


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserIdentityResponse,
    status_code=status.HTTP_200_OK,
    summary="Return the current authenticated user's identity",
)
async def me(
    jwt_payload: dict = Depends(get_current_user_payload),
    service: AuthService = Depends(get_auth_service),
) -> UserIdentityResponse:
    """
    Return the identity of the currently authenticated user.

    Requires a valid Bearer JWT in the Authorization header.
    """
    return await service.get_me(jwt_payload=jwt_payload)


# ---------------------------------------------------------------------------
# GET /auth/verify-email  (Phase 1 — opaque token)
# ---------------------------------------------------------------------------

@router.get(
    "/verify-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify email address using a one-time opaque token",
)
async def verify_email_token(
    token: str,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """
    Verify email ownership using a one-time opaque token (Phase 1 flow).

    This endpoint exists for compatibility with the opaque-token email
    verification flow implemented in Phase 1. The new OTP-based flow is
    at POST /auth/verify-email.
    """
    return await service.verify_email(raw_token=token)


# ---------------------------------------------------------------------------
# POST /auth/verify-email  (Checkpoint 4 — OTP-based)
# ---------------------------------------------------------------------------

@router.post(
    "/verify-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify email address using a 6-digit OTP code",
)
async def verify_email_otp(
    body: VerifyEmailOTPRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """
    Verify email ownership using a 6-digit OTP sent at registration or resend.

    Request body:
      - email: the address being verified
      - otp:   the 6-digit code from the verification email

    Error responses:
      - 404 USER_NOT_FOUND           — no account with this email
      - 409 ALREADY_VERIFIED         — email is already confirmed
      - 401 OTP_NOT_FOUND            — no active OTP; request a resend
      - 401 OTP_EXPIRED              — OTP TTL elapsed; request a resend
      - 401 OTP_INVALID              — wrong code; attempts remaining
      - 401 OTP_MAX_ATTEMPTS_EXCEEDED — too many wrong attempts; request a resend
    """
    return await service.verify_email_otp(email=body.email, raw_otp=body.otp)


# ---------------------------------------------------------------------------
# POST /auth/resend-otp  (Checkpoint 4)
# ---------------------------------------------------------------------------

@router.post(
    "/resend-otp",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a new OTP verification code",
)
async def resend_otp(
    body: ResendOTPRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """
    Invalidate any existing OTP and generate a fresh verification code.

    A new code is emailed to the provided address if the account exists and
    is not yet verified.

    Error responses:
      - 404 USER_NOT_FOUND  — no account with this email
      - 409 ALREADY_VERIFIED — email is already confirmed, no OTP needed
    """
    return await service.resend_otp(email=body.email)


# ---------------------------------------------------------------------------
# POST /auth/forgot-password
# ---------------------------------------------------------------------------

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a password reset token",
)
async def forgot_password(
    body: ForgotPasswordRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """
    Generate a password reset token for the given email.

    - Always returns success regardless of whether the email exists
      (prevents account enumeration).
    """
    return await service.forgot_password(email=body.email)


# ---------------------------------------------------------------------------
# POST /auth/reset-password
# ---------------------------------------------------------------------------

@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password using a one-time token",
)
async def reset_password(
    body: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """
    Update the user's password using a valid one-time reset token.

    - Returns 401 if token is invalid, expired, or already used.
    - New password is bcrypt-hashed before storage.
    - Token is consumed atomically with the password update.
    """
    return await service.reset_password(
        raw_token=body.token,
        new_password=body.new_password,
    )
