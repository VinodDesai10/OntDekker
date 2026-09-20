"use client";

/**
 * OntDekker TripsView
 *
 * Public trips discovery page — entry from Sidebar "Trips".
 *
 * Sections:
 *   - Header + Create Trip button
 *   - Search bar
 *   - Filter chips: All / Community / Personal
 *   - 3-column responsive TripCard grid
 *   - Loading / empty / error states
 *
 * Data: useSWR(tripKeys.all(params)) → PaginatedResponse<TripSummary>
 */

import React, { useState, useMemo, useCallback } from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "motion/react";
import { Compass, Plus, RefreshCw, Search } from "lucide-react";
import { useRouter } from "next/navigation";

import TripCard from "@/components/cards/TripCard";
import Button from "@/components/feedback/Button";
import { swrFetcherWithParams, tripKeys } from "@/services/cache";
import TripCardSkeleton from "./TripCardSkeleton";
import CreateTripModal from "./CreateTripModal";

import type { PaginatedResponse } from "@/types";
import type { TripSummary } from "@/types/trip";

// ---------------------------------------------------------------------------
// Filter types
// ---------------------------------------------------------------------------

type TripFilter = "all" | "community" | "personal";

const FILTER_LABELS: Record<TripFilter, string> = {
  all: "All Trips",
  community: "Community",
  personal: "Personal",
};

// ---------------------------------------------------------------------------
// Empty + Error states
// ---------------------------------------------------------------------------

function EmptyTrips({ hasSearch }: { hasSearch: boolean }) {
  return (
    <motion.div
      className="flex flex-col items-center justify-center py-20 text-center space-y-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <Compass size={40} strokeWidth={1} className="text-gray-200" aria-hidden="true" />
      <div className="space-y-1">
        <p className="text-sm font-semibold text-ink">
          {hasSearch ? "No trips match your search." : "No trips yet."}
        </p>
        <p className="text-xs text-muted-slate max-w-xs">
          {hasSearch
            ? "Try a different search term or clear your filters."
            : "Create the first trip and start exploring!"}
        </p>
      </div>
    </motion.div>
  );
}

function ErrorBanner({ onRetry }: { onRetry: () => void }) {
  return (
    <motion.div
      className="flex items-center justify-between gap-4 bg-red-50 border border-red-100 rounded-2xl px-5 py-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      role="alert"
    >
      <p className="text-sm text-red-700">Unable to load trips. Please try again.</p>
      <Button variant="outline" size="sm" icon={RefreshCw} onClick={onRetry}>Retry</Button>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// TripsView
// ---------------------------------------------------------------------------

export default function TripsView() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [tripFilter, setTripFilter] = useState<TripFilter>("all");
  const [createOpen, setCreateOpen] = useState(false);

  // Simple debounce via timeout ref
  const searchTimer = React.useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setSearch(val);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => setDebouncedSearch(val), 400);
  }, []);

  const params = useMemo(() => ({
    ...(debouncedSearch ? { search: debouncedSearch } : {}),
    ...(tripFilter === "personal" ? { personal_only: true } : {}),
    // community filter would need a community_id; here we just use the label
    page_size: 18,
    page: 1,
  }), [debouncedSearch, tripFilter]);

  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<TripSummary>>(
    tripKeys.all(params),
    ([url, p]: [string, Record<string, unknown>]) => swrFetcherWithParams(url, p),
    { revalidateOnFocus: false },
  );

  const trips = data?.items ?? [];

  return (
    <>
      <motion.div
        className="container-main py-8 space-y-6 pb-20"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0, 0, 0.2, 1] }}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl font-bold tracking-tight text-ink">Trips</h1>
            <p className="text-sm text-charcoal">
              Discover and join expeditions from around the world.
            </p>
          </div>
          <Button
            variant="primary"
            size="sm"
            icon={Plus}
            onClick={() => setCreateOpen(true)}
          >
            Create Trip
          </Button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search
            size={15}
            strokeWidth={1.75}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-slate pointer-events-none"
            aria-hidden="true"
          />
          <input
            type="search"
            placeholder="Search trips by title or destination…"
            value={search}
            onChange={handleSearchChange}
            className="w-full pl-9 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm text-ink placeholder:text-muted-slate focus:outline-none focus:bg-white focus:border-ink focus:ring-1 focus:ring-ink transition-all"
            aria-label="Search trips"
          />
        </div>

        {/* Filter chips */}
        <div className="flex items-center gap-2 flex-wrap">
          {(Object.keys(FILTER_LABELS) as TripFilter[]).map((f) => (
            <button
              key={f}
              type="button"
              aria-pressed={tripFilter === f}
              onClick={() => setTripFilter(f)}
              className={[
                "inline-flex items-center px-3 py-1.5 rounded-full border text-xs font-medium",
                "transition-all duration-[var(--duration-responsive)]",
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
                tripFilter === f
                  ? "bg-ink text-white border-ink"
                  : "bg-white text-charcoal border-gray-200 hover:border-gray-300 hover:bg-gray-50",
              ].join(" ")}
            >
              {FILTER_LABELS[f]}
            </button>
          ))}
          {data && (
            <span className="ml-auto text-[10px] font-mono text-muted-slate">
              {data.pagination.totalItems} trip{data.pagination.totalItems !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {/* Grid — all states */}
        <AnimatePresence mode="wait">
          {error ? (
            <ErrorBanner key="error" onRetry={() => mutate(undefined)} />
          ) : isLoading && !data ? (
            <TripCardSkeleton key="skeleton" count={6} />
          ) : trips.length === 0 ? (
            <EmptyTrips key="empty" hasSearch={!!debouncedSearch} />
          ) : (
            <div
              key="trips"
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
            >
              {trips.map((trip, index) => (
                <TripCard
                  key={trip.id}
                  trip={trip}
                  index={index}
                  onClick={() => router.push(`/expeditions/${trip.id}`)}
                />
              ))}
            </div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Create Trip Modal */}
      <CreateTripModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={() => mutate(undefined)}
      />
    </>
  );
}
