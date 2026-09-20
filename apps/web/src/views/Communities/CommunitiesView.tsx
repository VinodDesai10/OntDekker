"use client";

/**
 * OntDekker CommunitiesView
 *
 * Community discovery directory. Entry from Sidebar "Communities" item.
 *
 * Features:
 *   - Search communities (debounced, sent as backend `search` query param)
 *   - Filter chips: Public / Private
 *   - Community cards (name, description, member count, visibility badge)
 *   - "Create Community" button navigates to /communities/create
 *   - Loading skeleton, empty state, and error state
 *
 * Data layer:
 *   useSWR([communityKeys.list(params)], swrFetcherWithParams)
 *   → CommunitiesPage  { communities: CommunitySummary[], total, ... }
 */

import React, { useState, useEffect, useMemo, useRef } from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "motion/react";
import { Globe, Lock, Plus, Users, RefreshCw } from "lucide-react";

import CommunityCard from "@/components/cards/CommunityCard";
import Search from "@/components/navigation/Search";
import Button from "@/components/feedback/Button";
import { swrFetcherWithParams, communityKeys } from "@/services/cache";
import { useRouter } from "next/navigation";
import CommunityCardSkeleton from "./CommunityCardSkeleton";
import type { CommunitySummary, CommunityVisibility } from "@/types";
import type { CommunitiesPage } from "@/services/communityApi";

// ---------------------------------------------------------------------------
// Filter Chip
// ---------------------------------------------------------------------------

function FilterChip({
  label,
  icon: Icon,
  active,
  onToggle,
}: {
  label: string;
  icon: React.ComponentType<{
    size?: number | string;
    strokeWidth?: number | string;
    className?: string;
  }>;
  active: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onToggle}
      className={[
        "inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full border text-xs font-medium",
        "transition-all duration-150",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#111111]",
        active
          ? "bg-[#111111] text-white border-[#111111]"
          : "bg-white text-gray-700 border-[#EAE7DF] hover:border-gray-300 hover:bg-gray-50",
      ].join(" ")}
    >
      <Icon size={12} strokeWidth={2} aria-hidden="true" />
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyCommunities({ hasFilters }: { hasFilters: boolean }) {
  return (
    <motion.div
      className="flex flex-col items-center justify-center py-20 text-center space-y-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <Users size={40} strokeWidth={1} className="text-gray-200" aria-hidden="true" />
      <div className="space-y-1">
        <p className="text-sm font-semibold text-[#111111]">
          {hasFilters ? "No communities match your search." : "No communities yet."}
        </p>
        <p className="text-xs text-gray-500 max-w-xs">
          {hasFilters
            ? "Try clearing your filters or using a different search term."
            : "Be the first to create a travel community on OntDekker."}
        </p>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Error banner
// ---------------------------------------------------------------------------

function ErrorBanner({ onRetry }: { onRetry: () => void }) {
  return (
    <motion.div
      className="flex items-center justify-between gap-4 bg-red-50 border border-red-100 rounded-2xl px-5 py-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      role="alert"
    >
      <p className="text-sm text-red-700">
        Unable to load communities. Check your connection and try again.
      </p>
      <Button variant="outline" size="sm" icon={RefreshCw} onClick={onRetry}>
        Retry
      </Button>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// CommunitiesView
// ---------------------------------------------------------------------------

export default function CommunitiesView() {
  const router = useRouter();

  // Search input state (shows immediately in the input)
  const [searchInput, setSearchInput] = useState("");
  // Debounced search sent to the backend (delayed 400ms)
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
    }, 400);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchInput]);

  // Visibility filter state
  const [visibilityFilter, setVisibilityFilter] = useState<
    CommunityVisibility | null
  >(null);

  const filters = useMemo(() => {
    const params: Record<string, unknown> = { limit: 48 };
    if (debouncedSearch) params.search = debouncedSearch;
    if (visibilityFilter) params.visibility = visibilityFilter;
    return params;
  }, [debouncedSearch, visibilityFilter]);

  const hasActiveFilters = !!debouncedSearch || !!visibilityFilter;

  // SWR fetch
  const swrKey = communityKeys.list(filters);
  const { data, isLoading, error, mutate } = useSWR<CommunitiesPage>(
    swrKey,
    ([url, params]: [string, Record<string, unknown>]) =>
      swrFetcherWithParams(url, params),
    { revalidateOnFocus: false },
  );

  // The backend returns { communities: [...] } (camelCase after transform)
  const communities: CommunitySummary[] = data?.communities ?? [];

  // Visibility chip handlers
  function handlePublicToggle() {
    setVisibilityFilter((v) => (v === "PUBLIC" ? null : "PUBLIC"));
  }

  function handlePrivateToggle() {
    setVisibilityFilter((v) => (v === "PRIVATE" ? null : "PRIVATE"));
  }

  return (
    <div className="space-y-6">
      {/* Page header + Create button */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-[#111111]">
            Communities
          </h1>
          <p className="text-sm text-gray-500">
            Discover and join niche travel communities on OntDekker.
          </p>
        </div>

        <Button
          variant="primary"
          size="sm"
          icon={Plus}
          onClick={() => router.push("/communities/create")}
          className="flex-shrink-0"
        >
          Create Community
        </Button>
      </div>

      {/* Search + filters */}
      <div className="space-y-3">
        <Search
          placeholder="Search by name or location…"
          value={searchInput}
          onChange={setSearchInput}
          className="max-w-md"
          ariaLabel="Search communities"
        />

        <div className="flex items-center gap-2 flex-wrap">
          <FilterChip
            label="Public"
            icon={Globe}
            active={visibilityFilter === "PUBLIC"}
            onToggle={handlePublicToggle}
          />
          <FilterChip
            label="Private"
            icon={Lock}
            active={visibilityFilter === "PRIVATE"}
            onToggle={handlePrivateToggle}
          />
          {hasActiveFilters && (
            <button
              type="button"
              onClick={() => {
                setSearchInput("");
                setDebouncedSearch("");
                setVisibilityFilter(null);
              }}
              className="text-xs text-gray-500 hover:text-[#111111] underline transition-colors"
            >
              Clear all
            </button>
          )}
          {!isLoading && data && (
            <span className="ml-auto text-xs text-gray-400 font-medium">
              {communities.length}
              {data.total > communities.length ? ` of ${data.total}` : ""}{" "}
              {communities.length === 1 ? "community" : "communities"}
            </span>
          )}
        </div>
      </div>

      {/* Community grid — all states */}
      <AnimatePresence mode="wait">
        {isLoading && !data ? (
          <CommunityCardSkeleton key="skeleton" count={6} />
        ) : error ? (
          <ErrorBanner key="error" onRetry={() => mutate()} />
        ) : communities.length === 0 ? (
          <EmptyCommunities key="empty" hasFilters={hasActiveFilters} />
        ) : (
          <div
            key="communities"
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
          >
            {communities.map((community, index) => (
              <CommunityCard
                key={community.id}
                community={community}
                index={index}
                onClick={() => router.push(`/communities/${community.id}`)}
              />
            ))}
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
