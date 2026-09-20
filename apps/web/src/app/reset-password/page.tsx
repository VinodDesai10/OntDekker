"use client";

/**
 * /reset-password — Reset Password Screen
 *
 * Backend contract (ResetPasswordRequest): { token: string; new_password: string }
 *
 * Token is received as the `token` query parameter in the URL.
 *
 * Behavior:
 *   - If no token in URL: show an error state with a link back to forgot-password.
 *   - While submitting: loading state on button.
 *   - On success: show success confirmation, navigate to /login after 3 seconds.
 *   - On backend error: display the normalized error message.
 *
 * useSearchParams() is isolated in a child component wrapped in Suspense,
 * as required by Next.js App Router for static page generation.
 *
 * Tokens are never logged.
 */

import { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Loader2, CheckCircle, AlertTriangle } from "lucide-react";
import { AuthCard } from "@/components/auth/AuthCard";
import { Button } from "@/components/ui/button";
import { resetPassword } from "@/services/auth";
import { ApiError } from "@/services/api";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Auto-redirect to login after successful reset
  useEffect(() => {
    if (!success) return;
    const timer = setTimeout(() => router.replace("/login"), 3000);
    return () => clearTimeout(timer);
  }, [success, router]);

  // No token in URL — cannot proceed
  if (!token) {
    return (
      <div className="flex flex-col items-center gap-4 py-2 text-center">
        <AlertTriangle className="size-10 text-[#F59E0B]" aria-hidden />
        <p className="text-sm leading-relaxed text-gray-500">
          This password reset link is missing or malformed. Request a new one.
        </p>
        <Link
          href="/forgot-password"
          className="text-sm font-medium text-[#111111] underline-offset-4 hover:underline"
        >
          Request a new link
        </Link>
      </div>
    );
  }

  if (success) {
    return (
      <div className="flex flex-col items-center gap-4 py-2 text-center">
        <CheckCircle className="size-10 text-[#0F5132]" aria-hidden />
        <p className="text-sm leading-relaxed text-gray-500">
          Your password has been changed. Redirecting to sign in…
        </p>
        <Link
          href="/login"
          className="text-sm font-medium text-[#111111] underline-offset-4 hover:underline"
        >
          Sign in now
        </Link>
      </div>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!newPassword) {
      setError("New password is required.");
      return;
    }
    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      // token is confirmed non-null above; never logged
      await resetPassword({ token: token!, new_password: newPassword });
      setSuccess(true);
    } catch (err) {
      if (err instanceof ApiError) {
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
      {/* Error banner */}
      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      {/* New password */}
      <div className="space-y-1.5">
        <label
          htmlFor="new-password"
          className="block text-sm font-medium text-[#111111]"
        >
          New password
        </label>
        <input
          id="new-password"
          type="password"
          autoComplete="new-password"
          required
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          disabled={submitting}
          placeholder="Min. 8 characters"
          className="w-full rounded-lg border border-[#EAE7DF] bg-white px-3.5 py-2.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
        />
      </div>

      {/* Confirm password */}
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
            Updating password…
          </>
        ) : (
          "Update password"
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
  );
}

export default function ResetPasswordPage() {
  return (
    <AuthCard
      title="Set new password"
      description="Choose a strong password for your account."
    >
      <Suspense fallback={null}>
        <ResetPasswordForm />
      </Suspense>
    </AuthCard>
  );
}
