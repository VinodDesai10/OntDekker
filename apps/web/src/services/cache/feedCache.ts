/**
 * OntDekker — Feed Cache Keys
 *
 * SWR key factories for the Feed (Discover) domain.
 */

/** Feed posts (Discover / travel stories) */
export const feedKeys = {
  list: (params: Record<string, unknown> = {}) =>
    ["/feed/api/v1/feed/stories", params] as [string, Record<string, unknown>],
  byId: (id: string) => `/feed/api/v1/feed/stories/${id}`,
  byUser: (userId: string, page = 1) =>
    `/feed/api/v1/feed/users/${userId}?page=${page}`,
  byCommunity: (communityId: string, page = 1) =>
    `/feed/api/v1/feed/communities/${communityId}?page=${page}`,
  comments: (postId: string, page = 1) =>
    `/feed/api/v1/feed/posts/${postId}/comments?page=${page}`,
  /**
   * My Posts — stable TanStack Query key for the authenticated user's own posts.
   * Matches the GET /feed/api/v1/feed/me/posts endpoint.
   * Used as a TanStack Query key on the Profile page so it can be
   * invalidated after create/delete operations in FeedView.
   */
  myPosts: (params: { limit?: number; offset?: number } = {}) =>
    ["feed", "me", "posts", params] as const,
} as const;
