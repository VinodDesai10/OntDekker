"use client";

/**
 * OntDekker CommunityDetailView — CP-2.5
 *
 * Changes from CP-2:
 *   - Membership state driven entirely by backend membershipStatus field
 *     (NOT_MEMBER | PENDING | MEMBER | CO_HEAD | HEAD). No local pendingRequest flag.
 *   - Optimistic updates for: Join, Leave, Promote, Demote, Remove
 *   - Confirmation Dialog for: Leave Community, Delete Community
 *   - ManageMemberModal passes profile map from CommunityMembersSection
 *   - Batch profiles fetched at this level and passed down to ManageMemberModal
 */

import { useMemo, useState, useCallback } from "react";
import useSWR, { useSWRConfig } from "swr";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Users,
  MapPin,
  Globe,
  Lock,
  RefreshCw,
  LogIn,
  LogOut,
  Clock,
  Trash2,
  ClipboardList,
  Pencil,
} from "lucide-react";

import Badge from "@/components/feedback/Badge";
import Button from "@/components/feedback/Button";
import Dialog from "@/components/overlays/Dialog";
import { swrFetcher, communityKeys } from "@/services/cache";
import { useRouter, useParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

import {
  joinCommunity,
  leaveCommunity,
  archiveCommunity,
  removeMember,
  updateMemberRole,
} from "@/services/communityApi";
import type { ProfileMap } from "@/services/users";

import CommunityDetailSkeleton from "./CommunityDetailSkeleton";
import CommunityMembersSection from "./CommunityMembersSection";
import JoinRequestsSection from "./JoinRequestsSection";
import ManageMemberModal from "./ManageMemberModal";

import type {
  Community,
  CommunityRule,
  CommunityMember,
  MemberRole,
  MembershipViewStatus,
} from "@/types";

// ---------------------------------------------------------------------------
// Image URL helper
//
// The backend stores MinIO URLs with the internal Docker hostname "minio"
// (e.g. http://minio:9000/communities/…). That hostname is only resolvable
// inside the Docker network — the browser cannot reach it, causing broken
// images. We rewrite the host to "localhost:9000" so the browser hits the
// port-mapped MinIO instance directly.
//
// Safe to call with null / already-correct URLs.
// ---------------------------------------------------------------------------

function resolveMediaUrl(url: string | null): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.hostname === "minio") {
      parsed.hostname = "localhost";
      parsed.port = "9000";
      return parsed.toString();
    }
    return url;
  } catch {
    // Not a valid URL — return as-is so the caller can decide
    return url;
  }
}

// ---------------------------------------------------------------------------
// Hero — banner only (avatar is rendered in the content area so it can
// overlap correctly without a second container-main wrapper)
// ---------------------------------------------------------------------------

function CommunityHero({
  bannerUrl,
  onBack,
}: {
  bannerUrl: string | null;
  onBack: () => void;
}) {
  const resolvedBanner = resolveMediaUrl(bannerUrl);

  return (
    /* Banner — 320 px tall, rounded bottom corners */
    <div className="relative h-80 w-full overflow-hidden rounded-b-3xl bg-gray-100">
      {resolvedBanner ? (
        <img
          src={resolvedBanner}
          alt=""
          aria-hidden="true"
          className="w-full h-full object-cover"
          loading="lazy"
        />
      ) : (
        <div className="w-full h-full bg-gradient-to-br from-gray-100 to-gray-200" />
      )}
      {/* Back button */}
      <button
        type="button"
        aria-label="Go back"
        onClick={onBack}
        className="
          absolute top-4 left-4 flex items-center justify-center
          w-9 h-9 rounded-xl bg-white/80 backdrop-blur-sm text-[#111111]
          hover:bg-white shadow-sm transition-all duration-150
          focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2
          focus-visible:outline-[#111111]
        "
      >
        <ArrowLeft size={16} strokeWidth={2} aria-hidden="true" />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

function CommunityMeta({
  visibility,
  location,
  memberCount,
}: {
  visibility: Community["visibility"];
  location: string | null;
  memberCount: number;
}) {
  const isPrivate = visibility === "PRIVATE";
  return (
    <div className="flex items-center gap-3 flex-wrap text-[10px] font-mono uppercase tracking-wider text-gray-500">
      <Badge variant={isPrivate ? "warning" : "success"} size="sm">
        {isPrivate ? (
          <Lock size={9} strokeWidth={2.5} aria-hidden="true" />
        ) : (
          <Globe size={9} strokeWidth={2.5} aria-hidden="true" />
        )}
        {isPrivate ? "Private" : "Public"}
      </Badge>
      <span className="flex items-center gap-1">
        <Users size={10} strokeWidth={2} aria-hidden="true" />
        {memberCount.toLocaleString()}{" "}
        {memberCount === 1 ? "member" : "members"}
      </span>
      {location && (
        <span className="flex items-center gap-1">
          <MapPin size={10} strokeWidth={2} aria-hidden="true" />
          {location}
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Rules
// ---------------------------------------------------------------------------

function CommunityRulesSection({ rules }: { rules: CommunityRule[] }) {
  if (rules.length === 0) return null;
  const sorted = [...rules].sort((a, b) => a.orderIndex - b.orderIndex);
  return (
    <section aria-label="Community rules" className="space-y-3">
      <h2 className="text-sm font-semibold text-[#111111]">Community Rules</h2>
      <div className="bg-white border border-gray-100 rounded-3xl px-5 divide-y divide-gray-100 shadow-sm">
        {sorted.map((rule, index) => (
          <div key={rule.id} className="py-4">
            <div className="flex items-start gap-3">
              <span
                className="flex-shrink-0 w-5 h-5 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center text-[10px] font-mono font-bold"
                aria-hidden="true"
              >
                {index + 1}
              </span>
              <div className="space-y-1 min-w-0">
                <p className="text-sm font-semibold text-[#111111]">
                  {rule.title}
                </p>
                {rule.description && (
                  <p className="text-xs text-gray-600 leading-relaxed">
                    {rule.description}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

function CommunityDetailError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
      <p className="text-sm font-semibold text-[#111111]">
        Unable to load this community.
      </p>
      <p className="text-xs text-gray-500">
        The community may not exist, or there was a connection problem.
      </p>
      <Button variant="outline" size="sm" icon={RefreshCw} onClick={onRetry}>
        Retry
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Action Bar — driven entirely by membershipStatus from backend
// ---------------------------------------------------------------------------

interface ActionBarProps {
  membershipStatus: MembershipViewStatus;
  isAuthenticated: boolean;
  joinLoading: boolean;
  leaveLoading: boolean;
  deleteLoading: boolean;
  onJoin: () => void;
  onLeave: () => void;
  onDelete: () => void;
  onEdit: () => void;
  onViewRequests: () => void;
}

function ActionBar({
  membershipStatus,
  isAuthenticated,
  joinLoading,
  leaveLoading,
  deleteLoading,
  onJoin,
  onLeave,
  onDelete,
  onEdit,
  onViewRequests,
}: ActionBarProps) {
  const isHead = membershipStatus === "HEAD";
  const isCoHead = membershipStatus === "CO_HEAD";
  const isMember = membershipStatus === "MEMBER";
  const isNotMember = membershipStatus === "NOT_MEMBER";

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {/* Not a member at all: show Join */}
      {isAuthenticated && isNotMember && (
        <Button
          variant="primary"
          size="sm"
          icon={LogIn}
          loading={joinLoading}
          onClick={onJoin}
        >
          Join Community
        </Button>
      )}

      {/* Head (OWNER) actions */}
      {isHead && (
        <>
          <Button variant="outline" size="sm" icon={Pencil} onClick={onEdit}>
            Edit
          </Button>
          <Button
            variant="outline"
            size="sm"
            icon={ClipboardList}
            onClick={onViewRequests}
          >
            Join Requests
          </Button>
          <Button
            variant="danger"
            size="sm"
            icon={Trash2}
            loading={deleteLoading}
            onClick={onDelete}
          >
            Delete
          </Button>
        </>
      )}

      {/* Co-Head (MODERATOR) actions */}
      {isCoHead && (
        <>
          <Button
            variant="outline"
            size="sm"
            icon={ClipboardList}
            onClick={onViewRequests}
          >
            Join Requests
          </Button>
          <Button
            variant="outline"
            size="sm"
            icon={LogOut}
            loading={leaveLoading}
            onClick={onLeave}
          >
            Leave
          </Button>
        </>
      )}

      {/* Regular member: show Leave */}
      {isMember && (
        <Button
          variant="outline"
          size="sm"
          icon={LogOut}
          loading={leaveLoading}
          onClick={onLeave}
        >
          Leave
        </Button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// CommunityDetailView
// ---------------------------------------------------------------------------

export default function CommunityDetailView() {
  const router = useRouter();
  const params = useParams();
  const communityId = (params?.id as string) ?? "";
  const { user, isAuthenticated } = useAuth();
  const { mutate: globalMutate } = useSWRConfig();

  // ── Community data ────────────────────────────────────────────────────────
  const {
    data: community,
    isLoading,
    error,
    mutate,
  } = useSWR<Community>(
    communityId ? communityKeys.byId(communityId) : null,
    swrFetcher,
    { revalidateOnFocus: false },
  );

  // ── Member profile map — fetched at this level so ManageMemberModal
  //    can show real names without an extra request ─────────────────────────
  const [profileMap, setProfileMap] = useState<ProfileMap>({});

  // ── Local UI state ────────────────────────────────────────────────────────
  const [joinLoading, setJoinLoading] = useState(false);
  const [leaveLoading, setLeaveLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showJoinRequests, setShowJoinRequests] = useState(false);

  // Confirmation dialogs
  const [leaveDialogOpen, setLeaveDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  // ManageMemberModal state
  const [manageMember, setManageMember] = useState<CommunityMember | null>(null);
  const [manageModalOpen, setManageModalOpen] = useState(false);

  const sortedRules = useMemo(() => {
    if (!community?.rules) return [];
    return [...community.rules].sort((a, b) => a.orderIndex - b.orderIndex);
  }, [community?.rules]);

  // Derive role from membershipStatus for permission checks
  const membershipStatus: MembershipViewStatus =
    community?.membershipStatus ?? "NOT_MEMBER";
  const isOwnerOrMod =
    membershipStatus === "HEAD" || membershipStatus === "CO_HEAD";

  // Derive MemberRole for components that still use it
  const currentUserRole: MemberRole | null =
    membershipStatus === "HEAD"
      ? "OWNER"
      : membershipStatus === "CO_HEAD"
        ? "MODERATOR"
        : membershipStatus === "MEMBER"
          ? "MEMBER"
          : null;

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleJoin = useCallback(async () => {
    if (!communityId || !community) return;
    setJoinLoading(true);
    setErrorMsg(null);

    // Optimistic: flip to MEMBER (will be corrected to PENDING by revalidation
    // if community requires approval)
    const optimisticCommunity: Community = {
      ...community,
      membershipStatus: "MEMBER",
      isMember: true,
      memberCount: community.memberCount + 1,
    };
    await mutate(optimisticCommunity, { revalidate: false });

    try {
      const result = await joinCommunity(communityId);
      // Revalidate to get the real state (MEMBER or PENDING)
      await mutate();
      if (result.requested) {
        // Backend will return membershipStatus=PENDING after revalidation
      }
    } catch (e: unknown) {
      // Rollback optimistic update
      await mutate();
      const msg = e instanceof Error ? e.message : "Failed to join community.";
      setErrorMsg(msg);
    } finally {
      setJoinLoading(false);
    }
  }, [communityId, community, mutate]);

  const handleLeaveConfirmed = useCallback(async () => {
    if (!communityId || !community) return;
    setLeaveLoading(true);
    setErrorMsg(null);
    setLeaveDialogOpen(false);

    // Optimistic update
    const optimisticCommunity: Community = {
      ...community,
      membershipStatus: "NOT_MEMBER",
      isMember: false,
      currentUserRole: null,
      memberCount: Math.max(0, community.memberCount - 1),
    };
    await mutate(optimisticCommunity, { revalidate: false });

    try {
      await leaveCommunity(communityId);
      // Revalidate to confirm
      await mutate();
      // Invalidate member list
      globalMutate(
        (key: unknown) =>
          Array.isArray(key) &&
          typeof key[0] === "string" &&
          (key[0] as string).includes(`/communities/${communityId}/members`),
      );
    } catch (e: unknown) {
      await mutate(); // rollback
      const msg =
        e instanceof Error ? e.message : "Failed to leave community.";
      setErrorMsg(msg);
    } finally {
      setLeaveLoading(false);
    }
  }, [communityId, community, mutate, globalMutate]);

  const handleDeleteConfirmed = useCallback(async () => {
    if (!communityId) return;
    setDeleteLoading(true);
    setErrorMsg(null);
    setDeleteDialogOpen(false);

    try {
      await archiveCommunity(communityId);
      globalMutate(
        (key: unknown) =>
          typeof key === "string"
            ? key.includes("/communities")
            : Array.isArray(key) &&
              typeof key[0] === "string" &&
              (key[0] as string).includes("/communities"),
      );
      router.push("/communities");
    } catch (e: unknown) {
      const msg =
        e instanceof Error ? e.message : "Failed to delete community.";
      setErrorMsg(msg);
      setDeleteLoading(false);
    }
  }, [communityId, globalMutate, router]);

  const handleOpenManage = useCallback((member: CommunityMember) => {
    setManageMember(member);
    setManageModalOpen(true);
  }, []);

  // Merge newly-loaded member profiles into the map whenever CommunityMembersSection
  // resolves them. We receive the full map from the section via a callback.
  const handleProfilesResolved = useCallback((map: ProfileMap) => {
    setProfileMap((prev) => ({ ...prev, ...map }));
  }, []);

  const invalidateMembers = useCallback(() => {
    globalMutate(
      (key: unknown) =>
        Array.isArray(key) &&
        typeof key[0] === "string" &&
        (key[0] as string).includes(`/communities/${communityId}/members`),
    );
  }, [communityId, globalMutate]);

  const handlePromote = useCallback(
    async (member: CommunityMember) => {
      // Optimistic: no community-level data changes for promote; just revalidate members
      await updateMemberRole(communityId, member.userId, { role: "MODERATOR" });
      invalidateMembers();
    },
    [communityId, invalidateMembers],
  );

  const handleDemote = useCallback(
    async (member: CommunityMember) => {
      await updateMemberRole(communityId, member.userId, { role: "MEMBER" });
      invalidateMembers();
    },
    [communityId, invalidateMembers],
  );

  const handleRemoveMember = useCallback(
    async (member: CommunityMember) => {
      // Optimistic: decrement member count
      if (community) {
        const optimistic: Community = {
          ...community,
          memberCount: Math.max(0, community.memberCount - 1),
        };
        await mutate(optimistic, { revalidate: false });
      }
      try {
        await removeMember(communityId, member.userId);
        invalidateMembers();
        await mutate();
      } catch (e: unknown) {
        await mutate(); // rollback
        throw e; // re-throw so ManageMemberModal can handle
      }
    },
    [communityId, community, mutate, invalidateMembers],
  );

  // ── Render ────────────────────────────────────────────────────────────────

  if (isLoading) return <CommunityDetailSkeleton />;

  if (error || !community) {
    return (
      <div className="container-main py-8">
        <button
          type="button"
          onClick={() => router.back()}
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-[#111111] mb-6 transition-colors"
        >
          <ArrowLeft size={15} strokeWidth={2} aria-hidden="true" />
          Back
        </button>
        <CommunityDetailError onRetry={() => mutate()} />
      </div>
    );
  }

  return (
    <>
      <motion.div
        className="pb-20"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0, 0, 0.2, 1] }}
      >
        {/* Hero — banner only */}
        <CommunityHero
          bannerUrl={community.bannerUrl}
          onBack={() => router.back()}
        />

        <div className="container-main space-y-6 pt-6">
          {/* Identity + meta */}
          <div className="space-y-2">
            <h1 className="text-2xl font-bold tracking-tight text-[#111111] leading-tight">
              {community.name}
            </h1>
            <CommunityMeta
              visibility={community.visibility}
              location={community.location}
              memberCount={community.memberCount}
            />
          </div>

          {/* Description */}
          {community.description && (
            <p className="text-sm text-gray-700 leading-relaxed max-w-2xl">
              {community.description}
            </p>
          )}

          {/* Pending approval notice — driven by backend membershipStatus */}
          {membershipStatus === "PENDING" && (
            <div className="flex items-center gap-2 px-4 py-3 bg-amber-50 border border-amber-100 rounded-2xl">
              <Clock
                size={14}
                className="text-amber-600 flex-shrink-0"
                aria-hidden="true"
              />
              <p className="text-sm text-amber-800">
                Your join request is pending approval.
              </p>
            </div>
          )}

          {/* Error notice */}
          {errorMsg && (
            <div
              role="alert"
              className="flex items-center justify-between gap-4 bg-red-50 border border-red-100 rounded-2xl px-4 py-3"
            >
              <p className="text-sm text-red-700">{errorMsg}</p>
              <button
                type="button"
                onClick={() => setErrorMsg(null)}
                className="text-xs text-red-500 hover:text-red-700 underline flex-shrink-0"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Action bar */}
          <ActionBar
            membershipStatus={membershipStatus}
            isAuthenticated={isAuthenticated}
            joinLoading={joinLoading}
            leaveLoading={leaveLoading}
            deleteLoading={deleteLoading}
            onJoin={handleJoin}
            onLeave={() => setLeaveDialogOpen(true)}
            onDelete={() => setDeleteDialogOpen(true)}
            onEdit={() => router.push(`/communities/${communityId}/edit`)}
            onViewRequests={() => setShowJoinRequests((v) => !v)}
          />

          {/* Join Requests (OWNER/MOD only, toggled) */}
          {isOwnerOrMod && showJoinRequests && (
            <JoinRequestsSection communityId={communityId} />
          )}

          {/* Members section */}
          <CommunityMembersSection
            communityId={communityId}
            currentUserId={user?.id}
            currentUserRole={currentUserRole}
            onManage={handleOpenManage}
            onProfilesResolved={handleProfilesResolved}
          />

          {/* Rules */}
          {sortedRules.length > 0 && (
            <CommunityRulesSection rules={sortedRules} />
          )}
        </div>
      </motion.div>

      {/* Manage member modal */}
      <ManageMemberModal
        isOpen={manageModalOpen}
        onClose={() => {
          setManageModalOpen(false);
          setManageMember(null);
        }}
        member={manageMember}
        currentUserRole={currentUserRole}
        profiles={profileMap}
        onPromote={handlePromote}
        onDemote={handleDemote}
        onRemove={handleRemoveMember}
      />

      {/* Leave community confirmation */}
      <Dialog
        isOpen={leaveDialogOpen}
        title="Leave Community"
        message={`Are you sure you want to leave ${community.name}? You will need to request to join again.`}
        confirmLabel="Leave"
        cancelLabel="Stay"
        destructive
        loading={leaveLoading}
        onConfirm={handleLeaveConfirmed}
        onCancel={() => setLeaveDialogOpen(false)}
      />

      {/* Delete community confirmation */}
      <Dialog
        isOpen={deleteDialogOpen}
        title="Delete Community"
        message={`Permanently delete "${community.name}"? This cannot be undone and all members will lose access.`}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        destructive
        loading={deleteLoading}
        onConfirm={handleDeleteConfirmed}
        onCancel={() => setDeleteDialogOpen(false)}
      />
    </>
  );
}
