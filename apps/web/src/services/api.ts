/**
 * OntDekker Frontend — API Transport Layer
 *
 * Provides configured Axios instances for each backend service.
 * This layer is transport-only: no endpoint-specific business methods here.
 *
 * Architecture:
 *   AuthContext (future) → calls setAccessToken() → interceptor attaches header
 *
 * Does NOT:
 *   - Implement endpoint-specific API functions (login, register, getProfile…)
 *   - Store tokens in browser storage
 *   - Implement automatic token refresh on 401
 *   - Import React or AuthContext (avoids circular dependencies)
 *   - Log Authorization headers or token values
 */

import axios, { AxiosError, AxiosInstance } from "axios";
import { env } from "@/lib/env";

// ---------------------------------------------------------------------------
// Backend error envelope
// Matches the shared OntDekkerException response contract in shared/exceptions.py
// ---------------------------------------------------------------------------

export interface ApiErrorBody {
  success: false;
  message: string;
  code: string;
  details?: unknown;
}

export class ApiError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly details: unknown;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.details = body.details;
  }
}

/**
 * Convert an AxiosError into a typed ApiError when the backend returned
 * the documented { success, message, code, details } envelope,
 * or re-throw as-is for network/non-API errors.
 */
export function normalizeError(error: unknown): never {
  if (error instanceof AxiosError && error.response) {
    const body = error.response.data as Partial<ApiErrorBody>;
    if (typeof body?.message === "string" && typeof body?.code === "string") {
      throw new ApiError(error.response.status, {
        success: false,
        message: body.message,
        code: body.code,
        details: body.details,
      });
    }
    // Non-standard error body — wrap with HTTP status info
    throw new ApiError(error.response.status, {
      success: false,
      message: error.message,
      code: `HTTP_${error.response.status}`,
    });
  }
  // Network error or non-Axios error — re-throw unchanged
  throw error;
}

// ---------------------------------------------------------------------------
// In-memory access token accessor
//
// Keeps the transport layer decoupled from React/AuthContext.
// AuthContext will call setAccessToken() after login and clear it on logout.
// The interceptor reads it here without importing AuthContext.
//
// This value NEVER touches localStorage or sessionStorage.
// Refresh-token logic is NOT implemented here — that belongs in AuthContext.
// ---------------------------------------------------------------------------

let _accessToken: string | null = null;

/** Called by AuthContext after a successful login or token refresh. */
export function setAccessToken(token: string | null): void {
  _accessToken = token;
}

/** Returns the current in-memory access token (may be null). */
export function getAccessToken(): string | null {
  return _accessToken;
}

// ---------------------------------------------------------------------------
// Axios instance factory
// ---------------------------------------------------------------------------

function createInstance(baseURL: string): AxiosInstance {
  const instance = axios.create({
    baseURL,
    headers: { "Content-Type": "application/json" },
    timeout: 10_000,
  });

  // Request interceptor: attach Bearer token when available
  instance.interceptors.request.use((config) => {
    const token = getAccessToken();
    if (token) {
      // Token is attached but never logged
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // Response interceptor: normalize backend error envelope on failure
  instance.interceptors.response.use(
    (response) => response,
    (error: unknown) => normalizeError(error)
  );

  return instance;
}

// ---------------------------------------------------------------------------
// Named Axios instances
// ---------------------------------------------------------------------------

/** Axios instance pre-configured for the Authentication Service. */
export const authHttp = createInstance(env.AUTH_API_URL);

/** Axios instance pre-configured for the User Service. */
export const userHttp = createInstance(env.USER_API_URL);
