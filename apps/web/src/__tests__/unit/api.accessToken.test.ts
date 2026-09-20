/**
 * Unit tests for setAccessToken() / getAccessToken() in src/services/api.ts
 *
 * These functions manage the in-memory access token used by the Axios
 * request interceptor. The token is NEVER written to localStorage or any
 * browser storage — it is purely in-memory.
 *
 * Tests:
 *   1. Initial/cleared state returns null
 *   2. Setting a token makes it retrievable
 *   3. Replacing a token works
 *   4. Clearing with null returns null
 *   5. Token is not persisted to localStorage
 *
 * Note: Each test resets the token to null in afterEach to ensure isolation,
 * since setAccessToken/getAccessToken operate on module-level state.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { setAccessToken, getAccessToken } from "@/services/api";

// Reset the in-memory token before and after every test to prevent
// state leakage between tests (the module is shared across the test file).
beforeEach(() => {
  setAccessToken(null);
});

afterEach(() => {
  setAccessToken(null);
});

// ---------------------------------------------------------------------------
// Core token management
// ---------------------------------------------------------------------------

describe("getAccessToken / setAccessToken", () => {
  it("returns null when no token has been set", () => {
    expect(getAccessToken()).toBeNull();
  });

  it("returns the token after it is set", () => {
    setAccessToken("test-access-token-abc123");
    expect(getAccessToken()).toBe("test-access-token-abc123");
  });

  it("replaces an existing token with a new value", () => {
    setAccessToken("first-token");
    setAccessToken("second-token");
    expect(getAccessToken()).toBe("second-token");
  });

  it("clears the token when set to null", () => {
    setAccessToken("some-token");
    setAccessToken(null);
    expect(getAccessToken()).toBeNull();
  });

  it("stores the exact string value provided (no transformation)", () => {
    const rawToken =
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEifQ.sig";
    setAccessToken(rawToken);
    expect(getAccessToken()).toBe(rawToken);
  });
});

// ---------------------------------------------------------------------------
// Storage isolation — token must NOT be written to localStorage
// ---------------------------------------------------------------------------

describe("access token storage isolation", () => {
  it("does not write the token to localStorage", () => {
    window.localStorage.clear();
    setAccessToken("should-not-be-stored");

    // Check every localStorage key — none should contain the token
    const allValues: string[] = [];
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key) allValues.push(window.localStorage.getItem(key) ?? "");
    }

    expect(allValues).not.toContain("should-not-be-stored");
    expect(window.localStorage.length).toBe(0);
  });

  it("does not read or depend on localStorage", () => {
    window.localStorage.setItem("ontdekker_access_token", "stale-stored-token");
    setAccessToken("real-in-memory-token");

    // getAccessToken must return the in-memory value, not the localStorage one
    expect(getAccessToken()).toBe("real-in-memory-token");
    window.localStorage.clear();
  });

  it("returns null even if localStorage contains a stale token value", () => {
    window.localStorage.setItem("access_token", "leftover-value");
    // Token not set in memory — should still return null
    expect(getAccessToken()).toBeNull();
    window.localStorage.clear();
  });
});
