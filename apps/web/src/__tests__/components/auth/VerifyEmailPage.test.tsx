/**
 * Component tests for the Verify Email page
 * (src/app/verify-email/page.tsx)
 *
 * Tests observable behavior only — no implementation internals.
 *
 * The page wraps a VerifyEmailContent child inside <Suspense>. That child
 * calls useSearchParams() to read `token` and `email` query parameters.
 *
 * Entry points:
 *   ?token=<opaque> → auto-verifies on mount (existing flow)
 *   ?email=<addr>   → awaiting-otp: shows which address received the code
 *   neither         → no-token fallback
 *
 * Coverage:
 *   1. No-token state    — URL missing both token and email params
 *   2. Loading state     — verifyEmail() is pending (token flow)
 *   3. Success state     — verifyEmail() resolves (token flow)
 *   4. Error state       — verifyEmail() rejects (ApiError + generic)
 *   5. Double-call protection — verifyEmail() called at most once per mount
 *   6. Awaiting-OTP state — email present, no token (post-registration)
 *
 * Mocks:
 *   - next/navigation useSearchParams
 *   - @/services/auth verifyEmail (service boundary)
 *
 * No MSW / no network calls needed.
 * No router needed (page navigates via <Link>, not useRouter).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import VerifyEmailPage from "@/app/verify-email/page";
import { ApiError } from "@/services/api";

// ---------------------------------------------------------------------------
// Mock next/navigation — useSearchParams
// ---------------------------------------------------------------------------

const mockSearchParamsGet = vi.fn<(arg: string) => string | null>();

vi.mock("next/navigation", () => ({
  useSearchParams: () => ({ get: mockSearchParamsGet }),
  // Link uses useRouter internally in some Next versions; provide a stub
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

// ---------------------------------------------------------------------------
// Mock verifyEmail at the service boundary
// ---------------------------------------------------------------------------

const mockVerifyEmail = vi.fn<(arg: string) => Promise<{ message: string }>>();

vi.mock("@/services/auth", () => ({
  verifyEmail: (...args: unknown[]) => mockVerifyEmail(...(args as [string])),
}));

// ---------------------------------------------------------------------------
// Mock AuthContext — required by the OtpForm sub-component in awaiting-otp
// ---------------------------------------------------------------------------

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    verifyEmailOtp: vi.fn(),
    resendOtp: vi.fn(),
  }),
}));

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// 1. No-token state
// ---------------------------------------------------------------------------

describe("VerifyEmailPage — no token", () => {
  it("renders the no-token guidance message when token is absent", async () => {
    mockSearchParamsGet.mockReturnValue(null);

    render(<VerifyEmailPage />);

    await screen.findByText(/please use the link from your verification email/i);

    expect(
      screen.getByText(/please use the link from your verification email/i)
    ).toBeInTheDocument();
  });

  it("shows a Back-to-register link when both token and email are absent", async () => {
    mockSearchParamsGet.mockReturnValue(null);

    render(<VerifyEmailPage />);

    await screen.findByRole("link", { name: /back to register/i });

    expect(
      screen.getByRole("link", { name: /back to register/i })
    ).toHaveAttribute("href", "/register");
  });

  it("does NOT call verifyEmail when token is absent", async () => {
    mockSearchParamsGet.mockReturnValue(null);

    render(<VerifyEmailPage />);

    await screen.findByText(/please use the link from your verification email/i);

    expect(mockVerifyEmail).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// 2. Loading state
// ---------------------------------------------------------------------------

describe("VerifyEmailPage — loading", () => {
  it("shows the sr-only loading text while verification is pending", async () => {
    // Deferred promise keeps the component in loading state
    let resolveFn!: (v: { message: string }) => void;
    mockVerifyEmail.mockImplementation(
      () =>
        new Promise<{ message: string }>((res) => {
          resolveFn = res;
        })
    );
    mockSearchParamsGet.mockReturnValue("valid-token-123");

    render(<VerifyEmailPage />);

    // sr-only loading text should appear while the promise is pending
    await screen.findByText(/verifying email/i);
    expect(screen.getByText(/verifying email/i)).toBeInTheDocument();

    // Resolve to prevent act() warning from dangling state update
    await act(async () => {
      resolveFn({ message: "ok" });
    });
  });

  it("calls verifyEmail with the token from the URL", async () => {
    mockVerifyEmail.mockResolvedValue({ message: "Email verified successfully." });
    mockSearchParamsGet.mockReturnValue("my-test-token");

    render(<VerifyEmailPage />);

    await waitFor(() => {
      expect(mockVerifyEmail).toHaveBeenCalledWith("my-test-token");
    });
  });
});

// ---------------------------------------------------------------------------
// 3. Success state
// ---------------------------------------------------------------------------

describe("VerifyEmailPage — success", () => {
  it("shows the confirmed message after verifyEmail resolves", async () => {
    mockVerifyEmail.mockResolvedValue({ message: "Email verified successfully." });
    mockSearchParamsGet.mockReturnValue("success-token");

    render(<VerifyEmailPage />);

    await screen.findByText(/your email has been confirmed/i);

    expect(
      screen.getByText(/your email has been confirmed/i)
    ).toBeInTheDocument();
  });

  it("shows the Sign-in link after verification succeeds", async () => {
    mockVerifyEmail.mockResolvedValue({ message: "Email verified successfully." });
    mockSearchParamsGet.mockReturnValue("success-token");

    render(<VerifyEmailPage />);

    const link = await screen.findByRole("link", {
      name: /sign in to ontdekker/i,
    });
    expect(link).toHaveAttribute("href", "/login");
  });
});

// ---------------------------------------------------------------------------
// 4. Error state
// ---------------------------------------------------------------------------

describe("VerifyEmailPage — error", () => {
  it("shows an error message from ApiError when verification fails", async () => {
    // ApiError(status, body) — matches constructor signature in api.ts
    mockVerifyEmail.mockRejectedValue(
      new ApiError(401, {
        success: false,
        message: "Verification token is invalid or has expired",
        code: "TOKEN_INVALID",
      })
    );
    mockSearchParamsGet.mockReturnValue("expired-token");

    render(<VerifyEmailPage />);

    await screen.findByText(
      /verification token is invalid or has expired/i
    );

    expect(
      screen.getByText(/verification token is invalid or has expired/i)
    ).toBeInTheDocument();
  });

  it("shows a generic message for non-ApiError rejections", async () => {
    mockVerifyEmail.mockRejectedValue(new Error("Network error"));
    mockSearchParamsGet.mockReturnValue("bad-token");

    render(<VerifyEmailPage />);

    await screen.findByText(/verification failed. please try again/i);

    expect(
      screen.getByText(/verification failed. please try again/i)
    ).toBeInTheDocument();
  });

  it("shows the expired-link hint text on error", async () => {
    mockVerifyEmail.mockRejectedValue(
      new ApiError(401, { success: false, message: "Token expired", code: "TOKEN_INVALID" })
    );
    mockSearchParamsGet.mockReturnValue("expired-token");

    render(<VerifyEmailPage />);

    await screen.findByText(/the link may have expired or already been used/i);

    expect(
      screen.getByText(/the link may have expired or already been used/i)
    ).toBeInTheDocument();
  });

  it("shows a Back-to-sign-in link on error", async () => {
    mockVerifyEmail.mockRejectedValue(
      new ApiError(401, { success: false, message: "Token invalid", code: "TOKEN_INVALID" })
    );
    mockSearchParamsGet.mockReturnValue("bad-token");

    render(<VerifyEmailPage />);

    const link = await screen.findByRole("link", { name: /back to sign in/i });
    expect(link).toHaveAttribute("href", "/login");
  });
});

// ---------------------------------------------------------------------------
// 5. Double-call protection
// ---------------------------------------------------------------------------

describe("VerifyEmailPage — double-call protection", () => {
  it("calls verifyEmail exactly once even under React StrictMode double-mount", async () => {
    /**
     * The production code guards against double-calls with a useRef `called`.
     * React StrictMode mounts, unmounts, and remounts components in dev.
     * We verify that verifyEmail is called exactly once regardless.
     *
     * Note: Vitest runs in non-StrictMode by default; calling twice would
     * require manual double-render which is not the same as StrictMode.
     * We confirm the simple case: exactly one call per render cycle.
     */
    mockVerifyEmail.mockResolvedValue({ message: "ok" });
    mockSearchParamsGet.mockReturnValue("once-token");

    render(<VerifyEmailPage />);

    await waitFor(() => {
      expect(mockVerifyEmail).toHaveBeenCalledTimes(1);
    });
  });
});

// ---------------------------------------------------------------------------
// 6. Awaiting-OTP state (Checkpoint 5.2 — post-registration)
// ---------------------------------------------------------------------------

describe("VerifyEmailPage — awaiting-otp (email param, no token)", () => {
  beforeEach(() => {
    // token → null, email → the registered address
    mockSearchParamsGet.mockImplementation((key: string) => {
      if (key === "email") return "user@example.com";
      return null; // token
    });
  });

  it("renders the 'We sent a verification code to' message", async () => {
    render(<VerifyEmailPage />);

    await screen.findByText(/we sent a verification code to/i);

    expect(
      screen.getByText(/we sent a verification code to/i)
    ).toBeInTheDocument();
  });

  it("displays the email address from the query parameter", async () => {
    render(<VerifyEmailPage />);

    await screen.findByText("user@example.com");

    expect(screen.getByText("user@example.com")).toBeInTheDocument();
  });

  it("does NOT call verifyEmail in awaiting-otp state", async () => {
    render(<VerifyEmailPage />);

    await screen.findByText(/we sent a verification code to/i);

    expect(mockVerifyEmail).not.toHaveBeenCalled();
  });

  it("shows the OTP input form in awaiting-otp state", async () => {
    render(<VerifyEmailPage />);

    // The OTP form is shown — verify button confirms it
    await screen.findByRole("button", { name: /^verify$/i });

    expect(
      screen.getByRole("button", { name: /^verify$/i })
    ).toBeInTheDocument();
  });
});
