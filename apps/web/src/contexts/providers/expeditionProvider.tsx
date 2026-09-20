"use client";

/**
 * OntDekker — Expedition domain state module
 *
 * Exports the state slice, action union, initial slice values, and the
 * reducer case handler for the Expedition domain.
 *
 * Consumed by AppStateProvider to compose the unified app reducer.
 */

import type { ExpeditionSummary } from "@/types";

// ---------------------------------------------------------------------------
// State slice
// ---------------------------------------------------------------------------

export interface ExpeditionState {
  myExpeditions: ExpeditionSummary[];
}

export const expeditionInitialState: ExpeditionState = {
  myExpeditions: [],
};

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

export type ExpeditionAction =
  | { type: "MY_EXPEDITIONS_LOADED"; expeditions: ExpeditionSummary[] };

// ---------------------------------------------------------------------------
// Reducer cases
// ---------------------------------------------------------------------------

/**
 * Handles Expedition actions.
 * Returns null for unrecognised action types.
 */
export function expeditionReducer<S extends ExpeditionState>(
  state: S,
  action: ExpeditionAction,
): S | null {
  switch (action.type) {
    case "MY_EXPEDITIONS_LOADED":
      return { ...state, myExpeditions: action.expeditions };

    default:
      return null;
  }
}
