/**
 * Infrastructure smoke test — 6F-1
 *
 * Verifies:
 *  - Vitest executes in jsdom environment
 *  - @testing-library/jest-dom matchers are wired
 *  - MSW server starts without error (lifecycle hooks in vitest.setup.ts)
 *
 * Does NOT test application functionality.
 */

import { describe, it, expect } from "vitest";

describe("Test infrastructure", () => {
  it("runs in jsdom environment", () => {
    expect(typeof window).toBe("object");
    expect(typeof document).toBe("object");
  });

  it("has jest-dom matchers available", () => {
    const el = document.createElement("div");
    el.textContent = "hello";
    document.body.appendChild(el);
    expect(el).toBeInTheDocument();
    document.body.removeChild(el);
  });

  it("localStorage is available in jsdom via window", () => {
    // jsdom v29+ removed localStorage by default; vitest.setup.ts restores it
    // via a LocalStorageMock shim. This confirms the shim is active and
    // that AuthContext tests can rely on window.localStorage.
    window.localStorage.setItem("smoke", "1");
    expect(window.localStorage.getItem("smoke")).toBe("1");
    window.localStorage.clear();
  });
});
