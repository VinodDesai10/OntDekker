"use client";

/**
 * OntDekker Frontend — Authentication Context
 *
 * Manages the authenticated user session across the application.
 *
 * Token strategy (matches current backend contract — JSON body, no HttpOnly cookies):
 *   - Access token : in-memory only (never persisted to browser storage)
 *   - Refresh token: localStorage (Phase 1 — backend uses JSON body, not HttpOnly cookie)
 *
 * On mount: reads refresh_token from localStorage, calls POST /auth/refresh,
 * then calls GET /auth/me to restore the session. Clears stale tokens on failure.
 *
 * Endpoint calls are delegated to src/services/auth.ts typed functions.
 * This file does not construct endpoint paths or HTTP verbs directly.
 *
 * Does NOT:
 *   - Decode JWT payload client-side as a substitute for /auth/me
 *   - Implement automatic Axios 401 retry (belongs in a later interceptor layer)
 *   - Log tokens or Authorization header values
 *   - Import or call authHttp directly (delegated to auth service)
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { setAccessToken } from "@/services/api";
import { setAuthToken } from "@/services/axios";
import {
  getMe,
  login as authLogin,
  logout as authLogout,
  refresh as authRefresh,
  verifyEmailOtp as authVerifyEmailOtp,
  resendOtp as authResendOtp,
  type MessageResponse,
  type UserIdentityResponse,
  type VerifyEmailOtpRequest,
  type ResendOtpRequest,
} from "@/services/auth";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** The authenticated user identity as returned by /auth/me. */
export type AuthUser = UserIdentityResponse;

interface LoginCredentials {
  email: string;
  password: string;
}

// ---------------------------------------------------------------------------
// Storage key
// ---------------------------------------------------------------------------

const REFRESH_TOKEN_KEY = "ontdekker_refresh_token";

function getStoredRefreshToken(): string | null {
  if (
    typeof window === "undefined" ||
    typeof localStorage === "undefined" ||
    typeof localStorage.getItem !== "function"
  ) {
    return null;
  }
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    return null;
  }
}

function storeRefreshToken(token: string): void {
  if (
    typeof window === "undefined" ||
    typeof localStorage === "undefined" ||
    typeof localStorage.setItem !== "function"
  ) {
    return;
  }
  try {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } catch {}
}

function clearStoredRefreshToken(): void {
  if (
    typeof window === "undefined" ||
    typeof localStorage === "undefined" ||
    typeof localStorage.removeItem !== "function"
  ) {
    return;
  }
  try {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {}
}

// ---------------------------------------------------------------------------
// Context shape
// ---------------------------------------------------------------------------

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  /** Checkpoint 4: verify email using a 6-digit OTP (POST /auth/verify-email). */
  verifyEmailOtp: (data: VerifyEmailOtpRequest) => Promise<MessageResponse>;
  /** Checkpoint 4: request a new OTP for the given email (POST /auth/resend-otp). */
  resendOtp: (data: ResendOtpRequest) => Promise<MessageResponse>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  // Guard against concurrent initialisation (React StrictMode mounts twice)
  const initialising = useRef(false);

  /** Attempt to restore a session from a stored refresh token on app load. */
  const restoreSession = useCallback(async (): Promise<void> => {
    const storedRefresh = getStoredRefreshToken();
    if (!storedRefresh) return;

    try {
      // Exchange stored refresh token for a new access token
      const tokenData = await authRefresh({ refresh_token: storedRefresh });

      // Set in-memory access token — never log it
      setAccessToken(tokenData.access_token);
      setAuthToken(tokenData.access_token);

      // Load user identity from /auth/me (do not decode JWT client-side)
      const authUser = await getMe();
      setUser(authUser);
    } catch {
      // Refresh token is invalid or expired — clear stale state silently
      clearStoredRefreshToken();
      setAccessToken(null);
      setAuthToken(null);
      setUser(null);
    }
  }, []);

  // Run session restoration once on mount
  useEffect(() => {
    if (initialising.current) return;
    initialising.current = true;

    restoreSession().finally(() => {
      setIsLoading(false);
    });
  }, [restoreSession]);

  // ---------------------------------------------------------------------------
  // login
  // ---------------------------------------------------------------------------

  const login = useCallback(
    async ({ email, password }: LoginCredentials): Promise<void> => {
      const tokenData = await authLogin({ email, password });

      // Persist refresh token (localStorage — Phase 1 strategy)
      storeRefreshToken(tokenData.refresh_token);

      // Keep access token in memory only
      setAccessToken(tokenData.access_token);
      setAuthToken(tokenData.access_token);

      // Fetch and store authenticated user identity
      const authUser = await getMe();
      setUser(authUser);
    },
    []
  );

  // ---------------------------------------------------------------------------
  // logout
  // ---------------------------------------------------------------------------

  const logout = useCallback(async (): Promise<void> => {
    const storedRefresh = getStoredRefreshToken();

    // Attempt to revoke the refresh token on the backend
    if (storedRefresh) {
      try {
        await authLogout({ refresh_token: storedRefresh });
      } catch {
        // Remote logout failure is non-fatal — always clear local state
      }
    }

    // Clear all local auth state regardless of remote call result
    clearStoredRefreshToken();
    setAccessToken(null);
    setAuthToken(null);
    setUser(null);
  }, []);

  // ---------------------------------------------------------------------------
  // verifyEmailOtp (Checkpoint 4)
  // ---------------------------------------------------------------------------

  const verifyEmailOtp = useCallback(
    async (data: VerifyEmailOtpRequest): Promise<MessageResponse> => {
      return authVerifyEmailOtp(data);
    },
    []
  );

  // ---------------------------------------------------------------------------
  // resendOtp (Checkpoint 4)
  // ---------------------------------------------------------------------------

  const resendOtp = useCallback(
    async (data: ResendOtpRequest): Promise<MessageResponse> => {
      return authResendOtp(data);
    },
    []
  );

  // ---------------------------------------------------------------------------
  // Context value
  // ---------------------------------------------------------------------------

  const value: AuthContextValue = {
    user,
    isAuthenticated: user !== null,
    isLoading,
    login,
    logout,
    verifyEmailOtp,
    resendOtp,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// useAuth hook
// ---------------------------------------------------------------------------

/**
 * Access the authentication context.
 * Must be called inside an <AuthProvider> subtree.
 */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
