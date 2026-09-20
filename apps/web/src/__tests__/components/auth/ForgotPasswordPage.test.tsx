/**
 * Component tests for the Forgot Password page
 * (src/app/forgot-password/page.tsx)
 *
 * Tests observable behavior only — no implementation internals.
 *
 * ForgotPasswordPage calls forgotPassword() from @/services/auth directly.
 * No router calls are made; there is no navigation on success.
 * Mock is placed at the service boundary. No MSW needed.
 *
 * Coverage:
 *   1. Rendering / basic state
 *   2. Client-side validation
 *   3. Successful submission (confirmation state + "Try again" action)
 *   4. Failure behavior (three distinct error branches in production code)
 *   5. Pending / loading state
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ForgotPasswordPage from "@/app/forgot-password/page";
import { ApiError } from "@/services/api";

// ---------------------------------------------------------------------------
// Mock forgotPassword() at the service boundary
// ForgotPasswordPage imports forgotPassword() directly from @/services/auth.
// ---------------------------------------------------------------------------

const mockForgotPassword = vi.fn();

vi.mock("@/services/auth", () => ({
  forgotPassword: (...args: unknown[]) => mockForgotPassword(...args),
}));

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// 1. Rendering / basic state
// ---------------------------------------------------------------------------

describe("ForgotPasswordPage — rendering", () => {
  it("renders the email input", () => {
    render(<ForgotPasswordPage />);
    expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument();
  });

  it("renders the 'Send reset link' submit button", () => {
    render(<ForgotPasswordPage />);
    expect(
      screen.getByRole("button", { name: /send reset link/i })
    ).toBeInTheDocument();
  });

  it("renders a 'Back to sign in' link", () => {
    render(<ForgotPasswordPage />);
    expect(
      screen.getByRole("link", { name: /back to sign in/i })
    ).toBeInTheDocument();
  });

  it("does not show the confirmation state on initial render", () => {
    render(<ForgotPasswordPage />);
    expect(screen.queryByText(/check your inbox/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/try again/i)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 2. Validation
// ---------------------------------------------------------------------------

describe("ForgotPasswordPage — validation", () => {
  it("shows 'Email is required.' when submitted with empty email", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email is required."
    );
    expect(mockForgotPassword).not.toHaveBeenCalled();
  });

  it("shows 'Email is required.' for whitespace-only email", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText(/^email$/i), "   ");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email is required."
    );
    expect(mockForgotPassword).not.toHaveBeenCalled();
  });

  it("does not call forgotPassword() when validation fails", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    // Submit completely empty
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    await screen.findByRole("alert");
    expect(mockForgotPassword).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// 3. Successful submission
// ---------------------------------------------------------------------------

describe("ForgotPasswordPage — successful submission", () => {
  beforeEach(() => {
    mockForgotPassword.mockResolvedValue({
      message: "If that email exists, a reset link has been sent.",
    });
  });

  it("calls forgotPassword() with the trimmed email", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(
      screen.getByLabelText(/^email$/i),
      "  user@example.com  "
    );
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    await waitFor(() => {
      expect(mockForgotPassword).toHaveBeenCalledWith({
        email: "user@example.com",
      });
    });
  });

  it("shows the confirmation heading after successful submit", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    // The confirmation view title comes from AuthCard's title prop
    expect(await screen.findByText(/check your inbox/i)).toBeInTheDocument();
  });

  it("shows a 'Try again' button in the confirmation state", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(
      await screen.findByRole("button", { name: /try again/i })
    ).toBeInTheDocument();
  });

  it("confirmation state does not reveal whether an account exists", async () => {
    // The description text must be the safe generic form — not "your account exists"
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    await screen.findByText(/check your inbox/i);

    // Safe: the description mentions "if an account … exists"
    expect(screen.getByText(/if an account with that email exists/i)).toBeInTheDocument();
    // Must not claim the email was found or the account definitely exists
    expect(screen.queryByText(/your account/i)).not.toBeInTheDocument();
  });

  it("clicking 'Try again' returns to the form with the email cleared", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    // Wait for confirmation state
    const tryAgainButton = await screen.findByRole("button", {
      name: /try again/i,
    });

    await user.click(tryAgainButton);

    // Back to the form
    expect(
      await screen.findByRole("button", { name: /send reset link/i })
    ).toBeInTheDocument();

    // Email field is cleared
    expect(screen.getByLabelText(/^email$/i)).toHaveValue("");
  });
});

// ---------------------------------------------------------------------------
// 4. Failure behavior
// ---------------------------------------------------------------------------

describe("ForgotPasswordPage — failure behavior", () => {
  it("shows 'Something went wrong. Please try again later.' for a 500 ApiError", async () => {
    mockForgotPassword.mockRejectedValue(
      new ApiError(500, {
        success: false,
        message: "Internal server error",
        code: "INTERNAL_ERROR",
      })
    );
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong. Please try again later."
    );
  });

  it("shows ApiError.message for an unexpected sub-500 ApiError", async () => {
    // Backend should always return 200; a 4xx here is unexpected but the page
    // surfaces the error message directly per the production catch branch.
    mockForgotPassword.mockRejectedValue(
      new ApiError(400, {
        success: false,
        message: "Unexpected validation error",
        code: "VALIDATION_ERROR",
      })
    );
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unexpected validation error"
    );
  });

  it("shows 'Something went wrong. Please try again.' for a non-ApiError rejection", async () => {
    mockForgotPassword.mockRejectedValue(new Error("Network failure"));
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong. Please try again."
    );
  });

  it("does not show the confirmation state after a failed submission", async () => {
    mockForgotPassword.mockRejectedValue(
      new ApiError(500, {
        success: false,
        message: "Internal server error",
        code: "INTERNAL_ERROR",
      })
    );
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    await screen.findByRole("alert");
    expect(screen.queryByText(/check your inbox/i)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 5. Pending / loading state
// ---------------------------------------------------------------------------

describe("ForgotPasswordPage — loading state", () => {
  it("disables the submit button while forgotPassword() is pending", async () => {
    let resolveFn!: () => void;
    mockForgotPassword.mockImplementation(
      () => new Promise<void>((res) => { resolveFn = res; })
    );

    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");

    // Capture before clicking — accessible name changes to "Sending reset link…" during loading
    const submitButton = screen.getByRole("button", { name: /send reset link/i });
    const clickPromise = user.click(submitButton);

    await waitFor(() => {
      expect(submitButton).toBeDisabled();
    });

    resolveFn();
    await clickPromise;
  });

  it("shows 'Sending reset link…' text while pending", async () => {
    let resolveFn!: () => void;
    mockForgotPassword.mockImplementation(
      () => new Promise<void>((res) => { resolveFn = res; })
    );

    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");

    const clickPromise = user.click(
      screen.getByRole("button", { name: /send reset link/i })
    );

    await waitFor(() => {
      expect(screen.getByText(/sending reset link…/i)).toBeInTheDocument();
    });

    resolveFn();
    await clickPromise;
  });
});
