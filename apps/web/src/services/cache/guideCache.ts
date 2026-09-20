/**
 * OntDekker — Guide Cache Keys
 *
 * SWR key factories for the Guide domain.
 */

/** Guides */
export const guideKeys = {
  list: (params: Record<string, unknown> = {}) =>
    ["/guides/api/v1/guides", params] as [string, Record<string, unknown>],
  byId: (id: string) => `/guides/api/v1/guides/${id}`,
  reviews: (id: string, page = 1) =>
    `/guides/api/v1/guides/${id}/reviews?page=${page}`,
  ratingSummary: (id: string) =>
    `/guides/api/v1/guides/${id}/reviews/summary`,
  myConnections: () => `/guides/api/v1/guides/my-connections`,
} as const;
