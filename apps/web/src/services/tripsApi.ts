/**
 * OntDekker Trips API
 *
 * All API calls for /api/v1/trips (expedition-service, trip-centric surface).
 * Traefik routes /api/v1/trips/* → expedition-service.
 *
 * Endpoints:
 *   POST   /api/v1/trips
 *   GET    /api/v1/trips
 *   GET    /api/v1/trips/{id}
 *   PUT    /api/v1/trips/{id}
 *   DELETE /api/v1/trips/{id}
 *   POST   /api/v1/trips/{id}/join
 *   POST   /api/v1/trips/{id}/leave
 *   GET    /api/v1/users/me/trips
 */

import apiClient from "./axios";
import type { PaginatedResponse } from "@/types";
import type {
  Trip,
  TripSummary,
  TripParticipant,
  CreateTripRequest,
  UpdateTripRequest,
  TripListParams,
  MyTripsParams,
} from "@/types/trip";

// ---------------------------------------------------------------------------
// CREATE
// ---------------------------------------------------------------------------

export async function createTrip(payload: CreateTripRequest): Promise<Trip> {
  // Convert camelCase fields to snake_case for the backend
  const body = {
    title: payload.title,
    destination: payload.destination,
    description: payload.description ?? null,
    cover_image_url: payload.coverImageUrl ?? null,
    start_date: payload.startDate ?? null,
    end_date: payload.endDate ?? null,
    budget: payload.budget ?? null,
    max_participants: payload.maxParticipants,
    visibility: payload.visibility,
    community_id: payload.communityId ?? null,
  };
  const { data } = await apiClient.post<Trip>("/api/v1/trips", body);
  return data;
}

// ---------------------------------------------------------------------------
// LIST
// ---------------------------------------------------------------------------

export async function getTrips(
  params: TripListParams = {},
): Promise<PaginatedResponse<TripSummary>> {
  const { data } = await apiClient.get<PaginatedResponse<TripSummary>>(
    "/api/v1/trips",
    { params },
  );
  return data;
}

// ---------------------------------------------------------------------------
// GET single
// ---------------------------------------------------------------------------

export async function getTripById(tripId: string): Promise<Trip> {
  const { data } = await apiClient.get<Trip>(`/api/v1/trips/${tripId}`);
  return data;
}

// ---------------------------------------------------------------------------
// UPDATE
// ---------------------------------------------------------------------------

export async function updateTrip(
  tripId: string,
  payload: UpdateTripRequest,
): Promise<Trip> {
  const body = {
    ...(payload.title !== undefined && { title: payload.title }),
    ...(payload.destination !== undefined && { destination: payload.destination }),
    ...(payload.description !== undefined && { description: payload.description }),
    ...(payload.coverImageUrl !== undefined && { cover_image_url: payload.coverImageUrl }),
    ...(payload.startDate !== undefined && { start_date: payload.startDate }),
    ...(payload.endDate !== undefined && { end_date: payload.endDate }),
    ...(payload.budget !== undefined && { budget: payload.budget }),
    ...(payload.maxParticipants !== undefined && { max_participants: payload.maxParticipants }),
    ...(payload.visibility !== undefined && { visibility: payload.visibility }),
  };
  const { data } = await apiClient.put<Trip>(`/api/v1/trips/${tripId}`, body);
  return data;
}

// ---------------------------------------------------------------------------
// DELETE
// ---------------------------------------------------------------------------

export async function deleteTrip(tripId: string): Promise<void> {
  await apiClient.delete(`/api/v1/trips/${tripId}`);
}

// ---------------------------------------------------------------------------
// JOIN
// ---------------------------------------------------------------------------

export async function joinTrip(tripId: string): Promise<void> {
  await apiClient.post(`/api/v1/trips/${tripId}/join`);
}

// ---------------------------------------------------------------------------
// LEAVE
// ---------------------------------------------------------------------------

export async function leaveTrip(tripId: string): Promise<void> {
  await apiClient.post(`/api/v1/trips/${tripId}/leave`);
}

// ---------------------------------------------------------------------------
// MY TRIPS
// ---------------------------------------------------------------------------

export async function getMyTrips(
  params: MyTripsParams = {},
): Promise<PaginatedResponse<TripSummary>> {
  const { data } = await apiClient.get<PaginatedResponse<TripSummary>>(
    "/api/v1/users/me/trips",
    { params },
  );
  return data;
}

// ---------------------------------------------------------------------------
// PARTICIPANTS
// ---------------------------------------------------------------------------

/**
 * Fetch the participant list for a trip.
 *
 * The expedition-service stores trips and participants in the same database.
 * The trip ID is the same as the expedition ID, so participants are still
 * fetched from /expeditions/api/v1/expeditions/{id}/participants.
 */
export async function getTripParticipants(tripId: string): Promise<TripParticipant[]> {
  const { data } = await apiClient.get<TripParticipant[]>(
    `/expeditions/api/v1/expeditions/${tripId}/participants`,
  );
  return data;
}

/**
 * Fetch the current authenticated user's participant record for a trip.
 *
 * Returns null if the user is not a participant (not registered, not organizer).
 * Returns a TripParticipant with role=ORGANIZER if the user created the trip.
 * Returns a TripParticipant with role=PARTICIPANT if the user has joined.
 *
 * Uses GET /api/v1/trips/{id}/me/participant — never throws 404 for non-membership.
 */
export async function getMyParticipantStatus(
  tripId: string,
): Promise<TripParticipant | null> {
  const { data } = await apiClient.get<TripParticipant | null>(
    `/api/v1/trips/${tripId}/me/participant`,
  );
  return data ?? null;
}

// ---------------------------------------------------------------------------
// DISCUSSION
// ---------------------------------------------------------------------------

/**
 * Fetch paginated discussion messages for a trip.
 *
 * GET /api/v1/trips/{tripId}/discussion
 *
 * Returns messages ordered oldest → newest.
 * author_id on each message is the JWT sub; display names must be resolved
 * separately via batchProfilesByAuth().
 */
export async function getTripDiscussion(
  tripId: string,
  params: { page?: number; pageSize?: number } = {},
): Promise<import("@/types/trip").DiscussionListResponse> {
  const { data } = await apiClient.get(
    `/api/v1/trips/${tripId}/discussion`,
    { params },
  );
  return data;
}

/**
 * Post a new discussion message to a trip.
 *
 * POST /api/v1/trips/{tripId}/discussion
 *
 * The caller must be an active participant or organizer.
 * author_id is always derived server-side from the JWT — never sent in the body.
 */
export async function postDiscussionMessage(
  tripId: string,
  content: string,
): Promise<import("@/types/trip").DiscussionMessage> {
  const { data } = await apiClient.post(
    `/api/v1/trips/${tripId}/discussion`,
    { content },
  );
  return data;
}
