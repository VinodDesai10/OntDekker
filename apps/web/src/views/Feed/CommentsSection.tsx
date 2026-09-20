"use client";

/**
 * CommentsSection — Load, create, edit own, delete own comments
 *
 * Comment and reply author identity is resolved via a single batch call to
 * batchProfilesByAuth().  All unique author IDs from top-level comments AND
 * replies are collected, deduplicated, and resolved in one request.
 *
 * Displays displayName, username, and avatar for each comment/reply author.
 * Clicking an author navigates to /users/{username}.
 * Unresolved profiles fall back to "Unknown user".
 *
 * NOTE: Field names are camelCase because the axios interceptor
 * auto-converts snake_case API responses.
 */

import React, { useEffect, useState, useCallback } from "react";
import { Send, Pencil, Trash2, Check, X } from "lucide-react";
import { useRouter } from "next/navigation";
import {
  getComments,
  createComment,
  updateComment,
  deleteComment,
} from "@/services/feedApi";
import { batchProfilesByAuth, type ProfileMap } from "@/services/users";
import type { RawComment } from "./types";

interface CommentsSectionProps {
  postId: string;
  currentUserId: string | null;
  onCountChange: (delta: number) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Collect every unique authorId from comments and their replies */
function collectAuthorIds(comments: RawComment[]): string[] {
  const ids = new Set<string>();
  for (const c of comments) {
    ids.add(c.authorId);
    for (const r of c.replies ?? []) {
      ids.add(r.authorId);
    }
  }
  return [...ids];
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface AuthorLinkProps {
  authorId: string;
  profileMap: ProfileMap;
  className?: string;
}

function AuthorLink({ authorId, profileMap, className = "" }: AuthorLinkProps) {
  const router = useRouter();
  const profile = profileMap[authorId];
  const displayName = profile ? profile.displayName : "Unknown user";

  if (!profile) {
    return (
      <span className={`font-semibold text-[#111111] ${className}`}>
        {displayName}
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={() => router.push(`/users/${profile.username}`)}
      className={`font-semibold text-[#111111] hover:underline focus:outline-none ${className}`}
      aria-label={`View ${displayName}'s profile`}
    >
      {displayName}
    </button>
  );
}

interface AvatarProps {
  authorId: string;
  profileMap: ProfileMap;
}

function CommentAvatar({ authorId, profileMap }: AvatarProps) {
  const router = useRouter();
  const profile = profileMap[authorId];
  const initial = profile
    ? profile.displayName.charAt(0).toUpperCase()
    : "?";

  const content = profile?.avatarUrl ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={profile.avatarUrl}
      alt={profile.displayName}
      className="size-7 rounded-full object-cover"
    />
  ) : (
    <div className="size-7 rounded-full bg-[#111111] text-white flex items-center justify-center font-bold text-xs">
      {initial}
    </div>
  );

  if (!profile) {
    return <div className="size-7 shrink-0">{content}</div>;
  }

  return (
    <button
      type="button"
      onClick={() => router.push(`/users/${profile.username}`)}
      className="size-7 shrink-0 rounded-full overflow-hidden focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-[#111111]"
      aria-label={`View ${profile.displayName}'s profile`}
    >
      {content}
    </button>
  );
}

// ---------------------------------------------------------------------------
// CommentsSection
// ---------------------------------------------------------------------------

export function CommentsSection({
  postId,
  currentUserId,
  onCountChange,
}: CommentsSectionProps) {
  const [comments, setComments] = useState<RawComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newText, setNewText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Author identity map keyed by auth_user_id
  const [profileMap, setProfileMap] = useState<ProfileMap>({});

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  // ── Resolve author identities for a batch of comments ───────────────────
  const resolveAuthors = useCallback(
    (newComments: RawComment[]) => {
      const ids = collectAuthorIds(newComments);
      if (ids.length === 0) return;
      // Only fetch IDs not already in the map
      const missing = ids.filter((id) => !(id in profileMap));
      if (missing.length === 0) return;
      batchProfilesByAuth(missing).then((map) => {
        setProfileMap((prev) => ({ ...prev, ...map }));
      });
    },
    // profileMap as a dep would cause infinite loop; we intentionally capture
    // its current reference in the closure
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  // ── Load comments ────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getComments(postId)
      .then((res) => {
        if (!cancelled) {
          const raw = res as unknown as { comments?: RawComment[] };
          const loaded = raw.comments ?? (res as unknown as RawComment[]) ?? [];
          setComments(loaded);
          resolveAuthors(loaded);
        }
      })
      .catch(() => {
        if (!cancelled) setComments([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [postId, resolveAuthors]);

  // ── Create comment ───────────────────────────────────────────────────────
  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const text = newText.trim();
    if (!text) return;

    setSubmitting(true);
    try {
      const created = await createComment(postId, { content: text });
      const raw = created as unknown as RawComment;
      setComments((prev) => {
        const updated = [...prev, raw];
        // Resolve the new comment's author (may already be in map)
        resolveAuthors([raw]);
        return updated;
      });
      setNewText("");
      onCountChange(1);
    } catch {
      // silently fail
    } finally {
      setSubmitting(false);
    }
  }

  // ── Save edit ────────────────────────────────────────────────────────────
  async function handleSaveEdit(commentId: string) {
    const text = editText.trim();
    if (!text) return;

    try {
      const updated = await updateComment(commentId, { content: text });
      const raw = updated as unknown as RawComment;
      setComments((prev) =>
        prev.map((c) =>
          c.id === commentId ? { ...c, content: raw.content } : c
        )
      );
      setEditingId(null);
    } catch {
      // silently fail
    }
  }

  // ── Delete comment ───────────────────────────────────────────────────────
  async function handleDelete(commentId: string) {
    try {
      await deleteComment(commentId);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
      onCountChange(-1);
    } catch {
      // silently fail
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-3 border-t border-[#EAE7DF] pt-3">
      {loading ? (
        <p className="text-xs text-gray-400 py-2">Loading comments…</p>
      ) : comments.length === 0 ? (
        <p className="text-xs text-gray-400 py-2">
          No comments yet. Be the first to comment!
        </p>
      ) : (
        comments.map((comment) => {
          const isOwn =
            currentUserId !== null && comment.authorId === currentUserId;
          const isEditing = editingId === comment.id;

          return (
            <div
              key={comment.id}
              className="bg-[#FBF9F4] rounded-xl p-3 text-xs space-y-1.5"
            >
              <div className="flex items-start justify-between gap-2">
                {/* Author avatar + name */}
                <div className="flex items-center gap-2 min-w-0">
                  <CommentAvatar authorId={comment.authorId} profileMap={profileMap} />
                  <div className="min-w-0">
                    <AuthorLink
                      authorId={comment.authorId}
                      profileMap={profileMap}
                      className="truncate max-w-[180px] block"
                    />
                    {profileMap[comment.authorId]?.username && (
                      <span className="text-[10px] text-gray-400">
                        @{profileMap[comment.authorId].username}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[10px] text-gray-400">
                    {new Date(comment.createdAt).toLocaleDateString()}
                  </span>
                  {isOwn && !isEditing && (
                    <>
                      <button
                        type="button"
                        aria-label="Edit comment"
                        onClick={() => {
                          setEditingId(comment.id);
                          setEditText(comment.content);
                        }}
                        className="text-gray-400 hover:text-[#111111] transition-colors"
                      >
                        <Pencil size={12} />
                      </button>
                      <button
                        type="button"
                        aria-label="Delete comment"
                        onClick={() => handleDelete(comment.id)}
                        className="text-gray-400 hover:text-red-600 transition-colors"
                      >
                        <Trash2 size={12} />
                      </button>
                    </>
                  )}
                </div>
              </div>

              {isEditing ? (
                <div className="flex items-center gap-2 mt-1">
                  <input
                    type="text"
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSaveEdit(comment.id);
                      if (e.key === "Escape") setEditingId(null);
                    }}
                    className="flex-1 rounded-lg border border-[#EAE7DF] bg-white px-2.5 py-1 text-xs text-[#111111] outline-none focus:border-[#111111]"
                    autoFocus
                  />
                  <button
                    type="button"
                    aria-label="Save edit"
                    onClick={() => handleSaveEdit(comment.id)}
                    className="text-green-600 hover:text-green-700 transition-colors"
                  >
                    <Check size={14} />
                  </button>
                  <button
                    type="button"
                    aria-label="Cancel edit"
                    onClick={() => setEditingId(null)}
                    className="text-gray-400 hover:text-[#111111] transition-colors"
                  >
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <p className="text-gray-700 leading-relaxed pl-9">
                  {comment.content}
                </p>
              )}

              {/* Nested replies (one level) */}
              {comment.replies && comment.replies.length > 0 && (
                <div className="ml-9 mt-2 space-y-2 border-l-2 border-[#EAE7DF] pl-3">
                  {comment.replies.map((reply) => (
                    <div key={reply.id} className="text-xs space-y-1">
                      <div className="flex items-center gap-2">
                        <CommentAvatar
                          authorId={reply.authorId}
                          profileMap={profileMap}
                        />
                        <div className="min-w-0">
                          <AuthorLink
                            authorId={reply.authorId}
                            profileMap={profileMap}
                            className="truncate max-w-[160px] block"
                          />
                          {profileMap[reply.authorId]?.username && (
                            <span className="text-[10px] text-gray-400">
                              @{profileMap[reply.authorId].username}
                            </span>
                          )}
                        </div>
                      </div>
                      <p className="text-gray-600 pl-9">{reply.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })
      )}

      {/* New comment input */}
      {currentUserId && (
        <form onSubmit={handleCreate} className="flex items-center gap-2 pt-1">
          <input
            type="text"
            placeholder="Write a comment..."
            value={newText}
            onChange={(e) => setNewText(e.target.value)}
            className="flex-1 rounded-xl border border-[#EAE7DF] bg-white px-3 py-1.5 text-xs text-[#111111] outline-none focus:border-[#111111]"
          />
          <button
            type="submit"
            disabled={submitting || !newText.trim()}
            className="rounded-xl bg-[#111111] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#333333] disabled:opacity-50 transition-colors"
          >
            <Send size={13} />
          </button>
        </form>
      )}
    </div>
  );
}
