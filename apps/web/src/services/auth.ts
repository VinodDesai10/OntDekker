/**
 * OntDekker Frontend — Authentication Service API
 *
 * Typed TypeScript functions for all Authentication Service endpoints.
 * Contracts match the backend schemas defined in:
 *   services/authentication-service/app/schemas/auth.py
 *
 * All functions use the authHttp instance from api.ts, which:
 *   - Auto-attaches Bearer token when available
 *   - Normalizes backend error envelopes to ApiError
 *   - Does NOT retry 401s automatically (handled by AuthContext)
 *
 * Does NOT:
 *   - Store tokens (AuthContext responsibility)
 *   - Log sensitive values
 *   - Implement token refresh logic (AuthContext responsibility)
 */

import { authHttp } from "./api";

// ---------------------------------------------------------------------------
// TypeScript types matching backend Pydantic schemas
// ---------------------------------------------------------------------------

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface RegisterResponse {
  message: string;
  user_id: string;
  email: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface LogoutRequest {
  refresh_token: string;
}

export interface MessageResponse {
  message: string;
}

export interface UserIdentityResponse {
  id: string;
  email: string;
  is_verified: boolean;
  is_active: boolean;
  roles: string[];
  created_at: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

// Checkpoint 4 — OTP-based email verification

export interface VerifyEmailOtpRequest {
  email: string;
  otp: string;
}

export interface ResendOtpRequest {
  email: string;
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

/**
 * POST /auth/register
 *
 * Create a new user account.
 * Returns 201 on success, 409 if email already registered.
 */
export async function register(
  data: RegisterRequest
): Promise<RegisterResponse> {
  const response = await authHttp.post<RegisterResponse>("/auth/register", data);
  return response.data;
}

/**
 * POST /auth/login
 *
 * Authenticate and receive access + refresh tokens.
 * Returns 401 for invalid credentials or inactive account.
 */
export async function login(data: LoginRequest): Promise<TokenResponse> {
  const response = await authHttp.post<TokenResponse>("/auth/login", data);
  return response.data;
}

/**
 * POST /auth/refresh
 *
 * Exchange a valid refresh token for a new access token.
 * Returns 401 if token is invalid, revoked, or expired.
 */
export async function refresh(
  data: RefreshRequest
): Promise<AccessTokenResponse> {
  const response = await authHttp.post<AccessTokenResponse>(
    "/auth/refresh",
    data
  );
  return response.data;
}

/**
 * POST /auth/logout
 *
 * Revoke a refresh token.
 * Idempotent — returns 200 even if token is already revoked or unknown.
 */
export async function logout(data: LogoutRequest): Promise<MessageResponse> {
  const response = await authHttp.post<MessageResponse>("/auth/logout", data);
  return response.data;
}

/**
 * GET /auth/me
 *
 * Return the current authenticated user's identity.
 * Requires a valid Bearer JWT (auto-attached by authHttp).
 * Returns 401 if token is missing or invalid.
 */
export async function getMe(): Promise<UserIdentityResponse> {
  const response = await authHttp.get<UserIdentityResponse>("/auth/me");
  return response.data;
}

/**
 * GET /auth/verify-email
 *
 * Verify email address using a one-time token.
 * Token is passed as a query parameter.
 * Returns 401 if token is invalid or expired.
 */
export async function verifyEmail(token: string): Promise<MessageResponse> {
  const response = await authHttp.get<MessageResponse>("/auth/verify-email", {
    params: { token },
  });
  return response.data;
}

/**
 * POST /auth/forgot-password
 *
 * Request a password reset token for the given email.
 * Always returns 200 (prevents account enumeration).
 * Email delivery is Phase 2 infrastructure.
 */
export async function forgotPassword(
  data: ForgotPasswordRequest
): Promise<MessageResponse> {
  const response = await authHttp.post<MessageResponse>(
    "/auth/forgot-password",
    data
  );
  return response.data;
}

/**
 * POST /auth/reset-password
 *
 * Reset password using a one-time token.
 * Returns 401 if token is invalid, expired, or already used.
 */
export async function resetPassword(
  data: ResetPasswordRequest
): Promise<MessageResponse> {
  const response = await authHttp.post<MessageResponse>(
    "/auth/reset-password",
    data
  );
  return response.data;
}

/**
 * POST /auth/verify-email
 *
 * Verify email address using a 6-digit OTP submitted by the user.
 * Checkpoint 4 — OTP-based flow (distinct from the opaque-token GET flow).
 *
 * Returns 200 on success.
 * Returns 401 for invalid/expired OTP or max attempts exceeded.
 * Returns 404 if the email is not registered.
 * Returns 409 if the email is already verified.
 */
export async function verifyEmailOtp(
  data: VerifyEmailOtpRequest
): Promise<MessageResponse> {
  const response = await authHttp.post<MessageResponse>(
    "/auth/verify-email",
    data
  );
  return response.data;
}

/**
 * POST /auth/resend-otp
 *
 * Request a fresh verification OTP for the given email address.
 * Invalidates any previously issued OTP for that user.
 * Checkpoint 4 — used when the original OTP was not received or has expired.
 *
 * Returns 200 on success.
 * Returns 404 if the email is not registered.
 * Returns 409 if the email is already verified.
 */
export async function resendOtp(
  data: ResendOtpRequest
): Promise<MessageResponse> {
  const response = await authHttp.post<MessageResponse>(
    "/auth/resend-otp",
    data
  );
  return response.data;
}
