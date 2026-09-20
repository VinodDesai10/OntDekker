/**
 * Integration tests for AuthContext (AuthProvider + useAuth)
 *
 * Tests the full session lifecycle through the real AuthProvider.
 * No internal implementation details are tested — only observable state and
 * behavior exposed by useAuth().
 *
 * Groups:
 *   A. Initial session — no stored refresh token
 *   B. Session restoration — valid refresh token
 *   C. Session restoration — stale/invalid refresh token
 *   D. Session restoration — refresh succeeds, /auth/me fails
 *   E. Login success
 *   F. Login failure
 *   G. Logout success
 *   H. Logout remote failure (non-fatal)
 *
 * MSW intercepts HTTP at the network boundary.
 * Handlers match the real base URL: http://localhost:8000
 *
 * Test isolation:
 *   - localStorage cleared in global afterEach (vitest.setup.ts)
 *   - In-memory access token cleared in local afterEach
 *   - MSW handlers reset in global afterEach
 *   - React cleanup in global afterEach
 */

import {
  describe,
  it,
  expect,
  beforeEach,
  afterEach,
} from "vitest";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  act,
} from "@testing-library/react";
import React, { useState } from "react";
import { server } from "@/__tests__/mocks/server";
import { authHandlers, DEFAULT_USER, DEFAULT_ACCESS_TOKEN, DEFAULT_REFRESH_TOKEN } from "@/__tests__/mocks/authHandlers";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { setAccessToken, getAccessToken } from "@/services/api";

// ---------------------------------------------------------------------------
// Test consumer component
//
// Renders all observable AuthContext state and exposes action buttons.
// This is what we assert against — never the provider internals.
// ---------------------------------------------------------------------------

function AuthConsumer() {
  const { user, isAuthenticated, isLoading, login, logout } = useAuth();
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loginPending, setLoginPending] = useState(false);

  async function handleLogin() {
    setLoginPending(true);
    setLoginError(null);
    try {
      await login({ email: "explorer@ontdekker.com", password: "password123" });
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoginPending(false);
    }
  }

  return (
    <div>
      <p data-testid="loading">{String(isLoading)}</p>
      <p data-testid="authenticated">{String(isAuthenticated)}</p>
      <p data-testid="user-id">{user?.id ?? "null"}</p>
      <p data-testid="user-email">{user?.email ?? "null"}</p>
      <p data-testid="login-error">{loginError ?? "null"}</p>
      <button onClick={handleLogin} disabled={loginPending}>
        Login
      </button>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

/** Render AuthProvider + AuthConsumer as a self-contained unit. */
function renderAuth() {
  return render(
    <AuthProvider>
      <AuthConsumer />
    </AuthProvider>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const REFRESH_KEY = "ontdekker_refresh_token";

function setStoredRefreshToken(token: string) {
  window.localStorage.setItem(REFRESH_KEY, token);
}

function getStoredRefreshToken(): string | null {
  return window.localStorage.getItem(REFRESH_KEY);
}

// ---------------------------------------------------------------------------
// Isolation: clear in-memory access token before/after each test.
// localStorage and MSW resets are handled by global vitest.setup.ts.
// ---------------------------------------------------------------------------

beforeEach(() => {
  setAccessToken(null);
});

afterEach(() => {
  setAccessToken(null);
});

// ---------------------------------------------------------------------------
// A. INITIAL SESSION — NO STORED REFRESH TOKEN
// ---------------------------------------------------------------------------

describe("A. No stored refresh token", () => {
  it("starts loading then settles as unauthenticated", async () => {
    // No refresh token stored — no HTTP calls expected at all.
    // MSW is in "error on unhandled" mode so any stray request would fail.
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    expect(screen.getByTestId("user-id")).toHaveTextContent("null");
  });

  it("does not make any HTTP requests when localStorage has no token", async () => {
    // MSW onUnhandledRequest:"error" (set in vitest.setup.ts) will cause a
    // test failure if any unintended request is made — this is the assertion.
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    // Reaching here without error proves no requests were made.
    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
  });

  it("access token remains null when no session is restored", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    expect(getAccessToken()).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// B. SESSION RESTORATION — VALID REFRESH TOKEN
// ---------------------------------------------------------------------------

describe("B. Valid session restoration", () => {
  beforeEach(() => {
    setStoredRefreshToken("stored-valid-refresh-token");
    server.use(
      authHandlers.refreshSuccess({ access_token: DEFAULT_ACCESS_TOKEN }),
      authHandlers.getMeSuccess(DEFAULT_USER)
    );
  });

  it("becomes authenticated after successful refresh + /auth/me", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });

    expect(screen.getByTestId("loading")).toHaveTextContent("false");
  });

  it("populates user with the UserIdentityResponse from /auth/me", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("user-id")).toHaveTextContent(DEFAULT_USER.id);
    });

    expect(screen.getByTestId("user-email")).toHaveTextContent(DEFAULT_USER.email);
  });

  it("sends the stored refresh token in the refresh request body", async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      // Override to capture the request body
      authHandlers.refreshSuccess(),
    );

    // Use a capturing handler layered on top
    const { http, HttpResponse } = await import("msw");
    server.use(
      http.post("http://localhost:8000/auth/refresh", async ({ request }) => {
        capturedBody = await request.json() as Record<string, unknown>;
        return HttpResponse.json({
          access_token: DEFAULT_ACCESS_TOKEN,
          token_type: "bearer",
          expires_in: 900,
        });
      }),
      authHandlers.getMeSuccess()
    );

    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });

    expect(capturedBody).toEqual({ refresh_token: "stored-valid-refresh-token" });
  });

  it("sets the in-memory access token after successful refresh", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });

    expect(getAccessToken()).toBe(DEFAULT_ACCESS_TOKEN);
  });

  it("does not rotate or clear the stored refresh token (no rotation in current contract)", async () => {
    // AccessTokenResponse does not include a new refresh_token, so the
    // existing stored token must remain untouched.
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });

    expect(getStoredRefreshToken()).toBe("stored-valid-refresh-token");
  });

  it("isLoading transitions from true to false", async () => {
    renderAuth();

    // Initial state should be loading
    expect(screen.getByTestId("loading")).toHaveTextContent("true");

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });
  });
});

// ---------------------------------------------------------------------------
// C. SESSION RESTORATION — STALE/INVALID REFRESH TOKEN
// ---------------------------------------------------------------------------

describe("C. Stale/invalid refresh token", () => {
  beforeEach(() => {
    setStoredRefreshToken("stale-refresh-token");
    server.use(authHandlers.refreshFailure(401, "Token expired"));
  });

  it("settles as unauthenticated when refresh fails", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    expect(screen.getByTestId("user-id")).toHaveTextContent("null");
  });

  it("clears the stored refresh token from localStorage", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    expect(getStoredRefreshToken()).toBeNull();
  });

  it("clears the in-memory access token", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    expect(getAccessToken()).toBeNull();
  });

  it("does not call /auth/me when refresh fails", async () => {
    // Register a handler that would fail the test if /auth/me is called.
    // MSW onUnhandledRequest:"error" handles GET /auth/me as unhandled.
    // We don't need an extra assertion — an unhandled /auth/me request
    // would produce an MSW error and fail the test automatically.
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
  });
});

// ---------------------------------------------------------------------------
// D. SESSION RESTORATION — REFRESH SUCCEEDS, /auth/me FAILS
// ---------------------------------------------------------------------------

describe("D. Refresh success + /auth/me failure", () => {
  beforeEach(() => {
    setStoredRefreshToken("valid-refresh-token");
    server.use(
      authHandlers.refreshSuccess(),
      authHandlers.getMeFailure(401, "Unauthorized")
    );
  });

  it("settles as unauthenticated when /auth/me fails", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    expect(screen.getByTestId("user-id")).toHaveTextContent("null");
  });

  it("clears the stored refresh token after /auth/me failure", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    expect(getStoredRefreshToken()).toBeNull();
  });

  it("clears the in-memory access token after /auth/me failure", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    expect(getAccessToken()).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// E. LOGIN SUCCESS
// ---------------------------------------------------------------------------

describe("E. Login success", () => {
  beforeEach(() => {
    // Start with no stored token — unauthenticated initial state
    server.use(
      authHandlers.loginSuccess(),
      authHandlers.getMeSuccess(DEFAULT_USER)
    );
  });

  it("becomes authenticated after successful login", async () => {
    renderAuth();

    // Wait for initial session restoration to complete (no stored token)
    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });
  });

  it("populates user with identity from /auth/me", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByTestId("user-id")).toHaveTextContent(DEFAULT_USER.id);
    });

    expect(screen.getByTestId("user-email")).toHaveTextContent(DEFAULT_USER.email);
  });

  it("stores refresh token in localStorage under the correct key", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });

    expect(getStoredRefreshToken()).toBe(DEFAULT_REFRESH_TOKEN);
  });

  it("stores access token in memory only, not in localStorage", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });

    // Access token must be in memory
    expect(getAccessToken()).toBe(DEFAULT_ACCESS_TOKEN);

    // Access token must NOT be in localStorage
    const lsValues: string[] = [];
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key) lsValues.push(window.localStorage.getItem(key) ?? "");
    }
    expect(lsValues).not.toContain(DEFAULT_ACCESS_TOKEN);
  });

  it("sends the correct LoginRequest body", async () => {
    let capturedBody: Record<string, unknown> | null = null;
    const { http, HttpResponse } = await import("msw");

    server.use(
      http.post("http://localhost:8000/auth/login", async ({ request }) => {
        capturedBody = await request.json() as Record<string, unknown>;
        return HttpResponse.json({
          access_token: DEFAULT_ACCESS_TOKEN,
          refresh_token: DEFAULT_REFRESH_TOKEN,
          token_type: "bearer",
          expires_in: 900,
        });
      }),
      authHandlers.getMeSuccess()
    );

    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });

    expect(capturedBody).toEqual({
      email: "explorer@ontdekker.com",
      password: "password123",
    });
  });
});

// ---------------------------------------------------------------------------
// F. LOGIN FAILURE
// ---------------------------------------------------------------------------

describe("F. Login failure", () => {
  beforeEach(() => {
    server.use(authHandlers.loginFailure(401, "Invalid credentials"));
  });

  it("remains unauthenticated after failed login", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByTestId("login-error")).not.toHaveTextContent("null");
    });

    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    expect(screen.getByTestId("user-id")).toHaveTextContent("null");
  });

  it("does not store a refresh token on login failure", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByTestId("login-error")).not.toHaveTextContent("null");
    });

    expect(getStoredRefreshToken()).toBeNull();
  });

  it("access token remains null on login failure", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByTestId("login-error")).not.toHaveTextContent("null");
    });

    expect(getAccessToken()).toBeNull();
  });

  it("propagates the error message to callers", async () => {
    renderAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(screen.getByTestId("login-error")).toHaveTextContent(
        "Invalid credentials"
      );
    });
  });
});

// ---------------------------------------------------------------------------
// G. LOGOUT SUCCESS
// ---------------------------------------------------------------------------

describe("G. Logout success", () => {
  // Start authenticated via session restoration
  beforeEach(() => {
    setStoredRefreshToken(DEFAULT_REFRESH_TOKEN);
    server.use(
      authHandlers.refreshSuccess(),
      authHandlers.getMeSuccess(DEFAULT_USER),
      authHandlers.logoutSuccess()
    );
  });

  async function renderAuthenticated() {
    renderAuth();
    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });
  }

  it("becomes unauthenticated after logout", async () => {
    await renderAuthenticated();

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    });

    expect(screen.getByTestId("user-id")).toHaveTextContent("null");
  });

  it("clears the in-memory access token on logout", async () => {
    await renderAuthenticated();

    expect(getAccessToken()).toBe(DEFAULT_ACCESS_TOKEN);

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    });

    expect(getAccessToken()).toBeNull();
  });

  it("removes the refresh token from localStorage on logout", async () => {
    await renderAuthenticated();

    expect(getStoredRefreshToken()).toBe(DEFAULT_REFRESH_TOKEN);

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    });

    expect(getStoredRefreshToken()).toBeNull();
  });

  it("sends the stored refresh token in the logout request body", async () => {
    let capturedBody: Record<string, unknown> | null = null;
    const { http, HttpResponse } = await import("msw");

    server.use(
      http.post("http://localhost:8000/auth/logout", async ({ request }) => {
        capturedBody = await request.json() as Record<string, unknown>;
        return HttpResponse.json({ message: "Logged out" });
      })
    );

    await renderAuthenticated();

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    });

    expect(capturedBody).toEqual({ refresh_token: DEFAULT_REFRESH_TOKEN });
  });
});

// ---------------------------------------------------------------------------
// H. LOGOUT REMOTE FAILURE (non-fatal)
// ---------------------------------------------------------------------------

describe("H. Logout remote failure", () => {
  beforeEach(() => {
    setStoredRefreshToken(DEFAULT_REFRESH_TOKEN);
    server.use(
      authHandlers.refreshSuccess(),
      authHandlers.getMeSuccess(DEFAULT_USER),
      authHandlers.logoutFailure(500, "Internal server error")
    );
  });

  async function renderAuthenticated() {
    renderAuth();
    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });
  }

  it("still clears local state even when remote logout fails", async () => {
    await renderAuthenticated();

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    });

    expect(screen.getByTestId("user-id")).toHaveTextContent("null");
  });

  it("clears the in-memory access token despite remote failure", async () => {
    await renderAuthenticated();

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    });

    expect(getAccessToken()).toBeNull();
  });

  it("removes the stored refresh token despite remote failure", async () => {
    await renderAuthenticated();

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    });

    expect(getStoredRefreshToken()).toBeNull();
  });

  it("does not produce an unhandled promise rejection", async () => {
    // AuthContext.logout() wraps remote logout in try/catch and treats
    // failure as non-fatal. If this test passes without an unhandled
    // rejection error in Vitest, the contract is satisfied.
    await renderAuthenticated();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Logout" }));
    });

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    });
  });
});
