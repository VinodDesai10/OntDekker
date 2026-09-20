"use client";

/**
 * OntDekker — UI flags domain state module — Developer 3 scope
 *
 * Retains only the modal open/close UI flag needed by Guide and Expedition
 * views. Sidebar toggle and notifications drawer have been removed.
 *
 * Consumed by AppStateProvider to compose the unified app reducer.
 */

// ---------------------------------------------------------------------------
// State slice
// ---------------------------------------------------------------------------

export interface UiState {
  isModalOpen: boolean;
}

export const uiInitialState: UiState = {
  isModalOpen: false,
};

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

export type UiAction =
  | { type: "MODAL_OPEN" }
  | { type: "MODAL_CLOSE" };

// ---------------------------------------------------------------------------
// Reducer cases
// ---------------------------------------------------------------------------

/**
 * Handles UI flag actions.
 * Returns null for unrecognised action types.
 */
export function uiReducer<S extends UiState>(
  state: S,
  action: UiAction,
): S | null {
  switch (action.type) {
    case "MODAL_OPEN":
      return { ...state, isModalOpen: true };

    case "MODAL_CLOSE":
      return { ...state, isModalOpen: false };

    default:
      return null;
  }
}
