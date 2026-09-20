/**
 * Component tests for the Reset Password page
 * (src/app/reset-password/page.tsx)
 *
 * Tests observable behavior only — no implementation internals.
 *
 * ResetPasswordPage renders ResetPasswordForm inside <Suspense>.
 * ResetPasswordForm calls resetPassword() from @/services/auth directly.
 * Token comes from useSearchParams().get("token").
 * On success, useEffect schedules a delayed router.replace("/login") after 3s.
 *
 * Mock boundaries:
 *   - resetPassword() at @/services/auth
 *   - useSearchParams/useRouter at next/navigation
 *
 * Fake timers are used only where necessary for the delayed redirect test.
 * Real timers are restored immediately after each fake-timer test.
 *
 * Coverage:
 *   1. Missing-token state
 *   2. Rendering with valid token
 *   3. Validation
 *   4. Successful reset (including delayed redirect with fake timers)
 *   5. Failure behavior
 *   6. Pending / loading state
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ResetPasswordPage from "@/app/reset-password/page";
import { ApiError } from "@/services/api";

// ---------------------------------------------------------------------------
// Mock next/navigation
// ---------------------------------------------------------------------------

const mockReplace = vi.fn();
const mockSearchParamsGet = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  useSearchParams: () => ({ get: mockSearchParamsGet }),
}));

// ---------------------------------------------------------------------------
// Mock resetPassword() at the service boundary
// ---------------------------------------------------------------------------

const mockResetPassword = vi.fn();

vi.mock("@/services/auth", () => ({
  resetPassword: (...args: unknown[]) => mockResetPassword(...args),
}));

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  // Default: no token, no params
  mockSearchParamsGet.mockReturnValue(null);
});

// ---------------------------------------------------------------------------
// 1. Missing-token state
// ---------------------------------------------------------------------------

describe("ResetPasswordPage — missing token", () => {
  it("shows the missing/malformed-link error state when token param is absent", () => {
    mockSearchParamsGet.mockReturnValue(null);
    render(<ResetPasswordPage />);

    expect(
      screen.getByText(/password reset link is missing or malformed/i)
    ).toBeInTheDocument();
  });

  it("renders a link to request a new link at /forgot-password", () => {
    mockSearchParamsGet.mockReturnValue(null);
    render(<ResetPasswordPage />);

    const link = screen.getByRole("link", { name: /request a new link/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/forgot-password");
  });

  it("does not render the password inputs when token is missing", () => {
    mockSearchParamsGet.mockReturnValue(null);
    render(<ResetPasswordPage />);

    expect(screen.queryByLabelText(/new password/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/confirm password/i)).not.toBeInTheDocument();
  });

  it("does not call resetPassword() when token is absent", async () => {
    mockSearchParamsGet.mockReturnValue(null);
    render(<ResetPasswordPage />);

    // No submit button is rendered; verify resetPassword never called
    await waitFor(() => {
      expect(mockResetPassword).not.toHaveBeenCalled();
    });
  });
});

// ---------------------------------------------------------------------------
// 2. Rendering with valid token
// ---------------------------------------------------------------------------

describe("ResetPasswordPage — rendering with valid token", () => {
  beforeEach(() => {
    mockSearchParamsGet.mockImplementation((key: string) =>
      key === "token" ? "valid-reset-token-abc123" : null
    );
  });

  it("renders the new password input", () => {
    render(<ResetPasswordPage />);
    expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
  });

  it("renders the confirm password input", () => {
    render(<ResetPasswordPage />);
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
  });

  it("renders the 'Update password' submit button", () => {
    render(<ResetPasswordPage />);
    expect(
      screen.getByRole("button", { name: /update password/i })
    ).toBeInTheDocument();
  });

  it("renders a 'Back to sign in' link", () => {
    render(<ResetPasswordPage />);
    const link = screen.getByRole("link", { name: /back to sign in/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/login");
  });
});

// ---------------------------------------------------------------------------
// 3. Validation
// ---------------------------------------------------------------------------

describe("ResetPasswordPage — validation", () => {
  beforeEach(() => {
    mockSearchParamsGet.mockImplementation((key: string) =>
      key === "token" ? "valid-reset-token-abc123" : null
    );
  });

  it("shows 'New password is required.' when submitted with empty password", async () => {
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.click(screen.getByRole("button", { name: /update password/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "New password is required."
    );
    expect(mockResetPassword).not.toHaveBeenCalled();
  });

  it("shows 'Password must be at least 8 characters.' for a short password", async () => {
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "short");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Password must be at least 8 characters."
    );
    expect(mockResetPassword).not.toHaveBeenCalled();
  });

  it("shows 'Passwords do not match.' when confirm password differs", async () => {
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "validpass1");
    await user.type(screen.getByLabelText(/confirm password/i), "different99");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Passwords do not match."
    );
    expect(mockResetPassword).not.toHaveBeenCalled();
  });

  it("accepts exactly 8 characters as a valid minimum password length", async () => {
    mockResetPassword.mockResolvedValue({
      message: "Password has been reset successfully.",
    });
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "exactly8");
    await user.type(screen.getByLabelText(/confirm password/i), "exactly8");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    await waitFor(() => {
      expect(mockResetPassword).toHaveBeenCalledOnce();
    });
    // No validation error should be shown
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("does not call resetPassword() when validation fails", async () => {
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    // Submit completely empty
    await user.click(screen.getByRole("button", { name: /update password/i }));

    await screen.findByRole("alert");
    expect(mockResetPassword).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// 4. Successful reset
// ---------------------------------------------------------------------------

describe("ResetPasswordPage — successful reset", () => {
  beforeEach(() => {
    mockSearchParamsGet.mockImplementation((key: string) =>
      key === "token" ? "valid-reset-token-abc123" : null
    );
    mockResetPassword.mockResolvedValue({
      message: "Password has been reset successfully.",
    });
  });

  it("calls resetPassword() with token and new_password — NOT confirmPassword", async () => {
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "newsecure1");
    await user.type(screen.getByLabelText(/confirm password/i), "newsecure1");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    await waitFor(() => {
      expect(mockResetPassword).toHaveBeenCalledWith({
        token: "valid-reset-token-abc123",
        new_password: "newsecure1",
      });
    });
  });

  it("does not include confirmPassword in the resetPassword() call", async () => {
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "newsecure1");
    await user.type(screen.getByLabelText(/confirm password/i), "newsecure1");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    await waitFor(() => {
      expect(mockResetPassword).toHaveBeenCalledWith(
        expect.not.objectContaining({ confirmPassword: expect.anything() })
      );
    });
  });

  it("shows the success confirmation after successful reset", async () => {
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "newsecure1");
    await user.type(screen.getByLabelText(/confirm password/i), "newsecure1");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    expect(
      await screen.findByText(/your password has been changed/i)
    ).toBeInTheDocument();
  });

  it("renders a 'Sign in now' link in the success state", async () => {
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "newsecure1");
    await user.type(screen.getByLabelText(/confirm password/i), "newsecure1");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    const link = await screen.findByRole("link", { name: /sign in now/i });
    expect(link).toHaveAttribute("href", "/login");
  });

  it("navigates to /login after 3 seconds using fake timers", async () => {
    // Use vi.useFakeTimers() before rendering so the useEffect's setTimeout
    // is registered against fake timers. Use fireEvent (no internal delays)
    // for interactions so fake timers don't block the test.
    vi.useFakeTimers();

    const { fireEvent } = await import("@testing-library/react");

    render(<ResetPasswordPage />);

    // Fill fields with fireEvent — no internal timer delays
    fireEvent.change(screen.getByLabelText(/new password/i), {
      target: { value: "newsecure1" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "newsecure1" },
    });

    // Submit the form
    await act(async () => {
      fireEvent.submit(screen.getByRole("button", { name: /update password/i }).closest("form")!);
    });

    // mockResetPassword is already resolved synchronously from beforeEach
    // Flush effects that set success=true
    await act(async () => {
      await Promise.resolve();
    });

    // The success state should now be visible
    expect(screen.getByText(/your password has been changed/i)).toBeInTheDocument();

    // Verify no premature navigation
    expect(mockReplace).not.toHaveBeenCalled();

    // Advance time by 3 seconds and flush the timer callback + effects
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    expect(mockReplace).toHaveBeenCalledWith("/login");

    vi.useRealTimers();
  });

  it("does not navigate before the 3-second delay elapses", async () => {
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "newsecure1");
    await user.type(screen.getByLabelText(/confirm password/i), "newsecure1");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    await screen.findByText(/your password has been changed/i);

    vi.useFakeTimers();

    // Advance time by only 2.9 seconds — still before the redirect
    vi.advanceTimersByTime(2900);

    // Should still not have called replace
    expect(mockReplace).not.toHaveBeenCalled();

    vi.useRealTimers();
  });
});

// ---------------------------------------------------------------------------
// 5. Failure behavior
// ---------------------------------------------------------------------------

describe("ResetPasswordPage — failure behavior", () => {
  beforeEach(() => {
    mockSearchParamsGet.mockImplementation((key: string) =>
      key === "token" ? "invalid-or-expired-token" : null
    );
  });

  it("displays ApiError.message for a 401 invalid/expired token rejection", async () => {
    mockResetPassword.mockRejectedValue(
      new ApiError(401, {
        success: false,
        message: "Reset token is invalid or has expired",
        code: "TOKEN_INVALID",
      })
    );
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "newsecure1");
    await user.type(screen.getByLabelText(/confirm password/i), "newsecure1");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Reset token is invalid or has expired"
    );
  });

  it("displays the generic fallback for a non-ApiError rejection", async () => {
    mockResetPassword.mockRejectedValue(new Error("Network error"));
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "newsecure1");
    await user.type(screen.getByLabelText(/confirm password/i), "newsecure1");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong. Please try again."
    );
  });

  it("does not navigate to /login after a failed reset", async () => {
    mockResetPassword.mockRejectedValue(
      new ApiError(401, {
        success: false,
        message: "Reset token is invalid or has expired",
        code: "TOKEN_INVALID",
      })
    );
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "newsecure1");
    await user.type(screen.getByLabelText(/confirm password/i), "newsecure1");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    await screen.findByRole("alert");
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("does not show the success confirmation after a failed reset", async () => {
    mockResetPassword.mockRejectedValue(
      new ApiError(401, {
        success: false,
        message: "Reset token is invalid or has expired",
        code: "TOKEN_INVALID",
      })
    );
    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "newsecure1");
    await user.type(screen.getByLabelText(/confirm password/i), "newsecure1");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    await screen.findByRole("alert");
    expect(
      screen.queryByText(/your password has been changed/i)
    ).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 6. Pending / loading state
// ---------------------------------------------------------------------------

describe("ResetPasswordPage — loading state", () => {
  beforeEach(() => {
    mockSearchParamsGet.mockImplementation((key: string) =>
      key === "token" ? "valid-reset-token-abc123" : null
    );
  });

  it("disables the submit button while resetPassword() is pending", async () => {
    let resolveFn!: () => void;
    mockResetPassword.mockImplementation(
      () => new Promise<void>((res) => { resolveFn = res; })
    );

    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "newsecure1");
    await user.type(screen.getByLabelText(/confirm password/i), "newsecure1");

    // Capture before clicking — accessible name changes to "Updating password…" during loading
    const submitButton = screen.getByRole("button", { name: /update password/i });
    const clickPromise = user.click(submitButton);

    await waitFor(() => {
      expect(submitButton).toBeDisabled();
    });

    resolveFn();
    await clickPromise;
  });

  it("shows 'Updating password…' text while pending", async () => {
    let resolveFn!: () => void;
    mockResetPassword.mockImplementation(
      () => new Promise<void>((res) => { resolveFn = res; })
    );

    const user = userEvent.setup();
    render(<ResetPasswordPage />);

    await user.type(screen.getByLabelText(/new password/i), "newsecure1");
    await user.type(screen.getByLabelText(/confirm password/i), "newsecure1");

    const clickPromise = user.click(
      screen.getByRole("button", { name: /update password/i })
    );

    await waitFor(() => {
      expect(screen.getByText(/updating password…/i)).toBeInTheDocument();
    });

    resolveFn();
    await clickPromise;
  });
});

// ---------------------------------------------------------------------------
// Cleanup: restore real timers after each test to prevent leakage
// ---------------------------------------------------------------------------

afterEach(() => {
  vi.useRealTimers();
});
