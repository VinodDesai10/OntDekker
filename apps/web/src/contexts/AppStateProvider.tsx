"use client";

/**
 * OntDekker AppStateProvider — Developer 3 scope
 *
 * Centralized state container for the Guide and Expedition features.
 * Slices retained: user/auth, expedition, guide, ui.
 *
 * Usage:
 *   const { state, dispatch } = useAppState();
 */

import React, { createContext, useContext, useReducer } from "react";

import {
  type UserState,
  type UserAction,
  userInitialState,
  userReducer,
} from "./providers/userProvider";
import {
  type ExpeditionState,
  type ExpeditionAction,
  expeditionInitialState,
  expeditionReducer,
} from "./providers/expeditionProvider";
import {
  type GuideState,
  type GuideAction,
  guideInitialState,
  guideReducer,
} from "./providers/guideProvider";
import {
  type UiState,
  type UiAction,
  uiInitialState,
  uiReducer,
} from "./providers/uiProvider";

// ---------------------------------------------------------------------------
// State shape
// ---------------------------------------------------------------------------

export interface AppState
  extends UserState,
    ExpeditionState,
    GuideState,
    UiState {}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

export type AppAction =
  | UserAction
  | ExpeditionAction
  | GuideAction
  | UiAction;

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------

const initialState: AppState = {
  ...userInitialState,
  ...expeditionInitialState,
  ...guideInitialState,
  ...uiInitialState,
};

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

function appReducer(state: AppState, action: AppAction): AppState {
  const fromUser = userReducer(state, action as UserAction, initialState);
  if (fromUser !== null) return fromUser;

  const fromExpedition = expeditionReducer(state, action as ExpeditionAction);
  if (fromExpedition !== null) return fromExpedition;

  const fromGuide = guideReducer(state, action as GuideAction);
  if (fromGuide !== null) return fromGuide;

  const fromUi = uiReducer(state, action as UiAction);
  if (fromUi !== null) return fromUi;

  return state;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface AppStateContextValue {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
}

const AppStateContext = createContext<AppStateContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  return (
    <AppStateContext.Provider value={{ state, dispatch }}>
      {children}
    </AppStateContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAppState(): AppStateContextValue {
  const ctx = useContext(AppStateContext);
  if (!ctx) {
    throw new Error("useAppState must be used inside <AppStateProvider>");
  }
  return ctx;
}
