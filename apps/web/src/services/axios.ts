/**
 * OntDekker Axios Client
 *
 * Single shared Axios instance used by every API function in api.ts.
 * Never import Axios directly in components or views — always go through
 * this module or the useApi() hook.
 *
 * Configuration:
 *   baseURL   : NEXT_PUBLIC_API_BASE_URL (env) or "" (relative URLs — dev default)
 *   timeout   : 15 000 ms
 *   headers   : Content-Type: application/json
 *
 * Request interceptor:
 *   Attaches Authorization: Bearer <token> when a token is present.
 *   The token is injected via setAuthToken() — called from AppStateProvider
 *   whenever the auth state changes.
 *
 * Response interceptors:
 *   1. Success: recursively converts snake_case keys to camelCase so all
 *      response objects match the TypeScript type definitions.
 *   2. Error: normalises all error responses into ApiError shape:
 *        { detail: string; status: number }
 *      Re-throws as a plain Error with a `status` property so callers
 *      can distinguish HTTP errors from network errors.
 *
 * 401 handling:
 *   Dispatches a SIGN_OUT action by invoking the registered onUnauthorized
 *   callback. This is wired up in AppStateProvider.
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";
import type { ApiError } from "@/types";

// ---------------------------------------------------------------------------
// Base URL — reads from Next.js public env var
//
// Falls back to "" (empty string) so Axios uses relative URLs when
// NEXT_PUBLIC_API_BASE_URL is not set (e.g. a fresh clone with no
// .env.local).  Relative URLs work correctly in both environments:
//
//   Browser  → relative paths hit the same origin (http://localhost:3000),
//              and Next.js rewrite rules proxy /guides/api/* and
//              /expeditions/api/* to the backend services.
//
//   SSR      → Next.js rewrites also apply on the server side, so the
//              server-rendered requests go through the same proxy rules.
//
// When NEXT_PUBLIC_API_BASE_URL is explicitly set (e.g. in production to
// the Traefik gateway domain) that value is used instead.
// ---------------------------------------------------------------------------

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 15_000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ---------------------------------------------------------------------------
// Auth token management
// ---------------------------------------------------------------------------

/** Current JWT access token — set by AppStateProvider on auth change */
let _authToken: string | null = null;

/** Register / clear the token used by the request interceptor */
export function setAuthToken(token: string | null): void {
  _authToken = token;
}

/** Retrieve the current token (read-only) */
export function getAuthToken(): string | null {
  return _authToken;
}

// ---------------------------------------------------------------------------
// Unauthorised callback — wired up in AppStateProvider
// ---------------------------------------------------------------------------

let _onUnauthorized: (() => void) | null = null;

export function registerUnauthorizedHandler(handler: () => void): void {
  _onUnauthorized = handler;
}

// ---------------------------------------------------------------------------
// Key transformer — snake_case → camelCase
// ---------------------------------------------------------------------------

/**
 * Converts a single snake_case string to camelCase.
 * "profile_image_url" → "profileImageUrl"
 */
function toCamel(s: string): string {
  return s.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
}

/**
 * Recursively converts all object keys from snake_case to camelCase.
 * Arrays are walked element-by-element; primitives are returned as-is.
 */
function keysToCamel(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(keysToCamel);
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([k, v]) => [
        toCamel(k),
        keysToCamel(v),
      ]),
    );
  }
  return value;
}

// ---------------------------------------------------------------------------
// Request interceptor — inject Bearer token
// ---------------------------------------------------------------------------

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (_authToken) {
      config.headers.Authorization = `Bearer ${_authToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ---------------------------------------------------------------------------
// Response interceptor — camelCase transform + normalise errors
// ---------------------------------------------------------------------------

apiClient.interceptors.response.use(
  (response) => {
    // Transform all response data keys from snake_case to camelCase
    response.data = keysToCamel(response.data);
    return response;
  },
  (error: AxiosError<ApiError>) => {
    const status = error.response?.status ?? 0;
    const detail =
      error.response?.data?.detail ??
      error.message ??
      "An unexpected error occurred.";

    // Trigger sign-out on 401 Unauthorized
    if (status === 401 && _onUnauthorized) {
      _onUnauthorized();
    }

    // Produce a normalised error object
    const normalised = new Error(detail) as Error & { status: number; detail: string };
    normalised.status = status;
    normalised.detail = detail;
    return Promise.reject(normalised);
  },
);

export default apiClient;
