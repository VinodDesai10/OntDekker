/**
 * OntDekker Community API Functions
 *
 * All API calls for the Community Service (Developer 2 scope).
 * Follows the same pattern as guideApi.ts and expeditionApi.ts.
 *
 * Endpoint mapping:
 *   Communities : /communities/api/v1/communities/*
 *
 * All paths are relative to the Traefik gateway base URL configured
 * in axios.ts (NEXT_PUBLIC_API_BASE_URL).
 *
 * NOTE ON RESPONSE SHAPES
 * The Community Service uses its own pagination envelope:
 *   { communities: [...], total, limit, offset, has_more }
 * This differs from the generic PaginatedResponse<T> used elsewhere.
 * getCommunities() normalises the shape so callers see a consistent
 * CommunitiesPage type (defined below).
 *
 * NOTE ON MEDIA UPLOADS
 * Community images are uploaded using a 2-step presigned URL flow:
 *   1. POST /{id}/logo/upload-url  →  { upload_url, object_key, expires_in }
 *   2. PUT binary to `upload_url`  (directly to MinIO, no auth header)
 *   3. PUT /{id}/logo with { object_key } to persist
 * Same flow applies for banners via /{id}/banner/upload-url and /{id}/banner.
 */

import apiClient from "./axios";
import type {
  Community,
  CommunitySummary,
  CreateCommunityRequest,
  UpdateCommunityRequest,
  CommunityFilter,
  CommunityMember,
  MemberListResponse,
  JoinResult,
  CommunityJoinRequest,
  JoinRequestListResponse,
  JoinRequestActionRequest,
  MemberRoleUpdateRequest,
} from "@/types";

// ---------------------------------------------------------------------------
// Community-specific pagination response
// (Backend envelope differs from the generic PaginatedResponse<T>)
// ---------------------------------------------------------------------------

export interface CommunitiesPage {
  communities: CommunitySummary[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

// ---------------------------------------------------------------------------
// Media upload types (matching backend MediaUploadRequest / MediaUploadResponse)
// ---------------------------------------------------------------------------

export interface CommunityUploadUrlRequest {
  /** Original filename — used to extract the file extension on the server */
  filename: string;
  /** MIME type, e.g. "image/jpeg" */
  content_type: string;
}

export interface CommunityUploadUrlResponse {
  /** Presigned PUT URL to upload the binary directly to MinIO */
  uploadUrl: string;
  /** Object key to pass back to the backend after upload */
  objectKey: string;
  /** Seconds until the presigned URL expires (typically 3600) */
  expiresIn: number;
}

// ---------------------------------------------------------------------------
// Communities
// ---------------------------------------------------------------------------

/**
 * Fetch paginated community directory.
 *
 * Query params supported by the backend:
 *   limit, offset, search, location, visibility
 */
export async function getCommunities(
  filters: Partial<CommunityFilter> = {},
): Promise<CommunitiesPage> {
  const { data } = await apiClient.get("/communities/api/v1/communities", {
    params: filters,
  });
  // The axios response interceptor converts snake_case → camelCase so
  // has_more → hasMore already.  We return the data directly.
  return data as CommunitiesPage;
}

/** Fetch a single community's full detail */
export async function getCommunityById(
  communityId: string,
): Promise<Community> {
  const { data } = await apiClient.get(
    `/communities/api/v1/communities/${communityId}`,
  );
  return data as Community;
}

/** Create a new community. Returns the newly created community. */
export async function createCommunity(
  payload: CreateCommunityRequest,
): Promise<Community> {
  const { data } = await apiClient.post(
    "/communities/api/v1/communities",
    payload,
  );
  return data as Community;
}

/** Update an existing community */
export async function updateCommunity(
  communityId: string,
  payload: UpdateCommunityRequest,
): Promise<Community> {
  const { data } = await apiClient.put(
    `/communities/api/v1/communities/${communityId}`,
    payload,
  );
  return data as Community;
}

/** Archive (soft-delete) a community */
export async function archiveCommunity(communityId: string): Promise<void> {
  await apiClient.delete(`/communities/api/v1/communities/${communityId}`);
}

// ---------------------------------------------------------------------------
// Community media — presigned URL generation + persistence
// ---------------------------------------------------------------------------

/**
 * Step 1a — Request a presigned PUT URL for a community LOGO.
 * POST /communities/api/v1/communities/{id}/logo/upload-url
 *
 * OWNER only. Call AFTER the community has been created.
 */
export async function getLogoUploadUrl(
  communityId: string,
  request: CommunityUploadUrlRequest,
): Promise<CommunityUploadUrlResponse> {
  const { data } = await apiClient.post(
    `/communities/api/v1/communities/${communityId}/logo/upload-url`,
    request,
  );
  return data as CommunityUploadUrlResponse;
}

/**
 * Step 2a — Upload the logo binary directly to MinIO.
 * PUT <presignedUrl>  (no Authorization header — MinIO validates via query params)
 */
export async function uploadLogoToStorage(
  presignedUrl: string,
  file: File,
): Promise<void> {
  const response = await fetch(presignedUrl, {
    method: "PUT",
    body: file,
    headers: {
      "Content-Type": file.type,
    },
  });
  if (!response.ok) {
    throw new Error(
      `Failed to upload logo to storage (HTTP ${response.status}). Check that MinIO is running and accessible on port 9000.`,
    );
  }
}

/**
 * Step 3a — Persist the logo object key so the backend stores the URL.
 * PUT /communities/api/v1/communities/{id}/logo
 */
export async function persistCommunityLogo(
  communityId: string,
  objectKey: string,
): Promise<Community> {
  const { data } = await apiClient.put(
    `/communities/api/v1/communities/${communityId}/logo`,
    { object_key: objectKey },
  );
  return data as Community;
}

/**
 * Step 1b — Request a presigned PUT URL for a community BANNER.
 * POST /communities/api/v1/communities/{id}/banner/upload-url
 *
 * OWNER only. Call AFTER the community has been created.
 */
export async function getBannerUploadUrl(
  communityId: string,
  request: CommunityUploadUrlRequest,
): Promise<CommunityUploadUrlResponse> {
  const { data } = await apiClient.post(
    `/communities/api/v1/communities/${communityId}/banner/upload-url`,
    request,
  );
  return data as CommunityUploadUrlResponse;
}

/**
 * Step 2b — Upload the banner binary directly to MinIO.
 */
export async function uploadBannerToStorage(
  presignedUrl: string,
  file: File,
): Promise<void> {
  const response = await fetch(presignedUrl, {
    method: "PUT",
    body: file,
    headers: {
      "Content-Type": file.type,
    },
  });
  if (!response.ok) {
    throw new Error(
      `Failed to upload banner to storage (HTTP ${response.status}). Check that MinIO is running and accessible on port 9000.`,
    );
  }
}

/**
 * Step 3b — Persist the banner object key so the backend stores the URL.
 * PUT /communities/api/v1/communities/{id}/banner
 */
export async function persistCommunityBanner(
  communityId: string,
  objectKey: string,
): Promise<Community> {
  const { data } = await apiClient.put(
    `/communities/api/v1/communities/${communityId}/banner`,
    { object_key: objectKey },
  );
  return data as Community;
}

/**
 * High-level helper: upload a logo through the full 3-step flow.
 * Returns the updated Community after persistence.
 */
export async function uploadCommunityLogo(
  communityId: string,
  file: File,
): Promise<Community> {
  const { uploadUrl, objectKey } = await getLogoUploadUrl(communityId, {
    filename: file.name,
    content_type: file.type,
  });
  await uploadLogoToStorage(uploadUrl, file);
  return persistCommunityLogo(communityId, objectKey);
}

/**
 * High-level helper: upload a banner through the full 3-step flow.
 * Returns the updated Community after persistence.
 */
export async function uploadCommunityBanner(
  communityId: string,
  file: File,
): Promise<Community> {
  const { uploadUrl, objectKey } = await getBannerUploadUrl(communityId, {
    filename: file.name,
    content_type: file.type,
  });
  await uploadBannerToStorage(uploadUrl, file);
  return persistCommunityBanner(communityId, objectKey);
}

// ---------------------------------------------------------------------------
// Membership
// ---------------------------------------------------------------------------

/**
 * Join a community.
 *
 * - Public community (requires_approval=false): immediately returns { joined: true }
 * - Private or approval-required: creates a join request and returns
 *   { requested: true, requestId: UUID }
 *
 * POST /{id}/join
 */
export async function joinCommunity(
  communityId: string,
  payload: { message?: string | null } = {},
): Promise<JoinResult> {
  const { data } = await apiClient.post<JoinResult>(
    `/communities/api/v1/communities/${communityId}/join`,
    payload,
  );
  return data;
}

/**
 * Leave a community.
 * The OWNER (Head) cannot leave — backend returns 400 with validation error.
 *
 * DELETE /{id}/leave
 */
export async function leaveCommunity(communityId: string): Promise<void> {
  await apiClient.delete(
    `/communities/api/v1/communities/${communityId}/leave`,
  );
}

/**
 * List the active members of a community.
 * Private communities: only members can see the list (403 otherwise).
 *
 * GET /{id}/members?limit=&offset=&role=
 */
export async function listMembers(
  communityId: string,
  params: { limit?: number; offset?: number; role?: string } = {},
): Promise<MemberListResponse> {
  const { data } = await apiClient.get<MemberListResponse>(
    `/communities/api/v1/communities/${communityId}/members`,
    { params },
  );
  return data;
}

/**
 * Remove a member from the community.
 * MOD or OWNER only. MODs cannot remove other MODs or the OWNER.
 *
 * DELETE /{id}/members/{userId}
 */
export async function removeMember(
  communityId: string,
  userId: string,
): Promise<void> {
  await apiClient.delete(
    `/communities/api/v1/communities/${communityId}/members/${userId}`,
  );
}

/**
 * Update a member's role.
 * OWNER only. Cannot assign OWNER role via this endpoint.
 *
 * PUT /{id}/members/{userId}/role
 */
export async function updateMemberRole(
  communityId: string,
  userId: string,
  request: MemberRoleUpdateRequest,
): Promise<CommunityMember> {
  const { data } = await apiClient.put<CommunityMember>(
    `/communities/api/v1/communities/${communityId}/members/${userId}/role`,
    request,
  );
  return data;
}

/**
 * List pending join requests.
 * MOD or OWNER only.
 *
 * GET /{id}/join-requests?limit=&offset=
 */
export async function listJoinRequests(
  communityId: string,
  params: { limit?: number; offset?: number } = {},
): Promise<JoinRequestListResponse> {
  const { data } = await apiClient.get<JoinRequestListResponse>(
    `/communities/api/v1/communities/${communityId}/join-requests`,
    { params },
  );
  return data;
}

/**
 * Approve or reject a join request.
 * MOD or OWNER only.
 *
 * PUT /join-requests/{requestId}
 */
export async function actionJoinRequest(
  requestId: string,
  request: JoinRequestActionRequest,
): Promise<CommunityJoinRequest> {
  const { data } = await apiClient.put<CommunityJoinRequest>(
    `/communities/api/v1/communities/join-requests/${requestId}`,
    request,
  );
  return data;
}

/**
 * Cancel the authenticated user's own pending join request.
 * Only the original requester can cancel.
 *
 * DELETE /join-requests/{requestId}/cancel
 */
export async function cancelJoinRequest(requestId: string): Promise<void> {
  await apiClient.delete(
    `/communities/api/v1/communities/join-requests/${requestId}/cancel`,
  );
}

// ---------------------------------------------------------------------------
// My Memberships — communities the authenticated user has joined
// ---------------------------------------------------------------------------

/**
 * Fetch all communities where the currently authenticated user is an active
 * member (isMember === true).
 *
 * Uses the existing list endpoint with a high limit and filters client-side
 * since the backend does not have a dedicated "my communities" endpoint.
 *
 * Returns a lightweight array of CommunitySummary objects suitable for
 * use in community selectors (e.g., the post composer).
 *
 * GET /communities/api/v1/communities?limit=200
 */
export async function getMyMemberships(): Promise<CommunitySummary[]> {
  // Fetch up to 200 communities and filter to those where isMember is true.
  // The backend sets isMember based on the authenticated user from the JWT,
  // so this call must be made while the user is authenticated.
  const { data } = await apiClient.get("/communities/api/v1/communities", {
    params: { limit: 200, offset: 0 },
  });

  // The axios response interceptor converts snake_case → camelCase, so
  // is_member → isMember is already handled.
  const page = data as CommunitiesPage;
  return (page.communities ?? []).filter((c) => c.isMember === true);
}
