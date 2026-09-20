import type { UUID, ISODateString } from "./primitives";

// ---------------------------------------------------------------------------
// Community enumerations
// ---------------------------------------------------------------------------

export type CommunityVisibility = "PUBLIC" | "PRIVATE";

export type CommunityStatus = "ACTIVE" | "ARCHIVED" | "DELETED";

export type MemberRole = "OWNER" | "MODERATOR" | "MEMBER";

export type MemberStatus = "PENDING" | "ACTIVE" | "BANNED";

/**
 * Authoritative membership status returned by the backend on every
 * CommunitySchema response.  Replaces all ephemeral local state.
 *
 *   NOT_MEMBER  — visitor / logged-out user
 *   PENDING     — has a pending join request (private/approval-required)
 *   MEMBER      — active member (MEMBER role)
 *   CO_HEAD     — active moderator (MODERATOR role)
 *   HEAD        — community owner (OWNER role)
 */
export type MembershipViewStatus =
  | "NOT_MEMBER"
  | "PENDING"
  | "MEMBER"
  | "CO_HEAD"
  | "HEAD";

export type CommunityJoinRequestStatus =
  | "PENDING"
  | "APPROVED"
  | "REJECTED"
  | "CANCELLED";

// ---------------------------------------------------------------------------
// Community interfaces
// (field names here are camelCase — the axios interceptor converts
// snake_case → camelCase so backend's `logo_url` becomes `logoUrl`, etc.)
// ---------------------------------------------------------------------------

export interface Community {
  id: UUID;
  name: string;
  /** URL-safe identifier, e.g. "mountain-trekkers" */
  slug: string;
  description: string | null;
  /** URL to the banner/cover image — from backend banner_url field */
  bannerUrl: string | null;
  /** URL to the logo/profile image — from backend logo_url field */
  logoUrl: string | null;
  visibility: CommunityVisibility;
  location: string | null;
  /** Creator user ID — from backend creator_id */
  creatorId: UUID;
  memberCount: number;
  requiresApproval: boolean;
  /** Whether the current authenticated user is a member */
  isMember: boolean;
  /** Role of the current authenticated user; null when not a member */
  currentUserRole: MemberRole | null;
  /**
   * Authoritative membership status from the backend.
   * Use this instead of isMember + local pendingRequest flags.
   */
  membershipStatus: MembershipViewStatus;
  status: CommunityStatus;
  rules: CommunityRule[];
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

/**
 * Lightweight community summary returned by the list endpoint.
 * NOTE: The backend CommunitySummarySchema does not include bannerUrl.
 */
export interface CommunitySummary {
  id: UUID;
  name: string;
  slug: string;
  description: string | null;
  logoUrl: string | null;
  visibility: CommunityVisibility;
  location: string | null;
  memberCount: number;
  requiresApproval: boolean;
  isMember: boolean;
  status: CommunityStatus;
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

// ---------------------------------------------------------------------------
// Community Rule interface
// ---------------------------------------------------------------------------

export interface CommunityRule {
  id: UUID;
  communityId: UUID;
  title: string;
  description: string | null;
  /** Display sort order (1-based) — from backend order_index */
  orderIndex: number;
}

// ---------------------------------------------------------------------------
// Request shapes for mutations
// ---------------------------------------------------------------------------

export interface CreateCommunityRequest {
  name: string;
  description?: string | null;
  visibility: CommunityVisibility;
  location?: string | null;
  /** If true, new members require approval before joining */
  requires_approval?: boolean;
}

export interface UpdateCommunityRequest {
  name?: string;
  description?: string | null;
  visibility?: CommunityVisibility;
  location?: string | null;
  requires_approval?: boolean;
}

// ---------------------------------------------------------------------------
// Filter parameter types (mirrored from backend query schemas)
// ---------------------------------------------------------------------------

/**
 * Query filters for the community directory endpoint.
 * The backend supports: limit, offset, search, location, visibility
 */
export interface CommunityFilter {
  limit?: number;
  offset?: number;
  search?: string;
  location?: string;
  visibility?: CommunityVisibility;
}

// ---------------------------------------------------------------------------
// Membership types — CP-2
// ---------------------------------------------------------------------------

export type MembershipStatus = "ACTIVE" | "LEFT" | "REMOVED" | "BANNED";

/**
 * A community member record as returned by GET /{id}/members.
 * NOTE: The backend only returns user_id, not profile data.
 * Display name / username / avatar must be resolved separately
 * from the user-service if available, or derived from context.
 */
export interface CommunityMember {
  id: UUID;
  communityId: UUID;
  userId: UUID;
  role: MemberRole;
  status: MembershipStatus;
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

/** Paginated response from GET /{id}/members */
export interface MemberListResponse {
  members: CommunityMember[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

/** Result of POST /{id}/join for a public community */
export interface JoinResult {
  joined?: boolean;
  requested?: boolean;
  requestId?: UUID;
}

/** A join request record as returned by GET /{id}/join-requests */
export interface CommunityJoinRequest {
  id: UUID;
  communityId: UUID;
  requesterId: UUID;
  message: string | null;
  status: CommunityJoinRequestStatus;
  reviewedBy: UUID | null;
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

/** Paginated response from GET /{id}/join-requests */
export interface JoinRequestListResponse {
  requests: CommunityJoinRequest[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

/** Request body for PUT /join-requests/{id} */
export interface JoinRequestActionRequest {
  action: "approve" | "reject";
}

/** Request body for PUT /{id}/members/{userId}/role */
export interface MemberRoleUpdateRequest {
  /** Backend enum: MODERATOR | MEMBER (OWNER blocked by backend validator) */
  role: "MODERATOR" | "MEMBER";
}
