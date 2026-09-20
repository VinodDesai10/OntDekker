/**
 * Vitest global setup
 *
 * Runs once before any test file is executed.
 * Configures:
 *  - @testing-library/jest-dom custom matchers for Vitest
 *  - MSW Node server lifecycle (listen → reset → close)
 *  - Testing Library automatic DOM cleanup (provided by @testing-library/react
 *    automatically when a jsdom environment is detected)
 *  - localStorage shim (jsdom v29+ removed localStorage by default)
 */

import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { cleanup } from "@testing-library/react";
import { server } from "./src/__tests__/mocks/server";

// ---------------------------------------------------------------------------
// localStorage shim for jsdom v29+
// jsdom removed localStorage support by default. We restore it manually.
// ---------------------------------------------------------------------------

class LocalStorageMock implements Storage {
  private store: Map<string, string> = new Map();

  get length() {
    return this.store.size;
  }

  clear() {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string) {
    this.store.delete(key);
  }

  setItem(key: string, value: string) {
    this.store.set(key, value);
  }
}

// Inject localStorage into the jsdom window if it's missing or broken (e.g. Node 22 uninitialized Storage)
if (typeof window !== "undefined" && typeof window.localStorage?.getItem !== "function") {
  Object.defineProperty(window, "localStorage", {
    value: new LocalStorageMock(),
    writable: true,
    configurable: true,
  });
}

// ---------------------------------------------------------------------------
// MSW lifecycle
// ---------------------------------------------------------------------------

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});

afterEach(() => {
  // Reset any runtime handlers added during a test (via server.use(...))
  server.resetHandlers();
  // Ensure DOM is cleaned up between tests
  cleanup();
  // Clear localStorage between tests to prevent state leakage
  if (typeof window !== "undefined" && window.localStorage) {
    window.localStorage.clear();
  }
});

afterAll(() => {
  server.close();
});
