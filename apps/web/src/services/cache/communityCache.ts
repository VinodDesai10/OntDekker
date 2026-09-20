/**
 * OntDekker — Community Cache Keys
 *
 * SWR key factories for the Community domain.
 * Keys are structured as tuples [url, params] for swrFetcherWithParams
 * and plain strings for swrFetcher.
 */

/** Communities */
export const communityKeys = {
  list: (params: Record<string, unknown> = {}) =>
    ["/communities/api/v1/communities", params] as [
      string,
      Record<string, unknown>,
    ],
  byId: (id: string) => `/communities/api/v1/communities/${id}`,
  discussions: (id: string, page = 1) =>
    `/communities/api/v1/communities/${id}/discussions?limit=5&offset=${(page - 1) * 5}`,

  /**
   * Members list key — returns a [url, params] tuple for swrFetcherWithParams.
   * Keyed by communityId so mutations can revalidate precisely.
   */
  members: (id: string, params: Record<string, unknown> = {}) =>
    [`/communities/api/v1/communities/${id}/members`, params] as [
      string,
      Record<string, unknown>,
    ],

  /**
   * Join requests list key — MOD/OWNER-only endpoint.
   * Returns a [url, params] tuple.
   */
  joinRequests: (id: string, params: Record<string, unknown> = {}) =>
    [`/communities/api/v1/communities/${id}/join-requests`, params] as [
      string,
      Record<string, unknown>,
    ],
} as const;
