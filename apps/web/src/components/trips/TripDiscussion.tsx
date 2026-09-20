"use client";

/**
 * TripDiscussion
 *
 * Renders the expedition discussion thread for a given trip.
 *
 * Behaviour:
 *  - Fetches messages via GET /api/v1/trips/{tripId}/discussion (page 1 only).
 *  - Resolves author display names and avatars via batchProfilesByAuth() in a
 *    single batch request after the message list loads.
 *  - ORGANIZER and active PARTICIPANT (status === "ACTIVE") see a composer.
 *  - Non-members see a read-only view with a "join to participate" notice.
 *  - On submit the new message is appended to the local list immediately
 *    (optimistic-style) without re-fetching the whole page.
 *  - 403 from POST is caught and displayed as a friendly membership message.
 *  - 404 trip not found is surfaced as an error state.
 *
 * Identity resolution:
 *  - authorId on each DiscussionMessage is the JWT sub (auth UUID).
 *  - batchProfilesByAuth() is used — NOT batchProfiles().
 *  - The returned ProfileMap is keyed by the id field in the batch response,
 *    which for this endpoint equals the auth_user_id (same convention as MembersTab).
 *  - If a profile cannot be resolved, "Unknown user" is shown — never a UUID.
 */

import React, { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { MessageSquare, AlertCircle, Users } from "lucide-react";

import Avatar from "@/components/feedback/Avatar";
import Button from "@/components/feedback/Button";

import { getTripDiscussion, postDiscussionMessage } from "@/services/tripsApi";
import { batchProfilesByAuth, type ProfileMap } from "@/services/users";
import { ApiError } from "@/services/api";

import type { DiscussionMessage } from "@/types/trip";
import type { TripParticipant } from "@/types/trip";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface TripDiscussionProps {
  tripId: string;
  /** Current user's participant record — null when not a member or still loading. */
  myParticipant: TripParticipant | null;
  /** True while the myParticipant value is being fetched. */
  isLoadingMyParticipant: boolean;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_CONTENT_LENGTH = 2000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Determine whether the current user can post.
 * Organizers can always post. Active participants can post.
 */
function canPost(p: TripParticipant | null): boolean {
  if (!p) return false;
  return p.role === "ORGANIZER" || p.status === "ACTIVE";
}

/** Format a timestamp into a readable relative-ish date string. */
function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Skeleton placeholder while messages are loading. */
function DiscussionSkeleton() {
  return (
    <motion.div
      className="space-y-4 py-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      aria-label="Loading discussion"
      data-testid="discussion-skeleton"
    >
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex gap-3 items-start">
          <div className="w-8 h-8 rounded-full bg-gray-100 animate-pulse shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-28 rounded bg-gray-100 animate-pulse" />
            <div className="h-4 w-full rounded bg-gray-100 animate-pulse" />
            <div className="h-4 w-3/4 rounded bg-gray-100 animate-pulse" />
          </div>
        </div>
      ))}
    </motion.div>
  );
}

/** Error state for when the discussion fails to load. */
function DiscussionError({ message }: { message: string }) {
  return (
    <motion.div
      className="py-12 text-center space-y-3 bg-white border border-red-100 rounded-3xl p-8 shadow-2xs"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      role="alert"
      data-testid="discussion-error"
    >
      <AlertCircle
        size={36}
        strokeWidth={1}
        className="text-red-300 mx-auto"
        aria-hidden="true"
      />
      <p className="text-sm font-semibold text-ink">{message}</p>
      <p className="text-xs text-muted-slate max-w-xs mx-auto">
        Please try refreshing the page.
      </p>
    </motion.div>
  );
}

/** Empty discussion state. */
function DiscussionEmpty() {
  return (
    <motion.div
      className="py-12 text-center space-y-2 bg-white border border-gray-100 rounded-3xl p-8 shadow-2xs"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      data-testid="discussion-empty"
    >
      <MessageSquare
        size={36}
        strokeWidth={1}
        className="text-gray-300 mx-auto"
        aria-hidden="true"
      />
      <p className="text-sm font-semibold text-ink">No messages yet.</p>
      <p className="text-xs text-muted-slate max-w-xs mx-auto">
        Be the first to kick off the expedition discussion!
      </p>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Single message row
// ---------------------------------------------------------------------------

interface MessageRowProps {
  message: DiscussionMessage;
  profileMap: ProfileMap;
}

function MessageRow({ message, profileMap }: MessageRowProps) {
  const profile = profileMap[message.authorId];

  // Resolution order:
  //  1. displayName from user-service
  //  2. username from user-service
  //  3. "Unknown user" — neutral fallback, never a UUID
  const displayName =
    profile?.displayName || profile?.username || "Unknown user";
  const avatarUrl = profile?.avatarUrl ?? null;
  const username = profile?.username ?? null;

  return (
    <div className="flex gap-3 items-start py-4 border-b border-gray-100 last:border-0" data-testid="discussion-message">
      <Avatar src={avatarUrl} alt={displayName} size="sm" className="mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className="text-sm font-semibold text-ink truncate">
            {displayName}
          </span>
          {username && (
            <span className="text-xs text-muted-slate truncate">
              @{username}
            </span>
          )}
          <span className="text-xs text-muted-slate ml-auto shrink-0 font-mono">
            {formatTimestamp(message.createdAt)}
          </span>
        </div>
        <p className="mt-1 text-sm text-gray-700 whitespace-pre-wrap break-words">
          {message.content}
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Composer
// ---------------------------------------------------------------------------

interface ComposerProps {
  tripId: string;
  onMessagePosted: (message: DiscussionMessage) => void;
}

function Composer({ tripId, onMessagePosted }: ComposerProps) {
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const trimmed = content.trim();
  const isEmpty = trimmed.length === 0;
  const tooLong = content.length > MAX_CONTENT_LENGTH;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isEmpty || tooLong || submitting) return;

    setSubmitting(true);
    setError(null);

    try {
      const newMessage = await postDiscussionMessage(tripId, trimmed);
      onMessagePosted(newMessage);
      setContent("");
      textareaRef.current?.focus();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setError(
            "You must be an active member to post in this discussion."
          );
        } else if (err.status === 404) {
          setError("Trip not found. It may have been deleted.");
        } else {
          setError("Failed to send your message. Please try again.");
        }
      } else {
        setError("Failed to send your message. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-4 bg-white border border-gray-100 rounded-3xl p-5 shadow-2xs" data-testid="discussion-composer">
      <form onSubmit={handleSubmit} noValidate>
        <label htmlFor="discussion-input" className="sr-only">
          Write a message
        </label>
        <textarea
          id="discussion-input"
          ref={textareaRef}
          value={content}
          onChange={(e) => {
            setContent(e.target.value);
            setError(null);
          }}
          placeholder="Write a message to your fellow expedition members…"
          rows={3}
          maxLength={MAX_CONTENT_LENGTH + 1}
          disabled={submitting}
          className="w-full resize-none rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-ink placeholder:text-muted-slate focus:border-gray-400 focus:bg-white focus:outline-none disabled:opacity-60 transition-colors"
          aria-label="Message composer"
          data-testid="discussion-input"
        />

        {/* Character counter + error */}
        <div className="mt-2 flex items-center justify-between gap-3">
          <div className="flex-1">
            {error && (
              <p
                className="text-xs text-red-600 font-medium"
                role="alert"
                data-testid="composer-error"
              >
                {error}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span
              className={`text-xs font-mono ${
                tooLong ? "text-red-500" : "text-muted-slate"
              }`}
              aria-live="polite"
              aria-label={`${content.length} of ${MAX_CONTENT_LENGTH} characters used`}
            >
              {content.length}/{MAX_CONTENT_LENGTH}
            </span>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={isEmpty || tooLong || submitting}
              loading={submitting}
              data-testid="discussion-submit"
            >
              {submitting ? "Sending…" : "Send"}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Non-member notice
// ---------------------------------------------------------------------------

function NonMemberNotice() {
  return (
    <div
      className="mt-4 flex items-center gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-5 py-4"
      data-testid="non-member-notice"
      role="status"
    >
      <Users size={18} className="text-muted-slate shrink-0" aria-hidden="true" />
      <p className="text-sm text-muted-slate">
        Join this trip to participate in the discussion.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// TripDiscussion (main component)
// ---------------------------------------------------------------------------

export default function TripDiscussion({
  tripId,
  myParticipant,
  isLoadingMyParticipant,
}: TripDiscussionProps) {
  const [messages, setMessages] = useState<DiscussionMessage[]>([]);
  const [profileMap, setProfileMap] = useState<ProfileMap>({});
  const [loadingMessages, setLoadingMessages] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [profilesLoaded, setProfilesLoaded] = useState(false);

  // ---------------------------------------------------------------------------
  // Fetch initial discussion page
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;
    setLoadingMessages(true);
    setLoadError(null);

    getTripDiscussion(tripId, { page: 1, pageSize: 50 })
      .then((res) => {
        if (cancelled) return;
        // Backend returns oldest → newest; display in that order
        setMessages(res.items);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError) {
          if (err.status === 404) {
            setLoadError("This trip was not found. It may have been deleted.");
          } else {
            setLoadError("Unable to load the discussion. Please try again.");
          }
        } else {
          setLoadError("Unable to load the discussion. Please try again.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingMessages(false);
      });

    return () => {
      cancelled = true;
    };
  }, [tripId]);

  // ---------------------------------------------------------------------------
  // Batch-resolve author profiles after messages load
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (loadingMessages || messages.length === 0) {
      setProfilesLoaded(true);
      return;
    }

    const authorIds = [...new Set(messages.map((m) => m.authorId))];

    batchProfilesByAuth(authorIds)
      .then((map) => setProfileMap(map))
      .catch(() => {
        // Degrade gracefully — show "Unknown user" fallback for all authors
        setProfileMap({});
      })
      .finally(() => setProfilesLoaded(true));
  }, [loadingMessages, messages]);

  // ---------------------------------------------------------------------------
  // New message appended from composer
  // ---------------------------------------------------------------------------
  function handleMessagePosted(newMsg: DiscussionMessage) {
    setMessages((prev) => [...prev, newMsg]);

    // Resolve the new author's profile if not already in the map
    if (!profileMap[newMsg.authorId]) {
      batchProfilesByAuth([newMsg.authorId])
        .then((newMap) => setProfileMap((prev) => ({ ...prev, ...newMap })))
        .catch(() => {
          // Keep existing map; new author shows "Unknown user" temporarily
        });
    }
  }

  // ---------------------------------------------------------------------------
  // Render states
  // ---------------------------------------------------------------------------

  // Still loading messages
  if (loadingMessages) {
    return <DiscussionSkeleton />;
  }

  // Failed to load
  if (loadError) {
    return <DiscussionError message={loadError} />;
  }

  const userCanPost = canPost(myParticipant);
  const isLoading = loadingMessages || !profilesLoaded;

  if (isLoading) {
    return <DiscussionSkeleton />;
  }

  return (
    <motion.div
      className="py-6 space-y-0"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      data-testid="trip-discussion"
    >
      {/* Message list */}
      {messages.length === 0 ? (
        <DiscussionEmpty />
      ) : (
        <div className="bg-white border border-gray-100 rounded-3xl px-5 shadow-2xs" data-testid="message-list">
          <h4 className="text-xs font-semibold text-ink uppercase tracking-wider font-mono pt-5 pb-2">
            Discussion
          </h4>
          <div>
            {messages.map((msg) => (
              <MessageRow key={msg.id} message={msg} profileMap={profileMap} />
            ))}
          </div>
        </div>
      )}

      {/* Composer or non-member notice */}
      {!isLoadingMyParticipant && (
        userCanPost ? (
          <Composer tripId={tripId} onMessagePosted={handleMessagePosted} />
        ) : (
          <NonMemberNotice />
        )
      )}
    </motion.div>
  );
}
