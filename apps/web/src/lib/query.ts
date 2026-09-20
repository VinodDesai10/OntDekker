import { QueryClient } from "@tanstack/react-query";

/**
 * Shared QueryClient instance.
 *
 * Conservative defaults:
 *   - staleTime 60s  : data stays fresh for 1 minute before background refetch
 *   - retry 1        : retry once on network/server error before surfacing failure
 *   - refetchOnWindowFocus false : avoids unexpected refetches during development
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
