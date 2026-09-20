"use client";

/**
 * Application-level provider tree.
 *
 * This is the only client-component boundary needed at the root level.
 * It keeps the root layout (layout.tsx) as a Server Component while
 * still providing React context to the entire tree.
 *
 * Wrapping order (outer → inner):
 *   QueryClientProvider  — TanStack Query server-state management
 *     AuthProvider       — OntDekker authentication state
 */

import { QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/contexts/AuthContext";
import { queryClient } from "@/lib/query";

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}
