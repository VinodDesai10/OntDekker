/**
 * OntDekker — Trip SWR Cache Keys
 */

export const tripKeys = {
  all: (params: Record<string, unknown> = {}) =>
    ["/api/v1/trips", params] as [string, Record<string, unknown>],
  byId: (id: string) => `/api/v1/trips/${id}`,
  mine: (params: Record<string, unknown> = {}) =>
    ["/api/v1/users/me/trips", params] as [string, Record<string, unknown>],
} as const;
