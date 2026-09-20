"use client";

/**
 * OntDekker MyGuidesView
 *
 * Displays guides the user has bookmarked / connected with.
 *
 * Data flow:
 *   1. On mount: GET /guides/api/v1/guides/my-connections?bookmarked_only=true
 *      → returns TravelConnectionListResponse { connections: [{ guide_id, ... }] }
 *   2. For each connection, GET /guides/api/v1/guides/{guide_id}
 *      → hydrates full GuideProfileSummary for each guide
 *   3. Dispatch SAVED_GUIDES_LOADED to populate AppState
 *   4. Render guide cards from AppState.savedGuides
 *
 * States: loading / error / empty / success
 *
 * Do NOT use mock guides.
 */

import React, { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Compass, RefreshCw } from "lucide-react";
import GuideCard from "@/components/cards/GuideCard";
import Button from "@/components/feedback/Button";
import GuideCardSkeleton from "@/views/Guides/GuideCardSkeleton";
import { useAppState } from "@/contexts/AppStateProvider";
import { useRouter } from "next/navigation";
import { getMyConnections, getGuideById, unbookmarkGuide } from "@/services/guideApi";
import { useSWRConfig } from "swr";
import { guideKeys } from "@/services/cache";
import { useToast } from "@/hooks/useToast";
import type { GuideProfileSummary } from "@/types";

// ---------------------------------------------------------------------------
// Error state
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
        Unable to load your saved guides. Please try again.
      </p>
      <Button variant="outline" size="sm" icon={RefreshCw} onClick={onRetry}>
        Retry
      </Button>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyState({ onDiscover }: { onDiscover: () => void }) {
  return (
    <div className="flex flex-col items-center py-20 gap-4 text-center">
      <Compass
        size={40}
        strokeWidth={1}
        className="text-gray-200"
        aria-hidden="true"
      />
      <div className="space-y-1">
        <p className="text-sm font-semibold text-ink">No saved guides yet.</p>
        <p className="text-xs text-muted-slate max-w-xs">
          Bookmark guides from the directory to keep them here for easy access.
        </p>
      </div>
      <Button variant="primary" size="md" onClick={onDiscover}>
        Discover guides
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// MyGuidesView
// ---------------------------------------------------------------------------

type LoadState = "loading" | "error" | "ready";

export default function MyGuidesView() {
  const { state, dispatch } = useAppState();
  const router = useRouter();
  const { mutate } = useSWRConfig();
  const { showToast } = useToast();

  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());

  // ── Fetch guides from backend ─────────────────────────────────────────────

  const fetchSavedGuides = useCallback(async () => {
    setLoadState("loading");
    try {
      // Step 1: get bookmarked connections
      const connectionsResponse = await getMyConnections({ bookmarked_only: true, page_size: 100 });
      const connections = connectionsResponse.connections ?? [];

      // Track which guide IDs are bookmarked
      const ids = new Set(connections.map((c) => c.guideId));
      setBookmarkedIds(ids);

      if (connections.length === 0) {
        dispatch({ type: "SAVED_GUIDES_LOADED", guides: [] });
        setLoadState("ready");
        return;
      }

      // Step 2: fetch full guide profiles for each connection
      const guideResults = await Promise.allSettled(
        connections.map((c) => getGuideById(c.guideId)),
      );

      const guides: GuideProfileSummary[] = [];
      for (const result of guideResults) {
        if (result.status === "fulfilled") {
          const apiResponse = result.value;
          // getGuideById returns ApiResponse<GuideProfile>; extract .data
          const profile = (apiResponse as { data?: GuideProfileSummary }).data ?? (apiResponse as unknown as GuideProfileSummary);
          if (profile && (profile as GuideProfileSummary).id) {
            guides.push(profile as GuideProfileSummary);
          }
        }
        // Silently skip failed individual guide fetches
      }

      // Step 3: hydrate AppState
      dispatch({ type: "SAVED_GUIDES_LOADED", guides });
      setLoadState("ready");
    } catch {
      setLoadState("error");
    }
  }, [dispatch]);

  useEffect(() => {
    fetchSavedGuides();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Unbookmark handler ────────────────────────────────────────────────────

  const handleUnbookmark = useCallback(
    async (e: React.MouseEvent, guide: GuideProfileSummary) => {
      e.stopPropagation();
      try {
        await unbookmarkGuide(guide.id);
        dispatch({ type: "GUIDE_BOOKMARK_TOGGLED", guideId: guide.id, bookmarked: false });
        setBookmarkedIds((prev) => {
          const next = new Set(prev);
          next.delete(guide.id);
          return next;
        });
        // Invalidate connections cache so directory reflects updated state
        await mutate(guideKeys.myConnections());
        showToast("Bookmark removed.", "info");
      } catch {
        showToast("Could not remove bookmark. Please try again.", "error");
      }
    },
    [dispatch, mutate, showToast],
  );

  // ── Render ─────────────────────────────────────────────────────────────────

  const { savedGuides } = state;

  return (
    <motion.div
      className="pb-20"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0, 0, 0.2, 1] }}
    >
      <div className="container-main pt-6 space-y-6">
        {/* Page header */}
        <div>
          <p className="text-xs font-mono uppercase tracking-widest text-muted-slate">
            Guides
          </p>
          <h1 className="text-2xl font-bold tracking-tight text-ink mt-1">
            My Guides
          </h1>
          <p className="text-sm text-muted-slate mt-1">
            Guides you&apos;ve saved or connected with.
          </p>
        </div>

        {/* Content states */}
        <AnimatePresence mode="wait">
          {loadState === "loading" ? (
            <GuideCardSkeleton key="skeleton" count={3} />
          ) : loadState === "error" ? (
            <ErrorBanner key="error" onRetry={fetchSavedGuides} />
          ) : savedGuides.length === 0 ? (
            <EmptyState
              key="empty"
              onDiscover={() => router.push("/guides")}
            />
          ) : (
            <div
              key="guides"
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
              role="list"
              aria-label="Saved guides"
            >
              {savedGuides.map((guide, i) => (
                <motion.div
                  key={guide.id}
                  role="listitem"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05, duration: 0.25 }}
                >
                  <GuideCard
                    guide={guide}
                    isBookmarked={bookmarkedIds.has(guide.id)}
                    onBookmarkToggle={(e) => handleUnbookmark(e, guide)}
                    onClick={() => router.push(`/guides/${guide.id}`)}
                    index={i}
                  />
                </motion.div>
              ))}
            </div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
