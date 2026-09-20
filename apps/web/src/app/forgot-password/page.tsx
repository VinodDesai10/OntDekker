"use client";

/**
 * /forgot-password — Request Password Reset Screen
 *
 * Uses forgotPassword() from auth.ts.
 *
 * Backend always returns 200 regardless of whether the email exists —
 * this prevents account enumeration. The UI reflects this: after submit
 * it shows a safe success confirmation without revealing account existence.
 *
 * Phase 1 note: email delivery is not yet implemented in the backend.
 * The token is generated and persisted; delivery is Phase 2.
 */

import { useState } from "react";
import Link from "next/link";
import { Loader2, CheckCircle } from "lucide-react";
import { AuthCard } from "@/components/auth/AuthCard";
import { Button } from "@/components/ui/button";
import { forgotPassword } from "@/services/auth";
import { ApiError } from "@/services/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError("Email is required.");
      return;
    }

    setSubmitting(true);
    try {
      await forgotPassword({ email: email.trim() });
      setSubmitted(true);
    } catch (err) {
      // Surface genuine transport/server errors; suppress enumeration-risk errors
      if (err instanceof ApiError && err.status >= 500) {
        setError("Something went wrong. Please try again later.");
      } else if (err instanceof ApiError) {
        // Backend returns 200 for all cases; any error here is unexpected
        setError(err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <AuthCard
        title="Check your inbox"
        description="If an account with that email exists, you'll receive a password reset link shortly."
      >
        <div className="flex flex-col items-center gap-4 py-2 text-center">
          <CheckCircle
            className="size-10 text-[#0F5132]"
            aria-hidden
          />
          <p className="text-sm leading-relaxed text-gray-500">
            Didn&apos;t receive anything?{" "}
            <button
              type="button"
              onClick={() => {
                setSubmitted(false);
                setEmail("");
              }}
              className="font-medium text-[#111111] underline-offset-4 hover:underline"
            >
              Try again
            </button>
          </p>
          <Link
            href="/login"
            className="text-sm font-medium text-[#111111] underline-offset-4 hover:underline"
          >
            Back to sign in
          </Link>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Reset your password"
      description="Enter your email and we'll send you a reset link."
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
              Sending reset link…
            </>
          ) : (
            "Send reset link"
          )}
        </Button>

        {/* Back to login */}
        <p className="text-center text-sm text-gray-500">
          <Link
            href="/login"
            className="font-medium text-[#111111] underline-offset-4 hover:underline"
          >
            Back to sign in
          </Link>
        </p>
      </form>
    </AuthCard>
  );
}
