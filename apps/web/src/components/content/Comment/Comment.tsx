"use client";

/**
 * OntDekker Comment
 *
 * Displays a single comment (or threaded reply) in a post's comment section.
 *
 * Layout:
 *   Flex row — Avatar (xs) on the left, content block on the right.
 *   Content: author display name, @username, body text, action row.
 *
 * Actions:
 *   Like   — Heart icon. Filled + moss-green when liked; muted-slate otherwise.
 *            spring scale 0.8→1.2→1 on toggle.
 *   Reply  — Reply icon + "Reply" label. Calls onReply with the comment id.
 *
 * Variants:
 *   isReply — indented (pl-8) with xs avatar treatment for thread replies.
 *
 * Entry animation (per 06-motion-design.md responsive tier):
 *   opacity 0→1, x -8→0, duration 200ms.
 *
 * createdAt relative time:
 *   < 60s   → "just now"
 *   < 60m   → "Xm"
 *   < 24h   → "Xh"
 *   else    → "MMM D" (e.g. "Jul 27")
 */

import React, { useCallback } from "react";
import { motion } from "motion/react";
import { Heart, Reply } from "lucide-react";
import Avatar from "@/components/feedback/Avatar";
import type { CommentProps } from "./Comment.types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Returns a human-readable relative time string for the given ISO date string.
 * Thresholds: <60s → "just now", <60m → "Xm", <24h → "Xh", else → "MMM D"
 */
function formatRelativeTime(createdAt: string): string {
  const now = Date.now();
  const created = new Date(createdAt).getTime();
  const diffSeconds = Math.floor((now - created) / 1000);

  if (diffSeconds < 60) {
    return "just now";
  }

  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) {
    return `${diffMinutes}m`;
  }

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours}h`;
  }

  // "MMM D" — e.g. "Jul 27"
  return new Date(createdAt).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Comment({
  id,
  author,
  body,
  likesCount,
  isLiked,
  createdAt,
  onLike,
  onReply,
  isReply = false,
}: CommentProps) {
  const handleLike = useCallback(() => {
    onLike?.(id, !isLiked);
  }, [id, isLiked, onLike]);

  const handleReply = useCallback(() => {
    onReply?.(id);
  }, [id, onReply]);

  return (
    <motion.div
      // Entry animation — responsive tier: 200ms, x slide-in from left
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, ease: [0, 0, 0.2, 1] }}
      className={[
        "flex items-start gap-2.5",
        isReply ? "pl-8" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {/* ---------------------------------------------------------------- */}
      {/* Avatar                                                             */}
      {/* ---------------------------------------------------------------- */}
      <Avatar
        src={author.avatarUrl}
        alt={author.displayName}
        size="xs"
        className="mt-0.5 flex-shrink-0"
      />

      {/* ---------------------------------------------------------------- */}
      {/* Content block                                                      */}
      {/* ---------------------------------------------------------------- */}
      <div className="flex-1 min-w-0">
        {/* Author row */}
        <div className="flex items-baseline gap-1.5 flex-wrap">
          <span className="text-sm font-semibold text-ink leading-snug">
            {author.displayName}
          </span>
          <span className="text-[10px] font-mono text-muted-slate">
            @{author.username}
          </span>
          {/* Separator + timestamp */}
          <span
            className="text-[10px] font-mono text-muted-slate ml-auto"
            aria-label={`Posted at ${createdAt}`}
          >
            {formatRelativeTime(createdAt)}
          </span>
        </div>

        {/* Body text */}
        <p className="text-sm text-charcoal mt-1 leading-relaxed break-words">
          {body}
        </p>

        {/* ---------------------------------------------------------------- */}
        {/* Action row                                                        */}
        {/* ---------------------------------------------------------------- */}
        <div
          className="flex items-center gap-0.5 mt-2"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Like button */}
          <motion.button
            type="button"
            aria-label={isLiked ? "Unlike comment" : "Like comment"}
            aria-pressed={isLiked}
            onClick={handleLike}
            className={[
              "flex items-center gap-1 px-2 py-1 rounded-lg",
              "text-xs font-medium transition-colors duration-[var(--duration-responsive)]",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
              isLiked
                ? "text-moss-green"
                : "text-muted-slate hover:text-ink hover:bg-gray-50",
            ].join(" ")}
            whileTap={{ scale: 0.85 }}
            // spring scale 0.8→1.2→1 on toggle
            animate={isLiked ? { scale: [0.8, 1.2, 1] } : { scale: 1 }}
            transition={{
              duration: 0.35,
              ease: [0.34, 1.56, 0.64, 1], // ease-spring
            }}
          >
            <Heart
              size={12}
              strokeWidth={2}
              fill={isLiked ? "currentColor" : "none"}
              aria-hidden="true"
            />
            {likesCount > 0 && (
              <span className="font-mono">{likesCount}</span>
            )}
          </motion.button>

          {/* Reply button */}
          {onReply && (
            <button
              type="button"
              aria-label={`Reply to ${author.displayName}`}
              onClick={handleReply}
              className="
                flex items-center gap-1 px-2 py-1 rounded-lg
                text-xs font-medium text-muted-slate
                hover:text-ink hover:bg-gray-50
                transition-colors duration-[var(--duration-responsive)]
                focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink
              "
            >
              <Reply size={12} strokeWidth={2} aria-hidden="true" />
              <span>Reply</span>
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
