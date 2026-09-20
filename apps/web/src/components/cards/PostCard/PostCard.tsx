"use client";

/**
 * OntDekker PostCard
 *
 * Travel story card used in the Discover Feed directory.
 *
 * Information displayed:
 *   - Cover image (when available)
 *   - Title (2-line clamp)
 *   - Location (mono, uppercase)
 *   - Tags (first 3)
 *   - Stats: likes · comments · views (mono)
 *   - Publication date
 *
 * Actions:
 *   Like      — heart toggle, spring scale animation
 *   Bookmark  — spring scale animation
 *   Read      — onClick navigates to /feed/[id]
 */

import React from "react";
import { motion } from "motion/react";
import { Heart, Bookmark, MessageCircle, Eye, MapPin, Calendar } from "lucide-react";
import BaseCard from "@/components/cards/BaseCard";
import Badge from "@/components/feedback/Badge";
import Button from "@/components/feedback/Button";
import type { PostCardProps } from "./PostCard.types";

/** Format ISO date to "Aug 5, 2026" */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function PostCard({
  post,
  onClick,
  onLikeToggle,
  onBookmarkToggle,
  index = 0,
}: PostCardProps) {
  const hasCover = Boolean(post.coverImageUrl);
  const visibleTags = post.tags.slice(0, 3);

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0, 0, 0.2, 1], delay: index * 0.05 }}
    >
      <BaseCard onClick={onClick} ariaLabel={`Read story: ${post.title}`}>
        <div className="space-y-4">
          {/* Cover image */}
          {hasCover && (
            <div className="w-full h-40 rounded-xl overflow-hidden bg-gray-100 -mx-0">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={post.coverImageUrl!}
                alt={post.title}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            </div>
          )}

          {/* Title + action row */}
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-sm font-semibold text-ink leading-snug line-clamp-2 flex-1">
              {post.title}
            </h3>

            {/* Like + Bookmark buttons */}
            <div
              className="flex items-center gap-1 flex-shrink-0"
              onClick={(e) => e.stopPropagation()}
            >
              <motion.button
                type="button"
                aria-label={post.isLiked ? "Unlike story" : "Like story"}
                aria-pressed={post.isLiked}
                onClick={onLikeToggle}
                className={[
                  "flex items-center justify-center w-7 h-7 rounded-lg border",
                  "transition-colors duration-[var(--duration-responsive)]",
                  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
                  post.isLiked
                    ? "bg-red-50 border-red-200 text-red-500"
                    : "bg-white border-gray-100 text-muted-slate hover:text-red-400 hover:border-red-200",
                ].join(" ")}
                whileTap={{ scale: 0.82 }}
                animate={post.isLiked ? { scale: [1, 1.2, 1] } : { scale: 1 }}
                transition={{ duration: 0.35, ease: [0.34, 1.56, 0.64, 1] }}
              >
                <Heart
                  size={13}
                  strokeWidth={2}
                  fill={post.isLiked ? "currentColor" : "none"}
                  aria-hidden="true"
                />
              </motion.button>

              <motion.button
                type="button"
                aria-label={post.isBookmarked ? "Remove bookmark" : "Bookmark story"}
                aria-pressed={post.isBookmarked}
                onClick={onBookmarkToggle}
                className={[
                  "flex items-center justify-center w-7 h-7 rounded-lg border",
                  "transition-colors duration-[var(--duration-responsive)]",
                  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
                  post.isBookmarked
                    ? "bg-amber-50 border-amber-200 text-amber-600"
                    : "bg-white border-gray-100 text-muted-slate hover:text-amber-500 hover:border-amber-200",
                ].join(" ")}
                whileTap={{ scale: 0.82 }}
                animate={post.isBookmarked ? { scale: [1, 1.2, 1] } : { scale: 1 }}
                transition={{ duration: 0.35, ease: [0.34, 1.56, 0.64, 1] }}
              >
                <Bookmark
                  size={13}
                  strokeWidth={2}
                  fill={post.isBookmarked ? "currentColor" : "none"}
                  aria-hidden="true"
                />
              </motion.button>
            </div>
          </div>

          {/* Location */}
          {post.location && (
            <span className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-muted-slate">
              <MapPin size={10} strokeWidth={2} aria-hidden="true" />
              {post.location}
            </span>
          )}

          {/* Tags */}
          {visibleTags.length > 0 && (
            <div className="flex flex-wrap gap-1.5" aria-label="Story tags">
              {visibleTags.map((tag) => (
                <Badge key={tag} variant="default" size="sm">
                  {tag}
                </Badge>
              ))}
              {post.tags.length > 3 && (
                <Badge variant="default" size="sm">
                  +{post.tags.length - 3}
                </Badge>
              )}
            </div>
          )}

          {/* Stats row */}
          <div className="flex items-center gap-3 text-[10px] font-mono text-muted-slate">
            <span className="flex items-center gap-1">
              <Heart size={9} strokeWidth={2} aria-hidden="true" />
              {post.likeCount.toLocaleString()}
            </span>
            <span className="flex items-center gap-1">
              <MessageCircle size={9} strokeWidth={2} aria-hidden="true" />
              {post.commentCount.toLocaleString()}
            </span>
            <span className="flex items-center gap-1">
              <Eye size={9} strokeWidth={2} aria-hidden="true" />
              {post.viewCount.toLocaleString()}
            </span>
            <span className="ml-auto flex items-center gap-1">
              <Calendar size={9} strokeWidth={2} aria-hidden="true" />
              {formatDate(post.createdAt)}
            </span>
          </div>

          {/* Divider */}
          <div className="border-t border-gray-100" aria-hidden="true" />

          {/* Read action */}
          <div
            className="flex items-center gap-2"
            onClick={(e) => e.stopPropagation()}
          >
            <Button
              variant="primary"
              size="sm"
              onClick={onClick}
              className="flex-1"
            >
              Read Story
            </Button>
          </div>
        </div>
      </BaseCard>
    </motion.div>
  );
}
