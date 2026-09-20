"use client";

/**
 * /verify-email — Email Verification Screen
 *
 * Handles two distinct entry points:
 *
 * 1. Opaque-token flow (existing)
 *    URL: /verify-email?token=<token>
 *    Backend: GET /auth/verify-email?token=<token>
 *    Auto-verifies on mount and shows success/error result.
 *
 * 2. OTP awaiting-verification flow (Checkpoint 5.3)
 *    URL: /verify-email?email=<encoded>
 *    Arrived here after successful registration.
 *    Displays the registered email and a 6-digit OTP input.
 *    On success, redirects to /login?verified=1 after ~1 second.
 *
 * States:
 *   - loading      : opaque-token verification in progress
 *   - success      : opaque-token verified — show confirmation + sign-in link
 *   - error        : opaque-token invalid/expired — show message + sign-in link
 *   - awaiting-otp : arrived from registration — OTP input form
 *   - no-token     : URL has neither token nor email — show fallback guidance
 *
 * useSearchParams() is isolated in a child component wrapped in Suspense,
 * as required by Next.js App Router for static page generation.
 *
 * Tokens are never logged.
 */

import { Suspense, useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Loader2,
  CheckCircle,
  AlertTriangle,
  Mail,
  ShieldCheck,
} from "lucide-react";
import { AuthCard } from "@/components/auth/AuthCard";
import { OtpInput } from "@/components/auth/OtpInput";
import { Button } from "@/components/ui/button";
import { verifyEmail } from "@/services/auth";
import { useAuth } from "@/contexts/AuthContext";
import { ApiError } from "@/services/api";

type VerifyState = "loading" | "success" | "error" | "awaiting-otp" | "no-token";

// ---------------------------------------------------------------------------
// OTP sub-form — rendered when state === "awaiting-otp"
// ---------------------------------------------------------------------------

interface OtpFormProps {
  email: string;
}

const RESEND_COOLDOWN_SECONDS = 30;

function OtpForm({ email }: OtpFormProps) {
  const router = useRouter();
  const { verifyEmailOtp, resendOtp } = useAuth();

  const [otp, setOtp] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [otpError, setOtpError] = useState<string | null>(null);
  const [otpSuccess, setOtpSuccess] = useState(false);

  // Resend state
  const [isResending, setIsResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [resendError, setResendError] = useState<string | null>(null);

  // Ref so the redirect timer is cleaned up on unmount
  const redirectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cooldownIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (redirectTimerRef.current) clearTimeout(redirectTimerRef.current);
      if (cooldownIntervalRef.current) clearInterval(cooldownIntervalRef.current);
    };
  }, []);

  async function handleResend() {
    setResendError(null);
    setResendSuccess(false);
    setIsResending(true);

    try {
      await resendOtp({ email });

      setResendSuccess(true);

      // Start 30-second cooldown
      setResendCooldown(RESEND_COOLDOWN_SECONDS);
      cooldownIntervalRef.current = setInterval(() => {
        setResendCooldown((prev) => {
          if (prev <= 1) {
            if (cooldownIntervalRef.current) {
              clearInterval(cooldownIntervalRef.current);
              cooldownIntervalRef.current = null;
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        // If already verified, redirect to login directly — no OTP needed.
        if (err.code === "ALREADY_VERIFIED") {
          router.replace("/login?verified=1");
          return;
        }
        setResendError(err.message);
      } else {
        setResendError("Something went wrong. Please try again.");
      }
    } finally {
      setIsResending(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (otp.length < 6) {
      setOtpError("Please enter all 6 digits.");
      return;
    }

    setOtpError(null);
    setIsSubmitting(true);

    try {
      await verifyEmailOtp({ email, otp });

      setOtpSuccess(true);

      // Redirect to /login?verified=1 after ~1 second
      redirectTimerRef.current = setTimeout(() => {
        router.replace("/login?verified=1");
      }, 1000);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        // If the email is already verified (e.g., verified in another tab),
        // redirect directly to login instead of showing an error.
        if (err.code === "ALREADY_VERIFIED") {
          router.replace("/login?verified=1");
          return;
        }
        setOtpError(err.message);
      } else {
        setOtpError("Something went wrong. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  // ---- Success state (post-submit) ----------------------------------------

  if (otpSuccess) {
    return (
      <div className="flex flex-col items-center gap-4 py-2 text-center">
        <CheckCircle
          className="size-10 text-[#0F5132]"
          aria-hidden
        />
        <p className="text-sm leading-relaxed text-gray-500">
          Email verified! Redirecting you to sign in…
        </p>
        <Loader2
          className="size-5 animate-spin text-gray-400"
          aria-hidden
        />
        <p className="sr-only" role="status">
          Verification successful. Redirecting…
        </p>
      </div>
    );
  }

  // ---- OTP entry form -------------------------------------------------------

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      aria-label="OTP verification form"
    >
      <div className="flex flex-col items-center gap-5">
        {/* Email address display */}
        <div className="text-center">
          <p className="text-sm text-gray-500">
            We sent a verification code to
          </p>
          <p className="mt-0.5 text-sm font-medium text-[#111111] break-all">
            {email}
          </p>
        </div>

        {/* OTP input */}
        <OtpInput
          value={otp}
          onChange={(val) => {
            setOtp(val);
            if (otpError) setOtpError(null);
          }}
          disabled={isSubmitting}
          hasError={!!otpError}
        />

        {/* Error message */}
        {otpError && (
          <p
            className="text-sm text-red-600 text-center"
            role="alert"
            aria-live="assertive"
          >
            {otpError}
          </p>
        )}

        {/* Submit button */}
        <Button
          type="submit"
          disabled={isSubmitting || otp.length < 6}
          aria-busy={isSubmitting}
          className="w-full h-10 bg-[#111111] text-white hover:bg-[#333333] rounded-lg text-sm font-medium disabled:opacity-50"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="size-4 animate-spin mr-2" aria-hidden />
              <span>Verifying…</span>
            </>
          ) : (
            "Verify"
          )}
        </Button>

        {/* Resend success message */}
        {resendSuccess && (
          <p
            className="text-sm text-green-700 text-center"
            role="status"
            aria-live="polite"
          >
            A new verification code has been sent.
          </p>
        )}

        {/* Resend error message */}
        {resendError && (
          <p
            className="text-sm text-red-600 text-center"
            role="alert"
            aria-live="assertive"
          >
            {resendError}
          </p>
        )}

        {/* Resend button */}
        <p className="text-sm text-gray-400">
          Didn&apos;t receive the code?{" "}
          <button
            type="button"
            onClick={handleResend}
            disabled={isResending || resendCooldown > 0}
            aria-disabled={isResending || resendCooldown > 0}
            aria-busy={isResending}
            className="text-[#111111] underline underline-offset-4 hover:text-[#333333] disabled:text-gray-400 disabled:no-underline disabled:cursor-not-allowed"
          >
            {isResending
              ? "Sending…"
              : resendCooldown > 0
              ? `Resend code (${resendCooldown}s)`
              : "Resend code"}
          </button>
        </p>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Main content — reads URL params and branches on state
// ---------------------------------------------------------------------------

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const email = searchParams.get("email");

  const initialState: VerifyState = token
    ? "loading"
    : email
    ? "awaiting-otp"
    : "no-token";

  const [state, setState] = useState<VerifyState>(initialState);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const called = useRef(false);

  useEffect(() => {
    if (!token || called.current) return;
    called.current = true;

    verifyEmail(token)
      .then(() => setState("success"))
      .catch((err: unknown) => {
        if (err instanceof ApiError) {
          setErrorMessage(err.message);
        } else {
          setErrorMessage("Verification failed. Please try again.");
        }
        setState("error");
      });
  }, [token]);

  // ---- loading ---------------------------------------------------------------

  if (state === "loading") {
    return (
      <div className="flex flex-col items-center gap-4 py-4">
        <Loader2 className="size-8 animate-spin text-gray-400" aria-hidden />
        <p className="sr-only">Verifying email…</p>
      </div>
    );
  }

  // ---- token success ---------------------------------------------------------

  if (state === "success") {
    return (
      <div className="flex flex-col items-center gap-4 py-2 text-center">
        <CheckCircle className="size-10 text-[#0F5132]" aria-hidden />
        <p className="text-sm leading-relaxed text-gray-500">
          Your email has been confirmed. Your account is now active.
        </p>
        <Link
          href="/login"
          className="text-sm font-medium text-[#111111] underline-offset-4 hover:underline"
        >
          Sign in to OntDekker
        </Link>
      </div>
    );
  }

  // ---- token error -----------------------------------------------------------

  if (state === "error") {
    return (
      <div className="flex flex-col items-center gap-4 py-2 text-center">
        <AlertTriangle className="size-10 text-[#F59E0B]" aria-hidden />
        {errorMessage && (
          <p className="text-sm leading-relaxed text-gray-500">
            {errorMessage}
          </p>
        )}
        <p className="text-sm text-gray-400">
          The link may have expired or already been used.
        </p>
        <Link
          href="/login"
          className="text-sm font-medium text-[#111111] underline-offset-4 hover:underline"
        >
          Back to sign in
        </Link>
      </div>
    );
  }

  // ---- awaiting-otp ----------------------------------------------------------

  if (state === "awaiting-otp" && email) {
    return <OtpForm email={email} />;
  }

  // ---- no-token --------------------------------------------------------------

  return (
    <div className="flex flex-col items-center gap-4 py-2 text-center">
      <AlertTriangle className="size-10 text-[#F59E0B]" aria-hidden />
      <p className="text-sm leading-relaxed text-gray-500">
        Please use the link from your verification email.
      </p>
      <Link
        href="/register"
        className="text-sm font-medium text-[#111111] underline-offset-4 hover:underline"
      >
        Back to register
      </Link>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page export
// ---------------------------------------------------------------------------

export default function VerifyEmailPage() {
  return (
    <AuthCard
      title="Verify your email"
      description="Enter the 6-digit code we sent to your inbox."
    >
      <Suspense
        fallback={
          <div className="flex justify-center py-4">
            <Loader2
              className="size-8 animate-spin text-gray-400"
              aria-hidden
            />
          </div>
        }
      >
        <VerifyEmailContent />
      </Suspense>
    </AuthCard>
  );
}
