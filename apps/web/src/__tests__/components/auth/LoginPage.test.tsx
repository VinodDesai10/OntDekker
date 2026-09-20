/**
 * Component tests for the Login page (src/app/login/page.tsx)
 *
 * Tests observable behavior only — no implementation internals.
 *
 * Coverage:
 *   1. Rendering / basic state
 *   2. Client-side validation
 *   3. Successful login (credentials passed, navigation)
 *   4. Login failure (ApiError message, generic fallback, no navigation)
 *   5. Already-authenticated redirect
 *
 * Mocks:
 *   - useAuth() from AuthContext (provides controllable login fn + auth state)
 *   - next/navigation (useRouter, useSearchParams)
 *
 * No MSW / no network — login() is fully delegated to the mocked AuthContext.
 * next/navigation is mocked globally; searchParams are controlled per-test via
 * mockSearchParams.get.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoginPage from "@/app/login/page";
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
// Mock AuthContext
// ---------------------------------------------------------------------------

const mockLogin = vi.fn();
const mockUseAuth = vi.fn();

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Default unauthenticated, idle auth state. */
function unauthState() {
  return { login: mockLogin, isAuthenticated: false, isLoading: false };
}

/** Render the page with no query params by default. */
function renderLogin() {
  return render(<LoginPage />);
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  // Default: no query params, unauthenticated, settled
  mockSearchParamsGet.mockReturnValue(null);
  mockUseAuth.mockReturnValue(unauthState());
});

// ---------------------------------------------------------------------------
// 1. Rendering / basic state
// ---------------------------------------------------------------------------

describe("LoginPage — rendering", () => {
  it("renders an email input", () => {
    renderLogin();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });

  it("renders a password input", () => {
    renderLogin();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
  });

  it("renders the submit button with 'Sign in' text", () => {
    renderLogin();
    expect(
      screen.getByRole("button", { name: /sign in/i })
    ).toBeInTheDocument();
  });

  it("shows the ?registered=1 success banner when param is present", () => {
    mockSearchParamsGet.mockImplementation((key: string) =>
      key === "registered" ? "1" : null
    );
    renderLogin();
    expect(
      screen.getByText(/account created/i)
    ).toBeInTheDocument();
  });

  it("does not show registration banner without the param", () => {
    mockSearchParamsGet.mockReturnValue(null);
    renderLogin();
    expect(screen.queryByText(/account created/i)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 2. Validation
// ---------------------------------------------------------------------------

describe("LoginPage — validation", () => {
  it("shows 'Email is required.' when submitted with empty email", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email is required."
    );
  });

  it("shows 'Password is required.' when email is filled but password is empty", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Password is required."
    );
  });

  it("does not call login() when validation fails", async () => {
    const user = userEvent.setup();
    renderLogin();

    // Submit with empty fields
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await screen.findByRole("alert");
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it("whitespace-only email is treated as empty (Email is required.)", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email/i), "   ");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email is required."
    );
    expect(mockLogin).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// 3. Successful login
// ---------------------------------------------------------------------------

describe("LoginPage — successful login", () => {
  beforeEach(() => {
    mockLogin.mockResolvedValue(undefined);
  });

  it("calls login() with trimmed email and exact password", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(
      screen.getByLabelText(/email/i),
      "  explorer@ontdekker.com  "
    );
    await user.type(screen.getByLabelText(/^password$/i), "secret123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: "explorer@ontdekker.com",
        password: "secret123",
      });
    });
  });

  it("navigates to '/feed' when no redirect param is present", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email/i), "explorer@ontdekker.com");
    await user.type(screen.getByLabelText(/^password$/i), "secret123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/feed");
    });
  });

  it("navigates to a safe relative redirect path from the query param", async () => {
    mockSearchParamsGet.mockImplementation((key: string) =>
      key === "redirect" ? "%2Fprofile" : null
    );
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email/i), "explorer@ontdekker.com");
    await user.type(screen.getByLabelText(/^password$/i), "secret123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/profile");
    });
  });

  it("falls back to '/feed' for an unsafe open-redirect value (//evil.com)", async () => {
    mockSearchParamsGet.mockImplementation((key: string) =>
      key === "redirect" ? "//evil.com" : null
    );
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email/i), "explorer@ontdekker.com");
    await user.type(screen.getByLabelText(/^password$/i), "secret123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/feed");
    });
  });

  it("falls back to '/feed' for an absolute URL redirect value", async () => {
    mockSearchParamsGet.mockImplementation((key: string) =>
      key === "redirect" ? "https://evil.com/steal" : null
    );
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email/i), "explorer@ontdekker.com");
    await user.type(screen.getByLabelText(/^password$/i), "secret123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/feed");
    });
  });
});

// ---------------------------------------------------------------------------
// 4. Login failure
// ---------------------------------------------------------------------------

describe("LoginPage — login failure", () => {
  it("displays ApiError.message when login() rejects with ApiError", async () => {
    mockLogin.mockRejectedValue(
      new ApiError(401, {
        success: false,
        message: "Invalid email or password",
        code: "INVALID_CREDENTIALS",
      })
    );
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email/i), "explorer@ontdekker.com");
    await user.type(screen.getByLabelText(/^password$/i), "wrongpass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid email or password"
    );
  });

  it("displays generic fallback message for a non-ApiError rejection", async () => {
    mockLogin.mockRejectedValue(new Error("Network failure"));
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email/i), "explorer@ontdekker.com");
    await user.type(screen.getByLabelText(/^password$/i), "somepass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong. Please try again."
    );
  });

  it("does not navigate after a failed login", async () => {
    mockLogin.mockRejectedValue(
      new ApiError(401, {
        success: false,
        message: "Invalid email or password",
        code: "INVALID_CREDENTIALS",
      })
    );
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email/i), "explorer@ontdekker.com");
    await user.type(screen.getByLabelText(/^password$/i), "wrongpass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await screen.findByRole("alert");
    expect(mockReplace).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// 5. Already-authenticated redirect
// ---------------------------------------------------------------------------

describe("LoginPage — already-authenticated redirect", () => {
  it("redirects to '/feed' when user is already authenticated and auth is not loading", async () => {
    mockUseAuth.mockReturnValue({
      login: mockLogin,
      isAuthenticated: true,
      isLoading: false,
    });

    renderLogin();

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/feed");
    });
  });

  it("does not redirect while auth is still loading", async () => {
    mockUseAuth.mockReturnValue({
      login: mockLogin,
      isAuthenticated: true,
      isLoading: true,
    });

    renderLogin();

    // Allow any pending microtasks to settle
    await waitFor(() => {
      expect(mockReplace).not.toHaveBeenCalled();
    });
  });
});
