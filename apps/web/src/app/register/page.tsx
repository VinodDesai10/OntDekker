"use client";

/**
 * /register — Create Account Screen
 *
 * Backend contract (RegisterRequest): { email: string; password: string }
 * Password minimum: 8 characters (enforced by backend, validated client-side).
 * Password confirmation: UI-only — not sent to backend.
 *
 * After successful registration navigates to /verify-email?email=<encoded>
 * so the verify-email page can display which address the OTP was sent to.
 *
 * Does NOT call the auth service directly — uses register() from auth.ts
 * directly since AuthContext does not expose a register method (registration
 * is distinct from session management).
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { AuthCard } from "@/components/auth/AuthCard";
import { Button } from "@/components/ui/button";
import { register } from "@/services/auth";
import { ApiError } from "@/services/api";

export default function RegisterPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // Client-side validation
    if (!email.trim()) {
      setError("Email is required.");
      return;
    }
    if (!password) {
      setError("Password is required.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await register({ email: email.trim(), password });
      // Navigate to verify-email — pass the registered address so the page
      // can display it without needing global state.
      router.push(`/verify-email?email=${encodeURIComponent(email.trim())}`);
    } catch (err) {
      if (err instanceof ApiError) {
        // EMAIL_ALREADY_REGISTERED with is_verified=false: the backend already
        // resent the OTP.  Redirect to verification so the user can complete it.
        // EMAIL_ALREADY_REGISTERED with is_verified=true: the backend still
        // returns this code — redirect so the user sees a "already verified,
        // go to login" message rather than a hard stop here.
        if (err.code === "EMAIL_ALREADY_REGISTERED") {
          router.push(`/verify-email?email=${encodeURIComponent(email.trim())}`);
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
    <AuthCard
      title="Create account"
      description="Join OntDekker to discover and plan your next expedition."
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
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
          <label
            htmlFor="password"
            className="block text-sm font-medium text-[#111111]"
          >
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={submitting}
            placeholder="Min. 8 characters"
            className="w-full rounded-lg border border-[#EAE7DF] bg-white px-3.5 py-2.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
          />
        </div>

        {/* Confirm password — UI only, not sent to backend */}
        <div className="space-y-1.5">
          <label
            htmlFor="confirm-password"
            className="block text-sm font-medium text-[#111111]"
          >
            Confirm password
          </label>
          <input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            disabled={submitting}
            placeholder="Re-enter your password"
            className="w-full rounded-lg border border-[#EAE7DF] bg-white px-3.5 py-2.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
          />
        </div>

        {/* Submit */}
        <Button
          type="submit"
          disabled={submitting}
          className="w-full"
          size="lg"
        >
          {submitting ? (
            <>
              <Loader2 className="mr-2 size-4 animate-spin" aria-hidden />
              Creating account…
            </>
          ) : (
            "Create account"
          )}
        </Button>

        {/* Login link */}
        <p className="text-center text-sm text-gray-500">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-[#111111] underline-offset-4 hover:underline"
          >
            Sign in
          </Link>
        </p>
      </form>
    </AuthCard>
  );
}
