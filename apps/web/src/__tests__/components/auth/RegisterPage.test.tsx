/**
 * Component tests for the Register page (src/app/register/page.tsx)
 *
 * Tests observable behavior only — no implementation internals.
 *
 * RegisterPage calls register() from @/services/auth directly (not through
 * AuthContext). The mock is placed at that service boundary.
 * No MSW / no network — register() is fully mocked.
 *
 * Coverage:
 *   1. Rendering / basic state
 *   2. Client-side validation (exact production messages and order)
 *   3. Successful registration (request shape, navigation, call count)
 *   4. Registration failure (ApiError message, generic fallback, no navigation)
 *   5. Submission / loading behavior
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RegisterPage from "@/app/register/page";
import { ApiError } from "@/services/api";

// ---------------------------------------------------------------------------
// Mock next/navigation
// ---------------------------------------------------------------------------

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// ---------------------------------------------------------------------------
// Mock register() at the service boundary
// RegisterPage imports register() directly from @/services/auth.
// ---------------------------------------------------------------------------

const mockRegister = vi.fn();

vi.mock("@/services/auth", () => ({
  register: (...args: unknown[]) => mockRegister(...args),
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

describe("RegisterPage — rendering", () => {
  it("renders an email input", () => {
    render(<RegisterPage />);
    expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument();
  });

  it("renders a password input", () => {
    render(<RegisterPage />);
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
  });

  it("renders a confirm password input", () => {
    render(<RegisterPage />);
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
  });

  it("renders the submit button with 'Create account' text", () => {
    render(<RegisterPage />);
    expect(
      screen.getByRole("button", { name: /create account/i })
    ).toBeInTheDocument();
  });

  it("renders a link to the sign in page", () => {
    render(<RegisterPage />);
    expect(screen.getByRole("link", { name: /sign in/i })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 2. Validation
// ---------------------------------------------------------------------------

describe("RegisterPage — validation", () => {
  it("shows 'Email is required.' when submitted with empty email", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email is required."
    );
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("shows 'Email is required.' for whitespace-only email", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "   ");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email is required."
    );
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("shows 'Password is required.' when email is filled but password is empty", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Password is required."
    );
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("shows 'Password must be at least 8 characters.' for a short password", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "short");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Password must be at least 8 characters."
    );
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("shows 'Passwords do not match.' when confirm password differs", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "validpass1");
    await user.type(screen.getByLabelText(/confirm password/i), "different99");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Passwords do not match."
    );
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("accepts exactly 8 characters as a valid minimum password length", async () => {
    mockRegister.mockResolvedValue({});
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "exactly8");
    await user.type(screen.getByLabelText(/confirm password/i), "exactly8");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledOnce();
    });
    // No validation error should be shown
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 3. Successful registration
// ---------------------------------------------------------------------------

describe("RegisterPage — successful registration", () => {
  beforeEach(() => {
    mockRegister.mockResolvedValue({
      message: "Account created successfully.",
      user_id: "new-user-id",
      email: "user@example.com",
    });
  });

  it("calls register() with trimmed email and password — NOT confirmPassword", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "  user@example.com  ");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith({
        email: "user@example.com",
        password: "securepass1",
      });
    });
  });

  it("does not include confirmPassword in the register() call", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith(
        expect.not.objectContaining({ confirmPassword: expect.anything() })
      );
    });
  });

  it("navigates to /verify-email?email=<encoded> after successful registration", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith(
        `/verify-email?email=${encodeURIComponent("user@example.com")}`
      );
    });
  });

  it("calls register() exactly once for one valid submission", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledOnce();
    });
  });
});

// ---------------------------------------------------------------------------
// 4. Registration failure
// ---------------------------------------------------------------------------

describe("RegisterPage — registration failure", () => {
  it("redirects to /verify-email for a 409 EMAIL_ALREADY_REGISTERED response", async () => {
    // New behavior: duplicate registration redirects to verify-email so the
    // user can complete (or is informed about) the verification flow — no
    // error banner is shown.
    mockRegister.mockRejectedValue(
      new ApiError(409, {
        success: false,
        message: "Email already registered",
        code: "EMAIL_ALREADY_REGISTERED",
      })
    );
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "taken@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith(
        `/verify-email?email=${encodeURIComponent("taken@example.com")}`
      );
    });
    // No error banner should be displayed
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("displays the generic fallback for a non-ApiError rejection", async () => {
    mockRegister.mockRejectedValue(new Error("Network error"));
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong. Please try again."
    );
  });

  it("does not navigate after a generic (non-duplicate) registration failure", async () => {
    // Only EMAIL_ALREADY_REGISTERED triggers a redirect — all other errors
    // should display an error banner and stay on the register page.
    mockRegister.mockRejectedValue(
      new ApiError(500, {
        success: false,
        message: "Internal server error",
        code: "INTERNAL_ERROR",
      })
    );
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await screen.findByRole("alert");
    expect(mockPush).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// 5. Submission / loading behavior
// ---------------------------------------------------------------------------

describe("RegisterPage — loading state", () => {
  it("disables the submit button while registration is in progress", async () => {
    let resolveFn!: () => void;
    mockRegister.mockImplementation(
      () => new Promise<void>((res) => { resolveFn = res; })
    );

    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");

    // Capture the submit button reference before clicking — its accessible
    // name changes to "Creating account…" once the loading state activates.
    const submitButton = screen.getByRole("button", { name: /create account/i });

    const clickPromise = user.click(submitButton);

    // While pending the button is disabled (verified via the DOM reference)
    await waitFor(() => {
      expect(submitButton).toBeDisabled();
    });

    // Resolve and clean up to prevent act() warning
    resolveFn();
    await clickPromise;
  });

  it("shows 'Creating account…' text while registration is pending", async () => {
    let resolveFn!: () => void;
    mockRegister.mockImplementation(
      () => new Promise<void>((res) => { resolveFn = res; })
    );

    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText(/^email$/i), "user@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");

    const clickPromise = user.click(
      screen.getByRole("button", { name: /create account/i })
    );

    await waitFor(() => {
      expect(screen.getByText(/creating account…/i)).toBeInTheDocument();
    });

    resolveFn();
    await clickPromise;
  });
});
