/**
 * Unit tests for runtime contract constants in src/services/users.ts
 *
 * Tests the exported upload constraint constants that guard against
 * unsupported file types/sizes at the frontend layer before upload.
 *
 * These constants must match the backend's ALLOWED_MIME_TYPES and
 * MINIO_MAX_FILE_SIZE as documented in:
 *   services/user-service/app/schemas/user.py
 *
 * Tests:
 *   1. UPLOAD_ACCEPTED_MIME_TYPES contains exactly the supported image types
 *   2. UPLOAD_MAX_BYTES matches the backend's 5 MB limit
 *
 * No network calls. No TypeScript type-only contracts (those are compile-time).
 */

import { describe, it, expect } from "vitest";
import {
  UPLOAD_ACCEPTED_MIME_TYPES,
  UPLOAD_MAX_BYTES,
} from "@/services/users";

// ---------------------------------------------------------------------------
// UPLOAD_ACCEPTED_MIME_TYPES
// ---------------------------------------------------------------------------

describe("UPLOAD_ACCEPTED_MIME_TYPES", () => {
  it("is a readonly array of exactly 3 MIME types", () => {
    expect(Array.isArray(UPLOAD_ACCEPTED_MIME_TYPES)).toBe(true);
    expect(UPLOAD_ACCEPTED_MIME_TYPES.length).toBe(3);
  });

  it("contains image/jpeg", () => {
    expect(UPLOAD_ACCEPTED_MIME_TYPES).toContain("image/jpeg");
  });

  it("contains image/png", () => {
    expect(UPLOAD_ACCEPTED_MIME_TYPES).toContain("image/png");
  });

  it("contains image/webp", () => {
    expect(UPLOAD_ACCEPTED_MIME_TYPES).toContain("image/webp");
  });

  it("contains no other MIME types beyond jpeg/png/webp", () => {
    // Exact set match — order doesn't matter
    const expected = ["image/jpeg", "image/png", "image/webp"];
    expect([...UPLOAD_ACCEPTED_MIME_TYPES].sort()).toEqual(expected.sort());
  });

  it("does not include unsupported formats (gif, svg, bmp)", () => {
    expect(UPLOAD_ACCEPTED_MIME_TYPES).not.toContain("image/gif");
    expect(UPLOAD_ACCEPTED_MIME_TYPES).not.toContain("image/svg+xml");
    expect(UPLOAD_ACCEPTED_MIME_TYPES).not.toContain("image/bmp");
  });
});

// ---------------------------------------------------------------------------
// UPLOAD_MAX_BYTES
// ---------------------------------------------------------------------------

describe("UPLOAD_MAX_BYTES", () => {
  it("is exactly 5 * 1024 * 1024 (5 MB)", () => {
    expect(UPLOAD_MAX_BYTES).toBe(5 * 1024 * 1024);
  });

  it("equals 5,242,880 bytes", () => {
    expect(UPLOAD_MAX_BYTES).toBe(5_242_880);
  });

  it("is a number", () => {
    expect(typeof UPLOAD_MAX_BYTES).toBe("number");
  });

  it("is greater than 1 MB (sanity check)", () => {
    expect(UPLOAD_MAX_BYTES).toBeGreaterThan(1 * 1024 * 1024);
  });

  it("is less than 10 MB (sanity check)", () => {
    expect(UPLOAD_MAX_BYTES).toBeLessThan(10 * 1024 * 1024);
  });
});
