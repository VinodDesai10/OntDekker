/**
 * Component tests for ProtectedRoute in src/components/auth/ProtectedRoute.tsx
 *
 * Tests the route guard behavior across three states:
 *   1. isLoading=true → shows placeholder, no redirect
 *   2. unauthenticated → redirects to /login with return path
 *   3. authenticated → renders children
 *
 * Mocks:
 *   - useAuth() from AuthContext
 *   - next/navigation hooks (useRouter, usePathname)
 *
 * Uses React Testing Library + userEvent.
 * Uses waitFor for async redirect effects (React 19 async updates).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";

// ---------------------------------------------------------------------------
// Mock next/navigation
// ---------------------------------------------------------------------------

// Declare mock functions BEFORE vi.mock() to avoid Vitest hoisting issues
const mockReplace = vi.fn();
const mockUsePathname = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  usePathname: () => mockUsePathname(),
}));

// ---------------------------------------------------------------------------
// Mock AuthContext
// ---------------------------------------------------------------------------

const mockUseAuth = vi.fn();

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

// ---------------------------------------------------------------------------
// Setup + teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  mockUsePathname.mockReturnValue("/profile");
});

// ---------------------------------------------------------------------------
// 1. isLoading=true → placeholder rendered, no redirect
// ---------------------------------------------------------------------------

describe("ProtectedRoute — loading state", () => {
  it("renders a loading placeholder when isLoading is true", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    render(
      <ProtectedRoute>
        <div>Protected content</div>
      </ProtectedRoute>
    );

    // The loading placeholder has sr-only text "Loading…" and an aria-label
    expect(screen.getByLabelText("Loading session")).toBeInTheDocument();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });

  it("does not redirect while isLoading is true", async () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    render(
      <ProtectedRoute>
        <div>Protected content</div>
      </ProtectedRoute>
    );

    // Wait a tick to ensure no redirect was queued
    await waitFor(() => {
      expect(mockReplace).not.toHaveBeenCalled();
    });
  });

  it("does not render children while loading even if isAuthenticated is false", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    render(
      <ProtectedRoute>
        <div data-testid="child">Child</div>
      </ProtectedRoute>
    );

    expect(screen.queryByTestId("child")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 2. isLoading=false + unauthenticated → redirect to /login?redirect=...
// ---------------------------------------------------------------------------

describe("ProtectedRoute — unauthenticated redirect", () => {
  it("redirects to /login with encoded pathname when unauthenticated", async () => {
    mockUsePathname.mockReturnValue("/profile/edit");
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <div>Protected content</div>
      </ProtectedRoute>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        "/login?redirect=%2Fprofile%2Fedit"
      );
    });
  });

  it("does not render children when redirecting", async () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <div data-testid="protected-child">Should not appear</div>
      </ProtectedRoute>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalled();
    });

    expect(screen.queryByTestId("protected-child")).not.toBeInTheDocument();
  });

  it("preserves complex pathnames with slashes", async () => {
    mockUsePathname.mockReturnValue("/users/johndoe/followers");
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <div>Content</div>
      </ProtectedRoute>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        "/login?redirect=%2Fusers%2Fjohndoe%2Ffollowers"
      );
    });
  });

  it("encodes special characters in the redirect parameter", async () => {
    mockUsePathname.mockReturnValue("/search?q=hello world");
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <div>Content</div>
      </ProtectedRoute>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        "/login?redirect=%2Fsearch%3Fq%3Dhello%20world"
      );
    });
  });

  it("redirects to /login even when pathname is null", async () => {
    mockUsePathname.mockReturnValue(null);
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <div>Content</div>
      </ProtectedRoute>
    );

    // Fallback to "/" when pathname is null
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login?redirect=%2F");
    });
  });
});

// ---------------------------------------------------------------------------
// 3. authenticated → children rendered, no redirect
// ---------------------------------------------------------------------------

describe("ProtectedRoute — authenticated", () => {
  it("renders children when authenticated", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <div data-testid="secure-content">Authenticated content</div>
      </ProtectedRoute>
    );

    expect(screen.getByTestId("secure-content")).toBeInTheDocument();
    expect(screen.getByText("Authenticated content")).toBeInTheDocument();
  });

  it("does not redirect when authenticated", async () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <div>Content</div>
      </ProtectedRoute>
    );

    await waitFor(() => {
      expect(mockReplace).not.toHaveBeenCalled();
    });
  });

  it("renders multiple children correctly", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <h1>Title</h1>
        <p>Paragraph</p>
      </ProtectedRoute>
    );

    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByText("Paragraph")).toBeInTheDocument();
  });

  it("does not render the loading placeholder when authenticated", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <div>Content</div>
      </ProtectedRoute>
    );

    expect(screen.queryByLabelText("Loading session")).not.toBeInTheDocument();
  });
});
