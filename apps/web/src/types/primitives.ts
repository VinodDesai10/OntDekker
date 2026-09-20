// ---------------------------------------------------------------------------
// Primitives & shared utilities
// ---------------------------------------------------------------------------

/** ISO-8601 datetime string, e.g. "2026-07-25T02:32:48.126Z" */
export type ISODateString = string;

/** UUID string, e.g. "550e8400-e29b-41d4-a716-446655440000" */
export type UUID = string;

/** Generic key–value map */
export type Dictionary<T = unknown> = Record<string, T>;
