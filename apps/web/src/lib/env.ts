/**
 * OntDekker Frontend — Environment Configuration
 *
 * Reads NEXT_PUBLIC_* environment variables and exports typed API base URLs.
 *
 * Responsibilities:
 *   - Provide typed access to public environment variables.
 *   - Expose development-safe defaults for local direct-port routing.
 *   - Surface misconfiguration errors at module load time (not silently at runtime).
 *
 * Does NOT:
 *   - Create Axios instances (see src/services/axios.ts — future checkpoint)
 *   - Make API calls
 *   - Store or handle tokens
 *   - Expose backend secrets
 *
 * Routing strategy:
 *   Phase 1 (local development): direct service ports, no Traefik.
 *   Phase 2+: Traefik gateway paths (/api/v1/authentication, /api/v1/user).
 */

const AUTH_API_URL =
  process.env.NEXT_PUBLIC_AUTH_API_URL ?? "http://localhost:8000";

const USER_API_URL =
  process.env.NEXT_PUBLIC_USER_API_URL ?? "http://localhost:8001";

export const env = {
  /**
   * Base URL for the Authentication Service.
   * e.g. http://localhost:8000 (local dev) or /api/v1/authentication (Traefik)
   */
  AUTH_API_URL,

  /**
   * Base URL for the User Service.
   * e.g. http://localhost:8001 (local dev) or /api/v1/user (Traefik)
   */
  USER_API_URL,
} as const;
