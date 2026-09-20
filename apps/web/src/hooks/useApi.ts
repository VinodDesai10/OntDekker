/**
 * useApi
 *
 * Provides access to the configured Axios client with the current user's
 * auth token already injected.  Components that need to make imperative
 * API calls (e.g. form submissions, optimistic updates) use this hook
 * rather than importing apiClient directly.
 *
 * The hook also keeps the auth token in sync: whenever the user in
 * AppState changes, it calls setAuthToken() so the interceptor in
 * axios.ts picks it up for subsequent requests.
 *
 * Usage:
 *   const api = useApi();
 *   await api.post("/expeditions/api/v1/expeditions", payload);
 *
 * For read-only data, prefer useSWR with swrFetcher from cache.ts.
 */

"use client";

import { useEffect } from "react";
import { useAppState } from "@/contexts/AppStateProvider";
import { apiClient, setAuthToken, registerUnauthorizedHandler } from "@/services/axios";
import type { AxiosInstance } from "axios";

export function useApi(): AxiosInstance {
  const { state, dispatch } = useAppState();

  // Sync auth token whenever it changes
  useEffect(() => {
    setAuthToken(state.user?.accessToken ?? null);
  }, [state.user?.accessToken]);

  // Register the unauthorised handler once on mount
  useEffect(() => {
    registerUnauthorizedHandler(() => {
      dispatch({ type: "SIGN_OUT" });
    });
  }, [dispatch]);

  return apiClient;
}
