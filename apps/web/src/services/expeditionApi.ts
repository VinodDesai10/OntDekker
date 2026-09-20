/**
 * OntDekker Expedition API Functions
 *
 * All API calls for the Expedition Service (Developer 3 scope).
 * Extracted from the monolithic api.ts as part of the service-layer split.
 *
 * Endpoint mapping:
 *   Expeditions : GET  /expeditions/api/v1/expeditions
 *
 * All paths are relative to the Traefik gateway base URL configured
 * in axios.ts (NEXT_PUBLIC_API_BASE_URL).
 */

import apiClient from "./axios";
import type {
  PaginatedResponse,
  Expedition,
  ExpeditionSummary,
  GearItem,
  GalleryPhoto,
  PackWeightSummary,
} from "@/types";

// ---------------------------------------------------------------------------
// Types for filter / pagination params
// ---------------------------------------------------------------------------

export interface ExpeditionParams {
  community_id?: string;
  organizer_id?: string;
  status?: string;
  visibility?: string;
  page?: number;
  page_size?: number;
}

// ---------------------------------------------------------------------------
// Expeditions
// ---------------------------------------------------------------------------

/** Fetch my expeditions (as participant or organiser) */
export async function getMyTrips(
  params: ExpeditionParams = {},
): Promise<PaginatedResponse<ExpeditionSummary>> {
  const { data } = await apiClient.get("/expeditions/api/v1/expeditions", {
    params,
  });
  return data;
}

/** Fetch a single expedition by ID */
export async function getExpeditionById(
  expeditionId: string,
): Promise<Expedition> {
  const { data } = await apiClient.get(
    `/expeditions/api/v1/expeditions/${expeditionId}`,
  );
  // Backend wraps the response: { success, message, data: Expedition }
  return (data as { data: Expedition }).data;
}

/** Fetch gear list for an expedition */
export async function getExpeditionGear(expeditionId: string): Promise<{
  expeditionId: string;
  items: GearItem[];
  summary: PackWeightSummary;
}> {
  const { data } = await apiClient.get(
    `/expeditions/api/v1/expeditions/${expeditionId}/gear`,
  );
  return data;
}

/** Fetch gallery photos for an expedition */
export async function getExpeditionGallery(
  expeditionId: string,
): Promise<{ expeditionId: string; photos: GalleryPhoto[]; totalPhotos: number }> {
  const { data } = await apiClient.get(
    `/expeditions/api/v1/expeditions/${expeditionId}/gallery`,
  );
  return data;
}

/** Request to join a public expedition */
export async function joinExpedition(
  expeditionId: string,
  message?: string,
): Promise<void> {
  await apiClient.post(
    `/expeditions/api/v1/expeditions/${expeditionId}/join`,
    { message },
  );
}

/** Leave an expedition */
export async function leaveExpedition(expeditionId: string): Promise<void> {
  await apiClient.delete(
    `/expeditions/api/v1/expeditions/${expeditionId}/leave`,
  );
}
