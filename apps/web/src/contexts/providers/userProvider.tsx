"use client";

/**
 * OntDekker — User / Auth domain state module
 *
 * Exports the state slice, action union, initial slice values, and the
 * reducer case handler for the User / Auth domain.
 *
 * Consumed by AppStateProvider to compose the unified app reducer.
 */

import type { AuthUser } from "@/types";

// ---------------------------------------------------------------------------
// State slice
// ---------------------------------------------------------------------------

export interface UserState {
  /** Authenticated user — null while unauthenticated */
  user: AuthUser | null;
  /** Whether the initial auth check has completed */
  isAuthReady: boolean;
}

export const userInitialState: UserState = {
  user: null,
  isAuthReady: false,
};

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

export type UserAction =
  | { type: "AUTH_READY"; user: AuthUser | null }
  | { type: "SIGN_OUT" };

// ---------------------------------------------------------------------------
// Reducer cases
// ---------------------------------------------------------------------------

/**
 * Handles User/Auth actions.
 * Returns null for unrecognised action types so the caller knows to try
 * other domain handlers.
 */
export function userReducer<S extends UserState>(
  state: S,
  action: UserAction,
  resetState: S,
): S | null {
  switch (action.type) {
    case "AUTH_READY":
      return { ...state, isAuthReady: true, user: action.user };

    case "SIGN_OUT":
      return {
        ...resetState,
        isAuthReady: true,
      } as S;

    default:
      return null;
  }
}
