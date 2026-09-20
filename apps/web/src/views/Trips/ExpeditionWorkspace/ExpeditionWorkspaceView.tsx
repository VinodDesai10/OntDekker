"use client";

/**
 * OntDekker ExpeditionWorkspaceView
 *
 * Expedition workspace page. Navigated to from Feed, MyTripsView, or CommunityDetailView.
 *
 * Tabs:
 *   Overview    — details, dates, budget, capacity, registration CTA
 *   Discussion  — expedition discussion thread
 *   Packing     — gear list with weight summary + WeightBadge
 *   Gallery     — photo gallery
 *   Members     — participant roster with real user profiles
 *
 * Data sources (all real — no mock data):
 *   - Trip detail:         GET /api/v1/trips/{id}                              → Trip
 *   - My participant:      GET /api/v1/trips/{id}/me/participant               → TripParticipant | null
 *   - Participants:        GET /expeditions/api/v1/expeditions/{id}/participants → TripParticipant[]
 *   - User profiles:       POST /users/batch-profiles-by-auth (user-service) → ProfileMap
 *   - Gallery:             GET /expeditions/api/v1/expeditions/{id}/gallery    → GalleryResponse
 *   - Gear:                GET /expeditions/api/v1/expeditions/{id}/gear       → GearResponse
 *
 * Registration lifecycle:
 *   - ORGANIZER  → shows "You are the Organiser" badge + Delete Trip button
 *   - PARTICIPANT → shows "Registered" state — no re-register button
 *   - NOT REGISTERED → shows "Register for Expedition" button → POST /api/v1/trips/{id}/join
 *   - After join: revalidates trip, participants, my-trips
 *   - Duplicate join (409 ALREADY_MEMBER) → handled gracefully
 *
 * Deletion (organizer only):
 *   - Delete button visible only to the organizer (user.id === trip.hostId)
 *   - Confirmation dialog prevents accidental deletion
 *   - DELETE /api/v1/trips/{id} — backend enforces authorization
 *   - On success: invalidates trip cache, public trips, my-trips → navigates to /trips
 */

import React, { useEffect, useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import { motion, AnimatePresence } from "motion/react";
import {
  LayoutDashboard,
  MessageSquare,
  Backpack,
  ImageIcon,
  Users,
  CheckCircle2,
  UserPlus,
  Crown,
  Trash2,
  X,
} from "lucide-react";

import ExpeditionHeader from "@/components/headers/ExpeditionHeader";
import Tabs from "@/components/navigation/Tabs";
import Avatar from "@/components/feedback/Avatar";
import Button from "@/components/feedback/Button";

import { swrFetcher, expeditionKeys, tripKeys } from "@/services/cache";
import { useRouter, useParams } from "next/navigation";
import { useToast } from "@/hooks/useToast";
import { useAuth } from "@/contexts/AuthContext";
import { batchProfilesByAuth, type ProfileMap } from "@/services/users";
import { joinTrip, deleteTrip } from "@/services/tripsApi";
import { ApiError } from "@/services/api";
import TripDiscussion from "@/components/trips/TripDiscussion";
import PackingTab from "@/components/trips/PackingTab";
import GalleryTab from "@/components/trips/GalleryTab";
import type { Trip, TripParticipant } from "@/types/trip";
import type { TabItem } from "@/components/navigation/Tabs";

// ---------------------------------------------------------------------------
// Tab definitions
// ---------------------------------------------------------------------------

const TABS: TabItem[] = [
  { id: "overview",    label: "Overview",    icon: LayoutDashboard },
  { id: "discussion",  label: "Discussion",  icon: MessageSquare },
  { id: "packing",     label: "Packing",     icon: Backpack },
  { id: "gallery",     label: "Gallery",     icon: ImageIcon },
  { id: "members",     label: "Members",     icon: Users },
];

// ---------------------------------------------------------------------------
// SWR key for the current user's participant status
// ---------------------------------------------------------------------------
const myParticipantKey = (tripId: string) =>
  `/api/v1/trips/${tripId}/me/participant`;

// ---------------------------------------------------------------------------
// Tab: Overview
// ---------------------------------------------------------------------------

interface OverviewTabProps {
  trip: Trip;
  tripId: string;
  myParticipant: TripParticipant | null;
  isLoadingMyParticipant: boolean;
}

function OverviewTab({
  trip,
  tripId,
  myParticipant,
  isLoadingMyParticipant,
}: OverviewTabProps) {
  const { showToast } = useToast();
  const { mutate } = useSWRConfig();
  const [joining, setJoining] = useState(false);

  // Derive registration state from real participant record
  const isOrganizer = myParticipant?.role === "ORGANIZER";
  const isRegistered = myParticipant?.status === "ACTIVE";

  // Participant count comes from the real backend (count_active_participants)
  const count = trip.currentParticipantsCount;

  async function handleRegister() {
    if (joining) return;
    setJoining(true);
    try {
      await joinTrip(tripId);
      showToast("Registered successfully for the expedition! Check your packing list.", "success");
      // Revalidate trip detail (count), participants list, my-trips, and my participant status
      await Promise.all([
        mutate(tripKeys.byId(tripId)),
        mutate(expeditionKeys.participants(tripId)),
        mutate(myParticipantKey(tripId)),
        mutate(
          (key) => Array.isArray(key) && key[0] === tripKeys.mine()[0],
          undefined,
          { revalidate: true },
        ),
      ]);
    } catch (err) {
      if (err instanceof ApiError && err.code === "ALREADY_MEMBER") {
        showToast("You are already registered for this expedition.", "info");
        // Revalidate to sync state in case of desync
        await mutate(myParticipantKey(tripId));
      } else {
        showToast("Failed to register. Please try again.", "error");
      }
    } finally {
      setJoining(false);
    }
  }

  function renderRegistrationButton() {
    if (isLoadingMyParticipant) {
      return (
        <div className="h-9 w-40 rounded-xl bg-gray-100 animate-pulse" />
      );
    }

    if (isOrganizer) {
      return (
        <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-700 text-sm font-medium">
          <Crown size={15} />
          You are the Organiser
        </div>
      );
    }

    if (isRegistered) {
      return (
        <Button
          variant="outline"
          size="md"
          disabled
          className="border-green-200 bg-green-50 text-green-700 cursor-default"
        >
          <CheckCircle2 size={16} className="mr-1.5" />
          Registered
        </Button>
      );
    }

    return (
      <Button
        variant="primary"
        size="md"
        onClick={handleRegister}
        disabled={joining}
      >
        {joining ? (
          <span className="flex items-center gap-2">
            <span className="h-3.5 w-3.5 rounded-full border-2 border-white border-t-transparent animate-spin" />
            Registering…
          </span>
        ) : (
          <>
            <UserPlus size={16} className="mr-1.5" />
            Register for Expedition
          </>
        )}
      </Button>
    );
  }

  return (
    <motion.div
      className="py-6 space-y-5"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      {/* Registration Callout */}
      <div className="bg-white border border-[#EAE7DF] rounded-3xl p-6 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-ink">Expedition Registration</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {count} / {trip.maxParticipants} spots filled&nbsp;
            ({Math.max(0, trip.maxParticipants - count)} spots left)
          </p>
        </div>
        {renderRegistrationButton()}
      </div>

      <div className="bg-white border border-gray-100 rounded-3xl p-5 space-y-3 shadow-2xs">
        <h3 className="text-xs font-mono uppercase tracking-wider text-muted-slate">Details</h3>
        <dl className="space-y-2 text-sm">
          {trip.startDate && (
            <div className="flex justify-between">
              <dt className="text-muted-slate">Start</dt>
              <dd className="font-mono font-medium text-ink">
                {new Date(trip.startDate).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </dd>
            </div>
          )}
          {trip.endDate && (
            <div className="flex justify-between">
              <dt className="text-muted-slate">End</dt>
              <dd className="font-mono font-medium text-ink">
                {new Date(trip.endDate).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </dd>
            </div>
          )}
          {trip.budget !== null && (
            <div className="flex justify-between">
              <dt className="text-muted-slate">Budget</dt>
              <dd className="font-mono font-medium text-ink">
                ${Number(trip.budget).toLocaleString()}
              </dd>
            </div>
          )}
          <div className="flex justify-between">
            <dt className="text-muted-slate">Capacity</dt>
            <dd className="font-mono font-medium text-ink">
              {count} / {trip.maxParticipants}
            </dd>
          </div>
        </dl>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Discussion
// Delegates to the dedicated TripDiscussion component.
// ---------------------------------------------------------------------------

interface DiscussionTabProps {
  tripId: string;
  myParticipant: TripParticipant | null;
  isLoadingMyParticipant: boolean;
}

function DiscussionTab({ tripId, myParticipant, isLoadingMyParticipant }: DiscussionTabProps) {
  return (
    <TripDiscussion
      tripId={tripId}
      myParticipant={myParticipant}
      isLoadingMyParticipant={isLoadingMyParticipant}
    />
  );
}

// ---------------------------------------------------------------------------
// Tab: Members
// Fetches participants, then batch-resolves real user profiles from user-service.
//
// Identity resolution:
//   expedition_participants.user_id == JWT sub claim (auth-service UUID).
//   Must use batchProfilesByAuth() — NOT batchProfiles() — because the
//   latter expects user-service profile UUIDs, which are different.
// ---------------------------------------------------------------------------

function MembersTab({
  expeditionId,
  trip,
}: {
  expeditionId: string;
  trip: Trip;
}) {
  const router = useRouter();

  const { data: participants, isLoading } = useSWR<TripParticipant[]>(
    expeditionKeys.participants(expeditionId),
    swrFetcher,
    { revalidateOnFocus: false }
  );

  // Real user profiles fetched from user-service via POST /users/batch-profiles-by-auth.
  // The participant user_id is the JWT sub claim (auth UUID), so we use the
  // auth-keyed batch endpoint — the returned map is keyed by auth_user_id.
  const [profileMap, setProfileMap] = useState<ProfileMap>({});
  const [profilesLoading, setProfilesLoading] = useState(false);

  useEffect(() => {
    if (!participants || participants.length === 0) return;

    const authUserIds = participants.map((p) => p.user_id);
    setProfilesLoading(true);
    batchProfilesByAuth(authUserIds)
      .then((map) => setProfileMap(map))
      .catch(() => {
        // If user-service is unavailable, degrade gracefully — show neutral fallback
        setProfileMap({});
      })
      .finally(() => setProfilesLoading(false));
  }, [participants]);

  /** Role display label — matches backend enum values. */
  function roleLabel(role: TripParticipant["role"]): string {
    switch (role) {
      case "ORGANIZER":    return "Organiser";
      case "CO_ORGANIZER": return "Co-Organiser";
      default:             return "Participant";
    }
  }

  /**
   * Display name for a participant.
   *
   * Resolution order:
   *   1. displayName from user-service profile (real name the user set)
   *   2. username from user-service profile (if display_name is empty)
   *   3. "Member" — neutral fallback when user-service has no record for this ID
   *
   * Never derives name from UUID, never shows fake names.
   */
  function displayName(participant: TripParticipant): string {
    const profile = profileMap[participant.user_id];
    if (profile?.displayName) return profile.displayName;
    if (profile?.username) return profile.username;
    return "Member";
  }

  /**
   * Avatar URL for a participant.
   * Returns null when user-service has no avatar — Avatar component handles fallback.
   */
  function avatarUrl(participant: TripParticipant): string | null {
    return profileMap[participant.user_id]?.avatarUrl ?? null;
  }

  /**
   * Navigate to the public profile page for this participant.
   * Only navigates when a username is available from the profile map.
   */
  function handleProfileClick(participant: TripParticipant): void {
    const username = profileMap[participant.user_id]?.username;
    if (username) {
      router.push(`/users/${username}`);
    }
  }

  const loading = isLoading || profilesLoading;

  if (loading) {
    return (
      <motion.div
        className="py-6 bg-white border border-gray-100 rounded-3xl p-5 space-y-3 shadow-2xs"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-10 rounded-xl bg-gray-100 animate-pulse" />
        ))}
      </motion.div>
    );
  }

  const memberList = participants ?? [];

  if (memberList.length === 0) {
    return (
      <motion.div
        className="py-12 text-center space-y-2 bg-white border border-gray-100 rounded-3xl p-8 shadow-2xs"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
      >
        <Users
          size={36}
          strokeWidth={1}
          className="text-gray-300 mx-auto"
          aria-hidden="true"
        />
        <p className="text-sm font-semibold text-ink">No members yet.</p>
      </motion.div>
    );
  }

  return (
    <motion.div
      className="py-6 bg-white border border-gray-100 rounded-3xl p-5 space-y-3 shadow-2xs"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <h4 className="text-xs font-semibold text-ink uppercase tracking-wider font-mono">
        Expedition Roster
        <span className="ml-2 font-normal text-muted-slate normal-case tracking-normal">
          {memberList.length} / {trip.maxParticipants}
        </span>
      </h4>
      <div className="divide-y divide-gray-100">
        {memberList.map((m) => {
          const username = profileMap[m.user_id]?.username;
          const isClickable = !!username;
          return (
            <div
              key={m.id}
              className={`py-3 flex items-center justify-between ${
                isClickable
                  ? "cursor-pointer hover:bg-gray-50 rounded-xl px-2 -mx-2 transition-colors"
                  : ""
              }`}
              onClick={isClickable ? () => handleProfileClick(m) : undefined}
              role={isClickable ? "button" : undefined}
              tabIndex={isClickable ? 0 : undefined}
              onKeyDown={
                isClickable
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        handleProfileClick(m);
                      }
                    }
                  : undefined
              }
              aria-label={
                isClickable
                  ? `View profile of ${displayName(m)}`
                  : undefined
              }
            >
              <div className="flex items-center gap-3">
                <Avatar src={avatarUrl(m)} alt={displayName(m)} size="sm" />
                <span className="text-sm font-medium text-ink">{displayName(m)}</span>
              </div>
              <span className="text-xs font-mono text-muted-slate">{roleLabel(m.role)}</span>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// DeleteTripModal — confirmation dialog before hard-committing deletion
// ---------------------------------------------------------------------------

interface DeleteTripModalProps {
  tripTitle: string;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}

function DeleteTripModal({ tripTitle, onConfirm, onClose }: DeleteTripModalProps) {
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    if (deleting) return;
    setDeleting(true);
    try {
      await onConfirm();
      // onConfirm handles navigation — modal stays mounted until parent unmounts
    } catch {
      // Error toast shown by caller; re-enable button
      setDeleting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-trip-title"
    >
      <div className="relative w-full max-w-sm rounded-2xl bg-white border border-[#EAE7DF] p-6 shadow-xl space-y-5">
        <div className="flex items-center justify-between">
          <h2 id="delete-trip-title" className="text-sm font-bold text-[#111111]">
            Delete Trip
          </h2>
          <button
            type="button"
            aria-label="Close dialog"
            onClick={onClose}
            disabled={deleting}
            className="text-gray-400 hover:text-[#111111] transition-colors disabled:opacity-50"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <div className="space-y-2">
          <p className="text-sm text-gray-700">
            Are you sure you want to delete{" "}
            <span className="font-semibold text-[#111111]">
              &ldquo;{tripTitle}&rdquo;
            </span>
            ?
          </p>
          <p className="text-xs text-gray-500">
            This action cannot be undone. All participants will be removed from the trip.
          </p>
        </div>

        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={deleting}
            className="px-4 py-2 text-xs font-medium text-gray-500 hover:text-[#111111] disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="inline-flex items-center gap-1.5 rounded-xl bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-50"
          >
            <Trash2 size={13} aria-hidden="true" />
            {deleting ? "Deleting…" : "Delete Trip"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function WorkspaceSkeleton() {
  return (
    <div className="pb-20 animate-pulse">
      <div className="container-main pt-6">
        <div className="h-52 w-full rounded-3xl bg-gray-100" />
        <div className="mt-5 space-y-3">
          <div className="h-3 w-24 rounded bg-gray-100" />
          <div className="h-7 w-3/4 rounded bg-gray-100" />
          <div className="h-3 w-40 rounded bg-gray-100" />
        </div>
      </div>
      <div className="container-main mt-6">
        <div className="h-10 w-full rounded-2xl bg-gray-100" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

function WorkspaceError({ onBack }: { onBack: () => void }) {
  return (
    <div className="container-main pt-12 text-center space-y-3 pb-20">
      <p className="text-sm font-semibold text-ink">Trip not found.</p>
      <p className="text-xs text-muted-slate">
        This trip may have been deleted or the link is incorrect.
      </p>
      <Button variant="outline" size="sm" onClick={onBack}>
        Go Back
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ExpeditionWorkspaceView
// ---------------------------------------------------------------------------

export default function ExpeditionWorkspaceView() {
  const router = useRouter();
  const params = useParams();
  const { user } = useAuth();
  const { mutate } = useSWRConfig();
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState("overview");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const tripId = (params.id as string) ?? "";

  // Trip detail
  const {
    data: trip,
    error,
    isLoading,
  } = useSWR<Trip>(
    tripId ? tripKeys.byId(tripId) : null,
    swrFetcher,
    { revalidateOnFocus: false }
  );

  // Current user's participant status — fetched from dedicated endpoint.
  // This determines whether to show Register / Organiser / Registered.
  const {
    data: myParticipant,
    isLoading: isLoadingMyParticipant,
  } = useSWR<TripParticipant | null>(
    // Only fetch when trip is loaded and user is authenticated
    tripId && user ? myParticipantKey(tripId) : null,
    swrFetcher,
    { revalidateOnFocus: false }
  );

  // Only the organizer sees the delete button.
  // Compare user.id (string UUID from /auth/me) against trip.hostId (string UUID from backend).
  const isOrganizer = !!user && !!trip && user.id === trip.hostId;

  async function handleDeleteConfirm() {
    if (!trip) return;
    await deleteTrip(tripId);
    // Invalidate all trip-related caches so listings update immediately
    await Promise.all([
      mutate(tripKeys.byId(tripId), undefined, { revalidate: false }),
      mutate(
        (key) => Array.isArray(key) && key[0] === tripKeys.all()[0],
        undefined,
        { revalidate: true },
      ),
      mutate(
        (key) => Array.isArray(key) && key[0] === tripKeys.mine()[0],
        undefined,
        { revalidate: true },
      ),
    ]);
    showToast("Trip deleted successfully.", "success");
    router.push("/trips");
  }

  async function handleDeleteWithErrorHandling() {
    try {
      await handleDeleteConfirm();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          showToast("You are not authorised to delete this trip.", "error");
        } else if (err.status === 404) {
          showToast("Trip not found — it may have already been deleted.", "error");
        } else {
          showToast("Failed to delete the trip. Please try again.", "error");
        }
      } else {
        showToast("Failed to delete the trip. Please try again.", "error");
      }
      // Re-throw so DeleteTripModal can reset its loading state
      throw err;
    }
  }

  if (isLoading && !trip) {
    return <WorkspaceSkeleton />;
  }

  if (error || !trip) {
    return <WorkspaceError onBack={() => router.back()} />;
  }

  return (
    <>
      {/* Delete confirmation dialog — rendered at root so it overlays everything */}
      {deleteDialogOpen && (
        <DeleteTripModal
          tripTitle={trip.title}
          onConfirm={handleDeleteWithErrorHandling}
          onClose={() => setDeleteDialogOpen(false)}
        />
      )}

      <motion.div
        className="pb-20"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0, 0, 0.2, 1] }}
      >
        {/* Expedition header + organizer delete action */}
        <div className="container-main pt-6">
          <ExpeditionHeader trip={trip} onBack={() => router.back()} />

          {/* Delete Trip button — only visible to organizer */}
          {isOrganizer && (
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => setDeleteDialogOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-xl border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-100 hover:border-red-300 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600"
                aria-label={`Delete trip: ${trip.title}`}
              >
                <Trash2 size={12} aria-hidden="true" />
                Delete Trip
              </button>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="container-main mt-6">
          <Tabs tabs={TABS} activeTabId={activeTab} onChange={setActiveTab} />
        </div>

        {/* Tab content */}
        <div className="container-main mt-5">
          <AnimatePresence mode="wait">
            {activeTab === "overview" && (
              <OverviewTab
                key="overview"
                trip={trip}
                tripId={tripId}
                myParticipant={myParticipant ?? null}
                isLoadingMyParticipant={isLoadingMyParticipant}
              />
            )}
            {activeTab === "discussion" && <DiscussionTab key="discussion" tripId={tripId} myParticipant={myParticipant ?? null} isLoadingMyParticipant={isLoadingMyParticipant} />}
            {activeTab === "packing" && (
              <PackingTab key="packing" expeditionId={tripId} myParticipant={myParticipant ?? null} />
            )}
            {activeTab === "gallery" && (
              <GalleryTab key="gallery" expeditionId={tripId} />
            )}
            {activeTab === "members" && (
              <MembersTab key="members" expeditionId={tripId} trip={trip} />
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </>
  );
}
