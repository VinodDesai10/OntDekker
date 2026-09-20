/**
 * OntDekker Guide API Functions
 *
 * All API calls for the Guide Service (Developer 3 scope).
 *
 * URL prefix: /guides/api/v1/guides
 *   Next.js rewrites /guides/api/:path* → http://guide-service:8000/api/:path*
 *   This applies to both SWR reads (swrFetcher) and direct apiClient mutations,
 *   ensuring all guide requests are proxied correctly in local Docker dev.
 *
 * Endpoint mapping (all paths use the /guides/api proxy prefix):
 *   GET    /guides/api/v1/guides                          — browse guide directory
 *   GET    /guides/api/v1/guides/{id}                     — get single guide profile
 *   PUT    /guides/api/v1/guides/{id}                     — update own profile
 *   POST   /guides/api/v1/guides/apply                    — submit guide application
 *   GET    /guides/api/v1/guides/apply                    — get own application
 *   POST   /guides/api/v1/guides/{id}/verify              — admin: verify a guide
 *   GET    /guides/api/v1/guides/{id}/specializations     — list specializations
 *   POST   /guides/api/v1/guides/{id}/specializations     — add specialization
 *   DELETE /guides/api/v1/guides/{id}/specializations/{s} — remove specialization
 */

import apiClient from "./axios";
import type {
  ApiResponse,
  PaginatedResponse,
  GuideProfileSummary,
  GuideProfile,
  GuideReview,
  GuideRatingSummary,
  GuideFilter,
  GuideApplicationCreate,
  GuideApplicationResponse,
  GuideSpecialization,
  TravelConnectionListResponse,
} from "@/types";

/** Proxy prefix — matches the Next.js rewrite: /guides/api/:path* → guide-service */
const BASE = "/guides/api/v1/guides";

// ---------------------------------------------------------------------------
// Guide directory
// ---------------------------------------------------------------------------

/** Fetch paginated guide directory */
export async function getGuides(
  filters: Partial<GuideFilter> = {},
): Promise<PaginatedResponse<GuideProfileSummary>> {
  const { data } = await apiClient.get<PaginatedResponse<GuideProfileSummary>>(
    BASE,
    { params: filters },
  );
  return data;
}

/** Fetch a single guide's full profile */
export async function getGuideById(
  guideId: string,
): Promise<ApiResponse<GuideProfile>> {
  const { data } = await apiClient.get<ApiResponse<GuideProfile>>(
    `${BASE}/${guideId}`,
  );
  return data;
}

/** Update guide's own profile */
export async function updateGuideProfile(
  guideId: string,
  payload: Partial<{
    bio: string;
    profile_image_url: string;
    cover_image_url: string;
    years_experience: number;
    price_per_day: number;
  }>,
): Promise<ApiResponse<GuideProfile>> {
  const { data } = await apiClient.put<ApiResponse<GuideProfile>>(
    `${BASE}/${guideId}`,
    payload,
  );
  return data;
}

// ---------------------------------------------------------------------------
// Guide application
// ---------------------------------------------------------------------------

/** Submit a guide application (creates a DRAFT application) */
export async function applyForGuide(
  payload: GuideApplicationCreate,
): Promise<GuideApplicationResponse> {
  const { data } = await apiClient.post<GuideApplicationResponse>(
    `${BASE}/apply`,
    payload,
  );
  return data;
}

/** Get the current user's own guide application */
export async function getMyGuideApplication(): Promise<GuideApplicationResponse> {
  const { data } = await apiClient.get<GuideApplicationResponse>(
    `${BASE}/apply`,
  );
  return data;
}

/** Submit a DRAFT application for review */
export async function submitGuideApplication(
  applicationId: string,
): Promise<GuideApplicationResponse> {
  const { data } = await apiClient.post<GuideApplicationResponse>(
    `${BASE}/apply/${applicationId}/submit`,
  );
  return data;
}

// ---------------------------------------------------------------------------
// Admin verification
// ---------------------------------------------------------------------------

/** Admin: verify a guide profile (PENDING → VERIFIED) */
export async function verifyGuide(
  guideId: string,
): Promise<ApiResponse<GuideProfile>> {
  const { data } = await apiClient.post<ApiResponse<GuideProfile>>(
    `${BASE}/${guideId}/verify`,
  );
  return data;
}

// ---------------------------------------------------------------------------
// Specializations
// ---------------------------------------------------------------------------

/** List all specializations for a guide */
export async function getGuideSpecializations(
  guideId: string,
): Promise<GuideSpecialization[]> {
  const { data } = await apiClient.get<GuideSpecialization[]>(
    `${BASE}/${guideId}/specializations`,
  );
  return data;
}

/** Add a specialization to a guide's profile */
export async function addGuideSpecialization(
  guideId: string,
  category: string,
): Promise<GuideSpecialization> {
  const { data } = await apiClient.post<GuideSpecialization>(
    `${BASE}/${guideId}/specializations`,
    { category },
  );
  return data;
}

/** Remove a specialization from a guide's profile */
export async function removeGuideSpecialization(
  guideId: string,
  specId: string,
): Promise<void> {
  await apiClient.delete(
    `${BASE}/${guideId}/specializations/${specId}`,
  );
}

// ---------------------------------------------------------------------------
// Reviews & ratings
// ---------------------------------------------------------------------------

/** Fetch reviews for a guide */
export async function getGuideReviews(
  guideId: string,
  params: { page?: number; page_size?: number } = {},
): Promise<PaginatedResponse<GuideReview>> {
  const { data } = await apiClient.get<PaginatedResponse<GuideReview>>(
    `${BASE}/${guideId}/reviews`,
    { params },
  );
  return data;
}

/** Fetch aggregated rating summary for a guide */
export async function getGuideRatingSummary(
  guideId: string,
): Promise<GuideRatingSummary> {
  const { data } = await apiClient.get<GuideRatingSummary>(
    `${BASE}/${guideId}/reviews/summary`,
  );
  return data;
}

// ---------------------------------------------------------------------------
// Bookmarks (Travel connections)
// ---------------------------------------------------------------------------

/** Fetch the current user's guide connections (bookmarked guides) */
export async function getMyConnections(
  params: { bookmarked_only?: boolean; page?: number; page_size?: number } = {},
): Promise<TravelConnectionListResponse> {
  const { data } = await apiClient.get<TravelConnectionListResponse>(
    `${BASE}/my-connections`,
    { params },
  );
  return data;
}

/** Bookmark a guide */
export async function bookmarkGuide(guideId: string): Promise<void> {
  await apiClient.post(`${BASE}/${guideId}/bookmark`);
}

/** Remove guide bookmark */
export async function unbookmarkGuide(guideId: string): Promise<void> {
  await apiClient.delete(`${BASE}/${guideId}/bookmark`);
}
