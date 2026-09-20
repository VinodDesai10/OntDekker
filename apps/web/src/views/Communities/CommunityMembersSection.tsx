"use client";

/**
 * OntDekker — CommunityMembersSection
 *
 * Displays the list of active community members with real profile data
 * (display name, username, avatar) fetched via the batch-profiles endpoint.
 *
 * Features:
 *   - Batch profile resolution — single POST /users/batch-profiles call
 *   - Client-side search by display name / username
 *   - OWNER / MOD manage button
 */

import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { Users, RefreshCw, ShieldCheck, Crown, User, Search, X } from "lucide-react";
import { motion } from "motion/react";

import Button from "@/components/feedback/Button";
import Badge from "@/components/feedback/Badge";
import { swrFetcherWithParams, communityKeys } from "@/services/cache";
import { batchProfiles, type ProfileMap } from "@/services/users";
import type { CommunityMember, MemberListResponse, MemberRole } from "@/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function RoleBadge({ role }: { role: MemberRole }) {
  if (role === "OWNER") {
    return (
      <Badge variant="warning" size="sm" className="gap-1">
        <Crown size={9} strokeWidth={2.5} aria-hidden="true" />
        Head
      </Badge>
    );
  }
  if (role === "MODERATOR") {
    return (
      <Badge variant="info" size="sm" className="gap-1">
        <ShieldCheck size={9} strokeWidth={2.5} aria-hidden="true" />
        Co-Head
      </Badge>
    );
  }
  return (
    <Badge variant="default" size="sm" className="gap-1">
      <User size={9} strokeWidth={2} aria-hidden="true" />
      Member
    </Badge>
  );
}

function shortId(userId: string): string {
  if (userId.length <= 12) return userId;
  return `${userId.slice(0, 6)}…${userId.slice(-4)}`;
}

// ---------------------------------------------------------------------------
// MemberRow
// ---------------------------------------------------------------------------

interface MemberRowProps {
  member: CommunityMember;
  profile: ProfileMap[string] | undefined;
  currentUserId: string | undefined;
  currentUserRole: MemberRole | null;
  onManage: (member: CommunityMember) => void;
}

function MemberRow({
  member,
  profile,
  currentUserId,
  currentUserRole,
  onManage,
}: MemberRowProps) {
  const isCurrentUser = member.userId === currentUserId;
  const isOwner = member.role === "OWNER";

  const canManage =
    !isCurrentUser &&
    !isOwner &&
    (currentUserRole === "OWNER" ||
      (currentUserRole === "MODERATOR" && member.role === "MEMBER"));

  const displayName = profile?.displayName ?? shortId(member.userId);
  const username = profile?.username ? `@${profile.username}` : null;
  const avatarSrc = profile?.avatarUrl ?? null;
  const initials = (profile?.displayName ?? member.userId)
    .slice(0, 2)
    .toUpperCase();

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.2 }}
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
            className="w-9 h-9 rounded-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center text-gray-600 text-xs font-semibold"
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
          {isCurrentUser && (
            <span className="ml-1.5 text-[10px] text-gray-400">(you)</span>
          )}
        </p>
        <div className="flex items-center gap-1.5 flex-wrap">
          {username && (
            <span className="text-[11px] text-gray-500 font-mono">{username}</span>
          )}
          <RoleBadge role={member.role} />
        </div>
      </div>

      {/* Action */}
      {canManage && (
        <Button
          variant="outline"
          size="xs"
          onClick={() => onManage(member)}
          aria-label={`Manage ${displayName}`}
        >
          Manage
        </Button>
      )}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// CommunityMembersSection
// ---------------------------------------------------------------------------

interface CommunityMembersSectionProps {
  communityId: string;
  currentUserId: string | undefined;
  currentUserRole: MemberRole | null;
  onManage: (member: CommunityMember) => void;
  /** Called whenever new profiles are resolved so parent can use them */
  onProfilesResolved?: (profiles: ProfileMap) => void;
}

export default function CommunityMembersSection({
  communityId,
  currentUserId,
  currentUserRole,
  onManage,
  onProfilesResolved,
}: CommunityMembersSectionProps) {
  const [showAll, setShowAll] = useState(false);
  const [search, setSearch] = useState("");
  const [profiles, setProfiles] = useState<ProfileMap>({});
  const INITIAL_LIMIT = 10;

  const params = showAll ? { limit: 200 } : { limit: INITIAL_LIMIT };
  const swrKey = communityKeys.members(communityId, params);

  const { data, isLoading, error, mutate } = useSWR<MemberListResponse>(
    swrKey,
    ([url, p]: [string, Record<string, unknown>]) =>
      swrFetcherWithParams(url, p),
    { revalidateOnFocus: false },
  );

  const members = data?.members ?? [];
  const total = data?.total ?? 0;

  // Batch-fetch profiles whenever the member list changes
  useEffect(() => {
    if (members.length === 0) return;
    const ids = members.map((m) => m.userId);
    batchProfiles(ids).then((map) => {
      setProfiles((prev) => ({ ...prev, ...map }));
      onProfilesResolved?.(map);
    });
  }, [members]);

  // Client-side search filter
  const filteredMembers = useMemo(() => {
    if (!search.trim()) return members;
    const q = search.toLowerCase().trim();
    return members.filter((m) => {
      const p = profiles[m.userId];
      if (!p) return shortId(m.userId).toLowerCase().includes(q);
      return (
        p.displayName.toLowerCase().includes(q) ||
        p.username.toLowerCase().includes(q)
      );
    });
  }, [members, profiles, search]);

  // Loading skeleton
  if (isLoading) {
    return (
      <section aria-label="Community members" className="space-y-3">
        <h2 className="text-sm font-semibold text-[#111111]">Members</h2>
        <div className="bg-white border border-gray-100 rounded-3xl px-5 divide-y divide-gray-100 shadow-sm animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="py-3 flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-gray-200 flex-shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 w-28 bg-gray-200 rounded" />
                <div className="h-2.5 w-16 bg-gray-200 rounded" />
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  // Error state
  if (error) {
    return (
      <section aria-label="Community members" className="space-y-3">
        <h2 className="text-sm font-semibold text-[#111111]">Members</h2>
        <div className="flex items-center justify-between gap-4 bg-red-50 border border-red-100 rounded-2xl px-5 py-4">
          <p className="text-sm text-red-700">Unable to load members.</p>
          <Button variant="outline" size="sm" icon={RefreshCw} onClick={() => mutate()}>
            Retry
          </Button>
        </div>
      </section>
    );
  }

  // Empty state
  if (members.length === 0) {
    return (
      <section aria-label="Community members" className="space-y-3">
        <h2 className="text-sm font-semibold text-[#111111]">Members</h2>
        <div className="flex flex-col items-center justify-center py-10 text-center space-y-2">
          <Users size={32} strokeWidth={1} className="text-gray-200" aria-hidden="true" />
          <p className="text-xs text-gray-500">No members yet.</p>
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Community members" className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-[#111111]">
          Members
          {total > 0 && (
            <span className="ml-1.5 text-xs text-gray-400 font-normal">
              ({total.toLocaleString()})
            </span>
          )}
        </h2>
      </div>

      {/* Search */}
      {total >= 5 && (
        <div className="relative">
          <Search
            size={13}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
            aria-hidden="true"
          />
          <input
            type="search"
            placeholder="Search members…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="
              w-full pl-8 pr-8 py-2 text-xs rounded-2xl
              border border-gray-200 bg-white
              focus:outline-none focus:ring-2 focus:ring-[#111111]/10 focus:border-[#111111]
              placeholder:text-gray-400
            "
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch("")}
              aria-label="Clear search"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X size={12} aria-hidden="true" />
            </button>
          )}
        </div>
      )}

      {/* List */}
      <div className="bg-white border border-gray-100 rounded-3xl px-5 divide-y divide-gray-100 shadow-sm">
        {filteredMembers.length === 0 ? (
          <div className="py-8 text-center text-xs text-gray-500">
            No members match &ldquo;{search}&rdquo;
          </div>
        ) : (
          filteredMembers.map((member) => (
            <MemberRow
              key={member.id}
              member={member}
              profile={profiles[member.userId]}
              currentUserId={currentUserId}
              currentUserRole={currentUserRole}
              onManage={onManage}
            />
          ))
        )}
      </div>

      {/* Show more / less */}
      {total > INITIAL_LIMIT && !search && (
        <button
          type="button"
          onClick={() => setShowAll((v) => !v)}
          className="w-full text-center text-xs text-gray-500 hover:text-[#111111] py-1 transition-colors"
        >
          {showAll ? "Show less" : `Show all ${total.toLocaleString()} members`}
        </button>
      )}
    </section>
  );
}
