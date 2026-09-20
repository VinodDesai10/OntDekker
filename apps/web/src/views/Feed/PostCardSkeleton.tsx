"use client";

/**
 * PostCardSkeleton
 *
 * Animated loading placeholder that matches the shape of PostCard:
 *   - Title lines
 *   - Location row
 *   - Tag chips
 *   - Stats row
 *   - Action button
 *
 * Motion: opacity pulse 0.4→0.8→0.4 at 1.5s (same as GuideCardSkeleton)
 */

import React from "react";
import { motion } from "motion/react";

function SkeletonPostCard() {
  return (
    <motion.div
      className="bg-white border border-gray-100 rounded-3xl p-6 space-y-4"
      animate={{ opacity: [0.4, 0.8, 0.4] }}
      transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
      aria-hidden="true"
    >
      {/* Cover image placeholder */}
      <div className="w-full h-40 rounded-xl bg-gray-100" />

      {/* Title + action buttons row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 space-y-1.5">
          <div className="h-3.5 w-full rounded-full bg-gray-100" />
          <div className="h-3.5 w-4/5 rounded-full bg-gray-100" />
        </div>
        <div className="flex gap-1">
          <div className="w-7 h-7 rounded-lg bg-gray-100" />
          <div className="w-7 h-7 rounded-lg bg-gray-100" />
        </div>
      </div>

      {/* Location */}
      <div className="h-2.5 w-24 rounded-full bg-gray-100" />

      {/* Tags */}
      <div className="flex gap-1.5">
        <div className="h-5 w-14 rounded-full bg-gray-100" />
        <div className="h-5 w-16 rounded-full bg-gray-100" />
        <div className="h-5 w-12 rounded-full bg-gray-100" />
      </div>

      {/* Stats row */}
      <div className="flex gap-3">
        <div className="h-2.5 w-8 rounded-full bg-gray-100" />
        <div className="h-2.5 w-8 rounded-full bg-gray-100" />
        <div className="h-2.5 w-8 rounded-full bg-gray-100" />
        <div className="ml-auto h-2.5 w-20 rounded-full bg-gray-100" />
      </div>

      {/* Divider */}
      <div className="h-px bg-gray-100" />

      {/* Action button */}
      <div className="h-8 w-full rounded-xl bg-gray-100" />
    </motion.div>
  );
}

interface PostCardSkeletonProps {
  count?: number;
}

export default function PostCardSkeleton({ count = 6 }: PostCardSkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading stories…"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
    >
      {Array.from({ length: count }, (_, i) => (
        <SkeletonPostCard key={i} />
      ))}
      <span className="sr-only">Loading stories…</span>
    </div>
  );
}
