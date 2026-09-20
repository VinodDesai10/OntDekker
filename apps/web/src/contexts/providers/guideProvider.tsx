"use client";

/**
 * OntDekker — Guide domain state module
 *
 * Exports the state slice, action union, initial slice values, and the
 * reducer case handler for the Guide domain.
 *
 * Consumed by AppStateProvider to compose the unified app reducer.
 */

import type { GuideProfileSummary } from "@/types";

// ---------------------------------------------------------------------------
// State slice
// ---------------------------------------------------------------------------

export interface GuideState {
  savedGuides: GuideProfileSummary[];
}

export const guideInitialState: GuideState = {
  savedGuides: [],
};

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

export type GuideAction =
  | { type: "SAVED_GUIDES_LOADED"; guides: GuideProfileSummary[] }
  | { type: "GUIDE_BOOKMARK_TOGGLED"; guideId: string; bookmarked: boolean };

// ---------------------------------------------------------------------------
// Reducer cases
// ---------------------------------------------------------------------------

/**
 * Handles Guide actions.
 * Returns null for unrecognised action types.
 */
export function guideReducer<S extends GuideState>(
  state: S,
  action: GuideAction,
): S | null {
  switch (action.type) {
    case "SAVED_GUIDES_LOADED":
      return { ...state, savedGuides: action.guides };

    case "GUIDE_BOOKMARK_TOGGLED":
      return {
        ...state,
        savedGuides: action.bookmarked
          ? state.savedGuides
          : state.savedGuides.filter((g) => g.id !== action.guideId),
      };

    default:
      return null;
  }
}
