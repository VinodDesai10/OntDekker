"use client";

/**
 * OntDekker MyTripsView
 *
 * Shows all trips where the authenticated user is a host or member.
 * Data: GET /api/v1/users/me/trips  (expedition-service, trip-centric surface)
 *
 * Sections:
 *   - Page header + Create Trip button
 *   - Status filter chips (All / Active / Upcoming / Completed)
 *   - 3-column responsive TripCard grid
 *   - Loading / empty / error / success states
 */

import React, { useState, useMemo } from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "motion/react";
import { Backpack, Plus, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";

import TripCard from "@/components/cards/TripCard";
import Button from "@/components/feedback/Button";
import { swrFetcherWithParams, tripKeys } from "@/services/cache";
import TripCardSkeleton from "./TripCardSkeleton";
import CreateTripModal from "./CreateTripModal";

import type { PaginatedResponse } from "@/types";
import type { TripSummary, TripStatus } from "@/types/trip";

// ---------------------------------------------------------------------------
// Filter chips
// ---------------------------------------------------------------------------

type StatusFilter = "all" | "ACTIVE" | "PUBLISHED" | "COMPLETED";

const FILTER_LABELS: Record<StatusFilter, string> = {
  all: "All",
  ACTIVE: "Active",
  PUBLISHED: "Upcoming",
  COMPLETED: "Completed",
};

// ---------------------------------------------------------------------------
// Empty + Error states
// ---------------------------------------------------------------------------

function EmptyTrips({ filter }: { filter: StatusFilter }) {
  const label = filter === "all" ? "trips yet" : `${FILTER_LABELS[filter].toLowerCase()} trips`;
  return (
    <motion.div
      className="flex flex-col items-center justify-center py-20 text-center space-y-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <Backpack size={40} strokeWidth={1} className="text-gray-200" aria-hidden="true" />
      <div className="space-y-1">
        <p className="text-sm font-semibold text-ink">No {label}.</p>
        <p className="text-xs text-muted-slate max-w-xs">
          Join or create a trip to see it here.
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
      <p className="text-sm text-red-700">Unable to load your trips. Please try again.</p>
      <Button variant="outline" size="sm" icon={RefreshCw} onClick={onRetry}>Retry</Button>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// MyTripsView
// ---------------------------------------------------------------------------

export default function MyTripsView() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [createOpen, setCreateOpen] = useState(false);

  const params = useMemo(
    () => ({
      ...(statusFilter !== "all" ? { status: statusFilter } : {}),
      page_size: 18,
    }),
    [statusFilter],
  );

  const { data, isLoading, error, mutate } = useSWR<PaginatedResponse<TripSummary>>(
    tripKeys.mine(params),
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
            <h1 className="text-2xl font-bold tracking-tight text-ink">My Trips</h1>
            <p className="text-sm text-charcoal">
              Your expeditions — active, upcoming, and completed.
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

        {/* Status filter chips */}
        <div className="flex items-center gap-2 flex-wrap">
          {(Object.keys(FILTER_LABELS) as StatusFilter[]).map((filter) => (
            <button
              key={filter}
              type="button"
              aria-pressed={statusFilter === filter}
              onClick={() => setStatusFilter(filter)}
              className={[
                "inline-flex items-center px-3 py-1.5 rounded-full border text-xs font-medium",
                "transition-all duration-[var(--duration-responsive)]",
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
                statusFilter === filter
                  ? "bg-ink text-white border-ink"
                  : "bg-white text-charcoal border-gray-200 hover:border-gray-300 hover:bg-gray-50",
              ].join(" ")}
            >
              {FILTER_LABELS[filter]}
            </button>
          ))}
          {data && (
            <span className="ml-auto text-[10px] font-mono text-muted-slate">
              {data.pagination.totalItems} trip{data.pagination.totalItems !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {/* Trip grid — all states */}
        <AnimatePresence mode="wait">
          {error ? (
            <ErrorBanner key="error" onRetry={() => mutate()} />
          ) : isLoading && !data ? (
            <TripCardSkeleton key="skeleton" count={6} />
          ) : trips.length === 0 ? (
            <EmptyTrips key="empty" filter={statusFilter} />
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

      <CreateTripModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={() => mutate()}
      />
    </>
  );
}
