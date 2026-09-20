/**
 * MSW handlers for the Authentication Service endpoints.
 *
 * Base URL: http://localhost:8000 (default from env.ts AUTH_API_URL)
 *
 * Provides factory functions so each test can supply its own response data
 * without hard-coding values in the shared module.
 *
 * Usage:
 *   server.use(authHandlers.refreshSuccess({ access_token: "tok" }));
 *   server.use(authHandlers.refreshFailure(401, "Token expired"));
 */

import { http, HttpResponse } from "msw";

const BASE = "http://localhost:8000";

// ---------------------------------------------------------------------------
// Canonical fixture shapes
// ---------------------------------------------------------------------------

export const DEFAULT_USER = {
  id: "user-id-123",
  email: "explorer@ontdekker.com",
  is_verified: true,
  is_active: true,
  roles: ["user"],
  created_at: "2026-01-01T00:00:00Z",
};

export const DEFAULT_ACCESS_TOKEN = "access-token-abc";
export const DEFAULT_REFRESH_TOKEN = "refresh-token-xyz";

// ---------------------------------------------------------------------------
// Handler factories
// ---------------------------------------------------------------------------

export const authHandlers = {
  /** POST /auth/refresh → 200 AccessTokenResponse */
  refreshSuccess: (overrides?: { access_token?: string }) =>
    http.post(`${BASE}/auth/refresh`, () =>
      HttpResponse.json({
        access_token: overrides?.access_token ?? DEFAULT_ACCESS_TOKEN,
        token_type: "bearer",
        expires_in: 900,
      })
    ),

  /** POST /auth/refresh → error */
  refreshFailure: (status = 401, message = "Token expired or invalid") =>
    http.post(`${BASE}/auth/refresh`, () =>
      HttpResponse.json(
        { success: false, message, code: "TOKEN_INVALID" },
        { status }
      )
    ),

  /** GET /auth/me → 200 UserIdentityResponse */
  getMeSuccess: (user = DEFAULT_USER) =>
    http.get(`${BASE}/auth/me`, () => HttpResponse.json(user)),

  /** GET /auth/me → error */
  getMeFailure: (status = 401, message = "Unauthorized") =>
    http.get(`${BASE}/auth/me`, () =>
      HttpResponse.json(
        { success: false, message, code: "UNAUTHORIZED" },
        { status }
      )
    ),

  /** POST /auth/login → 200 TokenResponse */
  loginSuccess: (overrides?: {
    access_token?: string;
    refresh_token?: string;
  }) =>
    http.post(`${BASE}/auth/login`, () =>
      HttpResponse.json({
        access_token: overrides?.access_token ?? DEFAULT_ACCESS_TOKEN,
        refresh_token: overrides?.refresh_token ?? DEFAULT_REFRESH_TOKEN,
        token_type: "bearer",
        expires_in: 900,
      })
    ),

  /** POST /auth/login → error */
  loginFailure: (status = 401, message = "Invalid credentials") =>
    http.post(`${BASE}/auth/login`, () =>
      HttpResponse.json(
        { success: false, message, code: "INVALID_CREDENTIALS" },
        { status }
      )
    ),

  /** POST /auth/logout → 200 MessageResponse */
  logoutSuccess: () =>
    http.post(`${BASE}/auth/logout`, () =>
      HttpResponse.json({ message: "Logged out successfully" })
    ),

  /** POST /auth/logout → error (non-fatal in AuthContext) */
  logoutFailure: (status = 500, message = "Logout failed") =>
    http.post(`${BASE}/auth/logout`, () =>
      HttpResponse.json(
        { success: false, message, code: "LOGOUT_FAILED" },
        { status }
      )
    ),

  /** POST /auth/register → 201 RegisterResponse */
  registerSuccess: (overrides?: {
    message?: string;
    user_id?: string;
    email?: string;
  }) =>
    http.post(`${BASE}/auth/register`, () =>
      HttpResponse.json(
        {
          message: overrides?.message ?? "Account created successfully.",
          user_id: overrides?.user_id ?? "new-user-id-456",
          email: overrides?.email ?? "explorer@ontdekker.com",
        },
        { status: 201 }
      )
    ),

  /** POST /auth/register → error (e.g. 409 email already registered) */
  registerFailure: (status = 409, message = "Email already registered") =>
    http.post(`${BASE}/auth/register`, () =>
      HttpResponse.json(
        { success: false, message, code: "EMAIL_ALREADY_REGISTERED" },
        { status }
      )
    ),

  /** POST /auth/forgot-password → 200 MessageResponse */
  forgotPasswordSuccess: (message = "If that email exists, a reset link has been sent.") =>
    http.post(`${BASE}/auth/forgot-password`, () =>
      HttpResponse.json({ message })
    ),

  /** POST /auth/forgot-password → error */
  forgotPasswordFailure: (status = 500, message = "Internal server error") =>
    http.post(`${BASE}/auth/forgot-password`, () =>
      HttpResponse.json(
        { success: false, message, code: "INTERNAL_ERROR" },
        { status }
      )
    ),

  /** GET /auth/verify-email → 200 MessageResponse */
  verifyEmailSuccess: (message = "Email verified successfully.") =>
    http.get(`${BASE}/auth/verify-email`, () =>
      HttpResponse.json({ message })
    ),

  /** GET /auth/verify-email → error (e.g. 401 invalid/expired token) */
  verifyEmailFailure: (status = 401, message = "Verification token is invalid or has expired") =>
    http.get(`${BASE}/auth/verify-email`, () =>
      HttpResponse.json(
        { success: false, message, code: "TOKEN_INVALID" },
        { status }
      )
    ),

  /** POST /auth/reset-password → 200 MessageResponse */
  resetPasswordSuccess: (message = "Password has been reset successfully.") =>
    http.post(`${BASE}/auth/reset-password`, () =>
      HttpResponse.json({ message })
    ),

  /** POST /auth/reset-password → error (e.g. 401 invalid/expired token) */
  resetPasswordFailure: (status = 401, message = "Reset token is invalid or has expired") =>
    http.post(`${BASE}/auth/reset-password`, () =>
      HttpResponse.json(
        { success: false, message, code: "TOKEN_INVALID" },
        { status }
      )
    ),

  // ---------------------------------------------------------------------------
  // Checkpoint 4 — OTP-based email verification
  // ---------------------------------------------------------------------------

  /** POST /auth/verify-email → 200 MessageResponse (OTP flow) */
  verifyEmailOtpSuccess: (message = "Email verified successfully.") =>
    http.post(`${BASE}/auth/verify-email`, () =>
      HttpResponse.json({ message })
    ),

  /** POST /auth/verify-email → error (OTP flow) */
  verifyEmailOtpFailure: (
    status = 401,
    message = "Incorrect OTP. Please try again.",
    code = "OTP_INVALID"
  ) =>
    http.post(`${BASE}/auth/verify-email`, () =>
      HttpResponse.json(
        { success: false, message, code },
        { status }
      )
    ),

  /** POST /auth/resend-otp → 200 MessageResponse */
  resendOtpSuccess: (message = "A new verification code has been sent to your email address.") =>
    http.post(`${BASE}/auth/resend-otp`, () =>
      HttpResponse.json({ message })
    ),

  /** POST /auth/resend-otp → error (e.g. 404 user not found, 409 already verified) */
  resendOtpFailure: (
    status = 404,
    message = "No account found with this email address.",
    code = "USER_NOT_FOUND"
  ) =>
    http.post(`${BASE}/auth/resend-otp`, () =>
      HttpResponse.json(
        { success: false, message, code },
        { status }
      )
    ),
};
