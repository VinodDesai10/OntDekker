"use client";

/**
 * OntDekker Frontend — Protected Route Guard
 *
 * Wraps any subtree that requires an authenticated session.
 * Uses AuthContext state — does NOT attempt server-side JWT validation
 * (access token is in-memory only; Next.js middleware cannot access it).
 *
 * Behavior:
 *   - While session restoration is in progress (isLoading=true):
 *       Renders a minimal, non-product loading state.
 *       Does NOT redirect — the session may still be successfully restored.
 *
 *   - When session restoration is complete and user is NOT authenticated:
 *       Redirects to /login, preserving the originally requested path as
 *       the `redirect` query parameter so the login screen can return the
 *       user after successful authentication.
 *
 *   - When authenticated:
 *       Renders children normally.
 *
 * Redirect loop prevention:
 *   - The /login route must NOT be wrapped by ProtectedRoute.
 *     Login and other auth screens are public by default.
 *
 * Usage:
 *   // In a layout or page that requires authentication:
 *   <ProtectedRoute>
 *     <DashboardPage />
 *   </ProtectedRoute>
 */

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Do not redirect while session restoration is still in progress.
    // Redirecting during load would break users whose refresh token is valid.
    if (isLoading) return;

    if (!isAuthenticated) {
      // Preserve the intended destination as a query parameter so the login
      // screen can redirect back after a successful login.
      const returnTo = encodeURIComponent(pathname ?? "/");
      router.replace(`/login?redirect=${returnTo}`);
    }
  }, [isAuthenticated, isLoading, router, pathname]);

  // While loading: render a minimal, non-product placeholder.
  // This is intentionally blank — a product-level loading skeleton belongs
  // to the authenticated layout (Checkpoint 6D+), not this guard.
  if (isLoading) {
    return (
      <div
        aria-label="Loading session"
        aria-live="polite"
        className="flex min-h-screen items-center justify-center"
      >
        <span className="sr-only">Loading…</span>
      </div>
    );
  }

  // While redirect is pending (user is not authenticated), render nothing.
  // The useEffect above triggers the navigation; avoid flashing protected content.
  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
