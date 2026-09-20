/**
 * Unit tests for normalizeError() in src/services/api.ts
 *
 * Tests the exact current behavior of the error normalization function:
 *
 * 1. Standard backend envelope → ApiError with correct fields
 * 2. Non-standard/missing body → ApiError with HTTP_{status} code fallback
 * 3. Axios error with no response (network failure) → re-thrown unchanged
 * 4. Non-Axios error → re-thrown unchanged
 *
 * No mocks of normalizeError itself — we call the real function.
 * No network calls.
 */

import { describe, it, expect } from "vitest";
import { AxiosError, AxiosHeaders } from "axios";
import { normalizeError, ApiError } from "@/services/api";

// ---------------------------------------------------------------------------
// Helper: build a realistic AxiosError with a response body
// ---------------------------------------------------------------------------

function makeAxiosResponseError(
  status: number,
  data: unknown,
  message = "Request failed"
): AxiosError {
  const request = {};
  const headers = new AxiosHeaders();
  const config = { headers };

  const response = {
    data,
    status,
    statusText: String(status),
    headers,
    config: config as AxiosError["config"],
  };

  const error = new AxiosError(
    message,
    `ERR_BAD_RESPONSE`,
    config as AxiosError["config"],
    request,
    response as AxiosError["response"]
  );

  return error;
}

// ---------------------------------------------------------------------------
// 1. Standard backend error envelope
// ---------------------------------------------------------------------------

describe("normalizeError — standard backend envelope", () => {
  it("throws ApiError with correct message, status, code, and details", () => {
    const error = makeAxiosResponseError(422, {
      success: false,
      message: "Validation failed",
      code: "VALIDATION_ERROR",
      details: { field: "email" },
    });

    expect(() => normalizeError(error)).toThrow(ApiError);

    try {
      normalizeError(error);
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const apiErr = e as ApiError;
      expect(apiErr.message).toBe("Validation failed");
      expect(apiErr.status).toBe(422);
      expect(apiErr.code).toBe("VALIDATION_ERROR");
      expect(apiErr.details).toEqual({ field: "email" });
    }
  });

  it("throws ApiError with name 'ApiError'", () => {
    const error = makeAxiosResponseError(401, {
      success: false,
      message: "Unauthorized",
      code: "UNAUTHORIZED",
    });

    try {
      normalizeError(error);
    } catch (e) {
      expect((e as Error).name).toBe("ApiError");
    }
  });

  it("propagates null details when omitted from envelope", () => {
    const error = makeAxiosResponseError(404, {
      success: false,
      message: "Not found",
      code: "NOT_FOUND",
      // no details field
    });

    try {
      normalizeError(error);
    } catch (e) {
      const apiErr = e as ApiError;
      expect(apiErr.details).toBeUndefined();
    }
  });

  it("handles 500 status correctly", () => {
    const error = makeAxiosResponseError(500, {
      success: false,
      message: "Internal server error",
      code: "INTERNAL_ERROR",
    });

    try {
      normalizeError(error);
    } catch (e) {
      const apiErr = e as ApiError;
      expect(apiErr.status).toBe(500);
      expect(apiErr.code).toBe("INTERNAL_ERROR");
    }
  });
});

// ---------------------------------------------------------------------------
// 2. Non-standard / missing body (fallback behavior)
// ---------------------------------------------------------------------------

describe("normalizeError — non-standard / missing body", () => {
  it("falls back to HTTP_{status} code when body has no message/code", () => {
    const error = makeAxiosResponseError(503, {
      error: "Service Unavailable",
      // no 'message' or 'code' keys matching the envelope
    });

    try {
      normalizeError(error);
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const apiErr = e as ApiError;
      expect(apiErr.status).toBe(503);
      expect(apiErr.code).toBe("HTTP_503");
      // message comes from AxiosError.message in this path
      expect(typeof apiErr.message).toBe("string");
    }
  });

  it("falls back when body is null", () => {
    const error = makeAxiosResponseError(502, null);

    try {
      normalizeError(error);
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const apiErr = e as ApiError;
      expect(apiErr.status).toBe(502);
      expect(apiErr.code).toBe("HTTP_502");
    }
  });

  it("falls back when body is a plain string", () => {
    const error = makeAxiosResponseError(400, "Bad Request");

    try {
      normalizeError(error);
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const apiErr = e as ApiError;
      expect(apiErr.code).toBe("HTTP_400");
    }
  });

  it("falls back when body has message but no code", () => {
    const error = makeAxiosResponseError(400, {
      message: "Something went wrong",
      // missing 'code'
    });

    try {
      normalizeError(error);
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const apiErr = e as ApiError;
      expect(apiErr.code).toBe("HTTP_400");
    }
  });

  it("falls back when body has code but no message", () => {
    const error = makeAxiosResponseError(400, {
      code: "SOME_CODE",
      // missing 'message'
    });

    try {
      normalizeError(error);
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const apiErr = e as ApiError;
      expect(apiErr.code).toBe("HTTP_400");
    }
  });
});

// ---------------------------------------------------------------------------
// 3. Axios error with no response (network failure)
// ---------------------------------------------------------------------------

describe("normalizeError — network error (no response)", () => {
  it("re-throws the original AxiosError unchanged when no response is present", () => {
    const networkError = new AxiosError(
      "Network Error",
      "ERR_NETWORK",
      { headers: new AxiosHeaders() } as AxiosError["config"],
      {},
      undefined // no response
    );

    expect(() => normalizeError(networkError)).toThrow(AxiosError);

    try {
      normalizeError(networkError);
    } catch (e) {
      // Must NOT be an ApiError — re-thrown as-is
      expect(e).not.toBeInstanceOf(ApiError);
      expect(e).toBeInstanceOf(AxiosError);
      expect((e as AxiosError).message).toBe("Network Error");
    }
  });
});

// ---------------------------------------------------------------------------
// 4. Non-Axios error (re-thrown unchanged)
// ---------------------------------------------------------------------------

describe("normalizeError — non-Axios error", () => {
  it("re-throws a plain Error unchanged", () => {
    const plainError = new Error("Something unexpected");

    expect(() => normalizeError(plainError)).toThrow("Something unexpected");

    try {
      normalizeError(plainError);
    } catch (e) {
      expect(e).toBe(plainError); // exact same reference
      expect(e).not.toBeInstanceOf(ApiError);
    }
  });

  it("re-throws a string unchanged", () => {
    expect(() => normalizeError("raw string error")).toThrow("raw string error");
  });

  it("re-throws null unchanged", () => {
    expect(() => normalizeError(null)).toThrow();

    try {
      normalizeError(null);
    } catch (e) {
      expect(e).toBeNull();
    }
  });
});
