"use client";

/**
 * /login — Sign In Screen
 *
 * Uses AuthContext.login() — does not make direct API calls.
 *
 * After successful login:
 *   - Reads `redirect` query parameter set by ProtectedRoute.
 *   - Validates the redirect is a safe internal path (starts with /).
 *   - Falls back to / if the redirect is absent or unsafe.
 *
 * useSearchParams() is isolated in a child component wrapped in Suspense,
 * as required by Next.js App Router for static page generation.
 *
 * Backend contract: email + password via auth service login().
 * Errors are displayed from normalized ApiError.message.
 */

import { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { AuthCard } from "@/components/auth/AuthCard";
import { useAuth } from "@/contexts/AuthContext";
import { ApiError } from "@/services/api";

/** Only allow redirects to same-origin relative paths, defaulting to /feed. */
function getSafeRedirect(raw: string | null): string {
  if (!raw) return "/feed";
  const decoded = decodeURIComponent(raw);
  // Must be a relative path starting with / and not // or /
  if (
    decoded.startsWith("/") &&
    !decoded.startsWith("//") &&
    decoded !== "/"
  ) {
    return decoded;
  }
  return "/feed";
}

function LoginForm() {
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const justRegistered = searchParams.get("registered") === "1";
  const justVerified = searchParams.get("verified") === "1";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Redirect already-authenticated users away from the login screen.
  // Exception: skip the redirect when ?verified=1 is present — the user
  // was sent here intentionally after OTP verification and must be allowed
  // to sign in even if a prior session is still active in localStorage.
  useEffect(() => {
    if (!authLoading && isAuthenticated && !justVerified) {
      const redirectTo = getSafeRedirect(searchParams.get("redirect"));
      router.replace(redirectTo);
    }
  }, [isAuthenticated, authLoading, router, searchParams, justVerified]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError("Email is required.");
      return;
    }
    if (!password) {
      setError("Password is required.");
      return;
    }

    setSubmitting(true);
    try {
      await login({ email: email.trim(), password });
      const redirectTo = getSafeRedirect(searchParams.get("redirect"));
      router.replace(redirectTo);
    } catch (err) {
      if (err instanceof ApiError) {
        // Email not verified — send the user to the verification screen so
        // they can enter their OTP. This is not a login failure; it is an
        // expected state for newly registered accounts.
        if (err.code === "EMAIL_NOT_VERIFIED") {
          router.replace(
            `/verify-email?email=${encodeURIComponent(email.trim())}`
          );
          return;
        }
        setError(err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      {/* Post-registration success banner */}
      {justRegistered && !error && (
        <div
          role="status"
          className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-[#0F5132]"
        >
          Account created. Sign in to continue.
        </div>
      )}

      {/* Post-verification success banner */}
      {justVerified && !justRegistered && !error && (
        <div
          role="status"
          className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-[#0F5132]"
        >
          Email verified. Sign in to continue.
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      {/* Email */}
      <div className="space-y-1.5">
        <label
          htmlFor="email"
          className="block text-sm font-medium text-[#111111]"
        >
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={submitting}
          placeholder="you@example.com"
          className="w-full rounded-lg border border-[#EAE7DF] bg-white px-3.5 py-2.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
        />
      </div>

      {/* Password */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label
            htmlFor="password"
            className="block text-sm font-medium text-[#111111]"
          >
            Password
          </label>
          <Link
            href="/forgot-password"
            className="text-sm text-gray-500 underline-offset-4 hover:underline"
          >
            Forgot password?
          </Link>
        </div>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={submitting}
          placeholder="••••••••"
          className="w-full rounded-lg border border-[#EAE7DF] bg-white px-3.5 py-2.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
        />
      </div>

      {/* Submit — uses a native <button type="submit"> so the form's onSubmit fires.
           The @base-ui/react Button primitive hardcodes type="button" on native buttons
           and cannot be overridden by the caller's type prop. */}
      <button
        type="submit"
        disabled={submitting}
        className={[
          "w-full inline-flex items-center justify-center gap-2",
          "h-10 rounded-lg px-4 text-sm font-medium",
          "bg-[#111111] text-white transition-colors",
          "hover:bg-[#333333] focus-visible:outline focus-visible:outline-2",
          "focus-visible:outline-offset-2 focus-visible:outline-[#111111]",
          "disabled:pointer-events-none disabled:opacity-50",
        ].join(" ")}
      >
        {submitting ? (
          <>
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Signing in…
          </>
        ) : (
          "Sign in"
        )}
      </button>

      {/* Register link */}
      <p className="text-center text-sm text-gray-500">
        Don&apos;t have an account?{" "}
        <Link
          href="/register"
          className="font-medium text-[#111111] underline-offset-4 hover:underline"
        >
          Create one
        </Link>
      </p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <AuthCard
      title="Sign in"
      description="Welcome back. Enter your credentials to continue."
    >
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </AuthCard>
  );
}
