import type { UUID, ISODateString } from "./primitives";

// ---------------------------------------------------------------------------
// Trip enumerations (reuses expedition status/visibility)
// ---------------------------------------------------------------------------

export type TripStatus =
  | "DRAFT"
  | "PUBLISHED"
  | "ACTIVE"
  | "COMPLETED"
  | "CANCELLED"
  | "ARCHIVED";

export type TripVisibility = "PUBLIC" | "PRIVATE";

export type TripParticipantRole = "ORGANIZER" | "CO_ORGANIZER" | "PARTICIPANT";

export type TripParticipantStatus = "ACTIVE" | "LEFT" | "REMOVED";

// ---------------------------------------------------------------------------
// Trip interfaces
// ---------------------------------------------------------------------------

/** Full trip detail — returned by GET /api/v1/trips/{id} */
export interface Trip {
  id: UUID;
  communityId: UUID | null;
  hostId: UUID;
  title: string;
  destination: string;
  description: string | null;
  coverImageUrl: string | null;
  startDate: string | null;
  endDate: string | null;
  budget: number | null;
  maxParticipants: number;
  currentParticipantsCount: number;
  visibility: TripVisibility;
  status: TripStatus;
  hostName: string | null;
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

/**
 * A single participant record — returned by
 * GET /expeditions/api/v1/expeditions/{id}/participants.
 *
 * Note: user_id and role are the only fields available until the
 * user-service integration is implemented. Display names must be
 * fetched separately (future CP-TRIP-2B-2).
 */
export interface TripParticipant {
  id: UUID;
  expedition_id: UUID;
  user_id: UUID;
  role: TripParticipantRole;
  status: TripParticipantStatus;
  joined_at: ISODateString;
  created_at: ISODateString;
  updated_at: ISODateString;
}

/** Lightweight card — returned by GET /api/v1/trips list */
export interface TripSummary {
  id: UUID;
  communityId: UUID | null;
  hostId: UUID;
  title: string;
  destination: string;
  coverImageUrl: string | null;
  startDate: string | null;
  endDate: string | null;
  budget: number | null;
  maxParticipants: number;
  currentParticipantsCount: number;
  visibility: TripVisibility;
  status: TripStatus;
  hostName: string | null;
  createdAt: ISODateString;
}

// ---------------------------------------------------------------------------
// Request shapes
// ---------------------------------------------------------------------------

export interface CreateTripRequest {
  title: string;
  destination: string;
  description?: string | null;
  coverImageUrl?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  budget?: number | null;
  maxParticipants: number;
  visibility: TripVisibility;
  communityId?: string | null;
}

export interface UpdateTripRequest {
  title?: string;
  destination?: string;
  description?: string | null;
  coverImageUrl?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  budget?: number | null;
  maxParticipants?: number;
  visibility?: TripVisibility;
}

// ---------------------------------------------------------------------------
// Filter params
// ---------------------------------------------------------------------------

export interface TripListParams {
  search?: string;
  community_id?: string;
  personal_only?: boolean;
  status?: TripStatus;
  page?: number;
  page_size?: number;
}

export interface MyTripsParams {
  status?: TripStatus;
  page?: number;
  page_size?: number;
}

// ---------------------------------------------------------------------------
// Discussion
// ---------------------------------------------------------------------------

/**
 * A single expedition discussion message.
 * Returned by GET and POST /api/v1/trips/{id}/discussion.
 *
 * authorId is the JWT sub (auth-service UUID).
 * Display name / avatar must be resolved separately via
 * batchProfilesByAuth([authorId, ...]).
 */
export interface DiscussionMessage {
  id: UUID;
  expeditionId: UUID;
  authorId: UUID;
  content: string;
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

/** Paginated list response from GET /api/v1/trips/{id}/discussion */
export interface DiscussionListResponse {
  items: DiscussionMessage[];
  pagination: {
    page: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
}

/** Request body for POST /api/v1/trips/{id}/discussion */
export interface PostDiscussionMessageRequest {
  content: string;
}
