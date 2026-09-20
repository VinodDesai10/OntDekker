"use client";

/**
 * OntDekker — JoinRequestsSection
 *
 * Displays pending join requests for a community.
 * Visible only to OWNER (Head) and MODERATOR (Co-Head).
 *
 * CP-2.5: Enriched with real profile data via POST /users/batch-profiles.
 * Displays: avatar, display name, username — with UUID fallback.
 */

import { useEffect, useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import {
  ClipboardList,
  RefreshCw,
  Check,
  X,
  Loader2,
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

import Button from "@/components/feedback/Button";
import { swrFetcherWithParams, communityKeys } from "@/services/cache";
import { actionJoinRequest } from "@/services/communityApi";
import { batchProfiles, type ProfileMap } from "@/services/users";
import type { CommunityJoinRequest, JoinRequestListResponse } from "@/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function shortId(id: string): string {
  if (id.length <= 12) return id;
  return `${id.slice(0, 6)}…${id.slice(-4)}`;
}

// ---------------------------------------------------------------------------
// JoinRequestRow
// ---------------------------------------------------------------------------

interface JoinRequestRowProps {
  request: CommunityJoinRequest;
  profile: ProfileMap[string] | undefined;
  onAction: (requestId: string, action: "approve" | "reject") => Promise<void>;
}

function JoinRequestRow({
  request,
  profile,
  onAction,
}: JoinRequestRowProps) {
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);

  const isBusy = approving || rejecting;

  const displayName = profile?.displayName ?? shortId(request.requesterId);
  const username = profile?.username ? `@${profile.username}` : null;
  const avatarSrc = profile?.avatarUrl ?? null;
  const initials = (profile?.displayName ?? request.requesterId)
    .slice(0, 2)
    .toUpperCase();

  async function handleApprove() {
    setApproving(true);
    try {
      await onAction(request.id, "approve");
    } finally {
      setApproving(false);
    }
  }

  async function handleReject() {
    setRejecting(true);
    try {
      await onAction(request.id, "reject");
    } finally {
      setRejecting(false);
    }
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -8, transition: { duration: 0.15 } }}
      className="flex items-center gap-3 py-3"
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        {avatarSrc ? (
          <img
            src={avatarSrc}
            alt={displayName}
            className="w-9 h-9 rounded-full object-cover"
          />
        ) : (
          <div
            className="
              w-9 h-9 rounded-full flex-shrink-0
              bg-gradient-to-br from-amber-100 to-orange-100
              flex items-center justify-center
              text-amber-700 text-xs font-semibold font-mono
            "
            aria-hidden="true"
          >
            {initials}
          </div>
        )}
      </div>

      {/* Identity */}
      <div className="flex-1 min-w-0 space-y-0.5">
        <p className="text-sm font-medium text-[#111111] truncate">
          {displayName}
        </p>
        {username && (
          <p className="text-[11px] text-gray-500 font-mono">{username}</p>
        )}
        {request.message && (
          <p className="text-xs text-gray-400 truncate italic">
            &ldquo;{request.message}&rdquo;
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          type="button"
          onClick={handleApprove}
          disabled={isBusy}
          aria-label={`Approve request from ${displayName}`}
          className="
            inline-flex items-center justify-center
            w-7 h-7 rounded-full
            bg-green-50 text-green-700
            hover:bg-green-100 disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors
          "
        >
          {approving ? (
            <Loader2 size={13} className="animate-spin" aria-hidden="true" />
          ) : (
            <Check size={13} strokeWidth={2.5} aria-hidden="true" />
          )}
        </button>

        <button
          type="button"
          onClick={handleReject}
          disabled={isBusy}
          aria-label={`Reject request from ${displayName}`}
          className="
            inline-flex items-center justify-center
            w-7 h-7 rounded-full
            bg-red-50 text-red-600
            hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors
          "
        >
          {rejecting ? (
            <Loader2 size={13} className="animate-spin" aria-hidden="true" />
          ) : (
            <X size={13} strokeWidth={2.5} aria-hidden="true" />
          )}
        </button>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// JoinRequestsSection
// ---------------------------------------------------------------------------

interface JoinRequestsSectionProps {
  communityId: string;
}

export default function JoinRequestsSection({
  communityId,
}: JoinRequestsSectionProps) {
  const { mutate } = useSWRConfig();
  const params = { limit: 50 };
  const swrKey = communityKeys.joinRequests(communityId, params);

  const {
    data,
    isLoading,
    error,
    mutate: mutateRequests,
  } = useSWR<JoinRequestListResponse>(
    swrKey,
    ([url, p]: [string, Record<string, unknown>]) =>
      swrFetcherWithParams(url, p),
    { revalidateOnFocus: true },
  );

  const requests = data?.requests ?? [];
  const total = data?.total ?? 0;

  // Batch-resolve profiles for all requester IDs
  const [profiles, setProfiles] = useState<ProfileMap>({});
  useEffect(() => {
    if (requests.length === 0) return;
    const ids = requests.map((r) => r.requesterId);
    batchProfiles(ids).then((map) =>
      setProfiles((prev) => ({ ...prev, ...map })),
    );
  }, [requests]);

  // -------------------------------------------------------------------------
  // Action handler — optimistic remove + revalidate
  // -------------------------------------------------------------------------
  async function handleAction(
    requestId: string,
    action: "approve" | "reject",
  ) {
    await actionJoinRequest(requestId, { action });

    // Optimistically remove from list, then revalidate
    await mutateRequests(
      (prev) =>
        prev
          ? {
              ...prev,
              requests: prev.requests.filter((r) => r.id !== requestId),
              total: Math.max(0, prev.total - 1),
            }
          : prev,
      { revalidate: true },
    );

    // Also revalidate the community detail to update member_count and membershipStatus
    mutate(
      (key: unknown) =>
        typeof key === "string" &&
        key.includes(`/communities/${communityId}`),
    );
  }

  // -------------------------------------------------------------------------
  // Loading skeleton
  // -------------------------------------------------------------------------
  if (isLoading) {
    return (
      <section aria-label="Join requests" className="space-y-3">
        <h2 className="text-sm font-semibold text-[#111111]">Join Requests</h2>
        <div className="bg-white border border-gray-100 rounded-3xl px-5 divide-y divide-gray-100 shadow-sm animate-pulse">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="py-3 flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-gray-200 flex-shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 w-28 bg-gray-200 rounded" />
                <div className="h-2.5 w-16 bg-gray-200 rounded" />
              </div>
              <div className="flex gap-1.5">
                <div className="w-7 h-7 rounded-full bg-gray-200" />
                <div className="w-7 h-7 rounded-full bg-gray-200" />
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  // -------------------------------------------------------------------------
  // Error
  // -------------------------------------------------------------------------
  if (error) {
    return (
      <section aria-label="Join requests" className="space-y-3">
        <h2 className="text-sm font-semibold text-[#111111]">Join Requests</h2>
        <div className="flex items-center justify-between gap-4 bg-red-50 border border-red-100 rounded-2xl px-5 py-4">
          <p className="text-sm text-red-700">Unable to load join requests.</p>
          <Button
            variant="outline"
            size="sm"
            icon={RefreshCw}
            onClick={() => mutateRequests()}
          >
            Retry
          </Button>
        </div>
      </section>
    );
  }

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------
  if (requests.length === 0) {
    return (
      <section aria-label="Join requests" className="space-y-3">
        <h2 className="text-sm font-semibold text-[#111111]">Join Requests</h2>
        <div className="flex flex-col items-center justify-center py-10 text-center space-y-2">
          <ClipboardList
            size={32}
            strokeWidth={1}
            className="text-gray-200"
            aria-hidden="true"
          />
          <p className="text-xs text-gray-500">No pending join requests.</p>
        </div>
      </section>
    );
  }

  // -------------------------------------------------------------------------
  // Requests list
  // -------------------------------------------------------------------------
  return (
    <section aria-label="Join requests" className="space-y-3">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold text-[#111111]">Join Requests</h2>
        {total > 0 && (
          <span
            className="
              inline-flex items-center justify-center
              min-w-[18px] h-[18px] px-1 rounded-full
              bg-amber-100 text-amber-800
              text-[10px] font-semibold
            "
          >
            {total}
          </span>
        )}
      </div>

      <div className="bg-white border border-gray-100 rounded-3xl px-5 divide-y divide-gray-100 shadow-sm">
        <AnimatePresence initial={false} mode="popLayout">
          {requests.map((request) => (
            <JoinRequestRow
              key={request.id}
              request={request}
              profile={profiles[request.requesterId]}
              onAction={handleAction}
            />
          ))}
        </AnimatePresence>
      </div>
    </section>
  );
}
