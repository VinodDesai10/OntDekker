/**
 * OntDekker — Expedition Cache Keys
 *
 * SWR key factories for the Expedition domain.
 */

/** Expeditions */
export const expeditionKeys = {
  mine: (params: Record<string, unknown> = {}) =>
    ["/expeditions/api/v1/expeditions", params] as [string, Record<string, unknown>],
  byId: (id: string) => `/expeditions/api/v1/expeditions/${id}`,
  gear: (id: string) => `/expeditions/api/v1/expeditions/${id}/gear`,
  gallery: (id: string) => `/expeditions/api/v1/expeditions/${id}/gallery`,
  participants: (id: string) =>
    `/expeditions/api/v1/expeditions/${id}/participants`,
  itinerary: (id: string) =>
    `/expeditions/api/v1/expeditions/${id}/itinerary`,
} as const;
