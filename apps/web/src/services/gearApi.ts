/**
 * OntDekker Gear API — Pack Weight Optimizer
 *
 * Mutation helpers for gear items under
 * /expeditions/api/v1/expeditions/{id}/gear
 *
 * GET is handled by SWR via swrFetcher + expeditionKeys.gear(id).
 * POST / PATCH / DELETE mutations are here so they can be called from
 * useSWRConfig().mutate() invalidation flows.
 *
 * Authorization (enforced by backend):
 *   - GET   : active participant
 *   - POST  : active participant
 *   - PATCH : item adder OR organiser/co-organiser
 *   - DELETE: item adder OR organiser/co-organiser
 */

import apiClient from "./axios";
import type { GearItem } from "@/types";
import type { GearCategory } from "@/types/expedition";

// ---------------------------------------------------------------------------
// Request shapes (snake_case sent to backend before axios transforms)
// ---------------------------------------------------------------------------

export interface AddGearItemRequest {
  name: string;
  category?: GearCategory;
  weightGrams?: number;
  quantity?: number;
  isPacked?: boolean;
}

export interface UpdateGearItemRequest {
  name?: string;
  category?: GearCategory;
  weightGrams?: number;
  quantity?: number;
  isPacked?: boolean;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * Add a gear item to an expedition's packing list.
 *
 * POST /expeditions/api/v1/expeditions/{expeditionId}/gear
 *
 * The caller must be an active participant.
 */
export async function addGearItem(
  expeditionId: string,
  payload: AddGearItemRequest,
): Promise<GearItem> {
  const body = {
    name: payload.name,
    ...(payload.category !== undefined && { category: payload.category }),
    ...(payload.weightGrams !== undefined && { weight_grams: payload.weightGrams }),
    ...(payload.quantity !== undefined && { quantity: payload.quantity }),
    ...(payload.isPacked !== undefined && { is_packed: payload.isPacked }),
  };
  const { data } = await apiClient.post<GearItem>(
    `/expeditions/api/v1/expeditions/${expeditionId}/gear`,
    body,
  );
  return data;
}

/**
 * Update a gear item (partial update).
 *
 * PATCH /expeditions/api/v1/expeditions/{expeditionId}/gear/{itemId}
 *
 * The caller must be the item owner or organiser/co-organiser.
 */
export async function updateGearItem(
  expeditionId: string,
  itemId: string,
  payload: UpdateGearItemRequest,
): Promise<GearItem> {
  const body = {
    ...(payload.name !== undefined && { name: payload.name }),
    ...(payload.category !== undefined && { category: payload.category }),
    ...(payload.weightGrams !== undefined && { weight_grams: payload.weightGrams }),
    ...(payload.quantity !== undefined && { quantity: payload.quantity }),
    ...(payload.isPacked !== undefined && { is_packed: payload.isPacked }),
  };
  const { data } = await apiClient.patch<GearItem>(
    `/expeditions/api/v1/expeditions/${expeditionId}/gear/${itemId}`,
    body,
  );
  return data;
}

/**
 * Delete a gear item.
 *
 * DELETE /expeditions/api/v1/expeditions/{expeditionId}/gear/{itemId}
 *
 * The caller must be the item owner or organiser/co-organiser.
 */
export async function deleteGearItem(
  expeditionId: string,
  itemId: string,
): Promise<void> {
  await apiClient.delete(
    `/expeditions/api/v1/expeditions/${expeditionId}/gear/${itemId}`,
  );
}
