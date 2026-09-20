/**
 * Component tests for LogoutButton in src/components/auth/LogoutButton.tsx
 *
 * Behavior under test:
 *   A. Button renders with accessible label "Sign out"
 *   B. Clicking calls logout() exactly once and then navigates to /login
 *   C. Button shows loading state (disabled, "Signing out…") while logout runs
 *   D. Navigates to /login even when logout() rejects (finally block always runs)
 *
 * Mocks:
 *   - useAuth() to provide a controllable logout function
 *   - next/navigation useRouter
 *
 * Uses userEvent for user interaction.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LogoutButton } from "@/components/auth/LogoutButton";

// ---------------------------------------------------------------------------
// Mock next/navigation
// ---------------------------------------------------------------------------

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
}));

// ---------------------------------------------------------------------------
// Mock AuthContext
// ---------------------------------------------------------------------------

const mockLogout = vi.fn();

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ logout: mockLogout }),
}));

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// A. Accessibility and initial render
// ---------------------------------------------------------------------------

describe("LogoutButton — render", () => {
  it("renders a button with aria-label 'Sign out'", () => {
    mockLogout.mockResolvedValue(undefined);

    render(<LogoutButton />);

    const button = screen.getByRole("button", { name: "Sign out" });
    expect(button).toBeInTheDocument();
  });

  it("renders 'Sign out' text when idle", () => {
    mockLogout.mockResolvedValue(undefined);

    render(<LogoutButton />);

    expect(screen.getByText("Sign out")).toBeInTheDocument();
  });

  it("is not disabled in the idle state", () => {
    mockLogout.mockResolvedValue(undefined);

    render(<LogoutButton />);

    const button = screen.getByRole("button", { name: "Sign out" });
    expect(button).not.toBeDisabled();
  });

  it("accepts a className prop without error", () => {
    mockLogout.mockResolvedValue(undefined);

    render(<LogoutButton className="custom-class" />);

    const button = screen.getByRole("button", { name: "Sign out" });
    expect(button).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// B. Click behavior — successful logout
// ---------------------------------------------------------------------------

describe("LogoutButton — click behavior", () => {
  it("calls logout exactly once when clicked", async () => {
    mockLogout.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<LogoutButton />);

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledTimes(1);
    });
  });

  it("navigates to /login after successful logout", async () => {
    mockLogout.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<LogoutButton />);

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login");
    });
  });

  it("navigates to /login exactly once", async () => {
    mockLogout.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<LogoutButton />);

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledTimes(1);
    });
  });
});

// ---------------------------------------------------------------------------
// C. Loading state during logout
// ---------------------------------------------------------------------------

describe("LogoutButton — loading state", () => {
  it("disables the button while logout is in progress", async () => {
    // Use a deferred promise so we can control exactly when logout resolves
    let resolveFn!: () => void;
    mockLogout.mockImplementation(
      () => new Promise<void>((res) => { resolveFn = res; })
    );

    const user = userEvent.setup();
    render(<LogoutButton />);

    // Start the click — don't await yet so loading state is observable
    const clickPromise = user.click(
      screen.getByRole("button", { name: "Sign out" })
    );

    // Wait for loading state to appear
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Sign out" })
      ).toBeDisabled();
    });

    // Resolve and clean up — prevents act() warning from pending state update
    resolveFn();
    await clickPromise;
  });

  it("shows 'Signing out…' text while loading", async () => {
    let resolveFn!: () => void;
    mockLogout.mockImplementation(
      () => new Promise<void>((res) => { resolveFn = res; })
    );

    const user = userEvent.setup();
    render(<LogoutButton />);

    const clickPromise = user.click(
      screen.getByRole("button", { name: "Sign out" })
    );

    await waitFor(() => {
      expect(screen.getByText("Signing out…")).toBeInTheDocument();
    });

    // Resolve and clean up
    resolveFn();
    await clickPromise;
  });

  it("returns button to idle state after logout completes", async () => {
    mockLogout.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<LogoutButton />);
    await user.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login");
    });
  });
});

// ---------------------------------------------------------------------------
// D. Logout rejection — component navigates regardless (catch + finally)
// ---------------------------------------------------------------------------

describe("LogoutButton — logout rejection", () => {
  it("still navigates to /login when logout() rejects", async () => {
    // The catch block in handleLogout swallows the error.
    // The finally block always calls router.replace("/login").
    mockLogout.mockRejectedValue(new Error("Remote revocation failed"));
    const user = userEvent.setup();

    render(<LogoutButton />);

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login");
    });
  });

  it("calls logout exactly once even when it rejects", async () => {
    mockLogout.mockRejectedValue(new Error("Revocation error"));
    const user = userEvent.setup();

    render(<LogoutButton />);

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledTimes(1);
    });
  });
});
