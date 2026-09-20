"use client";

/**
 * GuideCardSkeleton
 *
 * Animated loading placeholder that matches the exact shape of GuideCard:
 *   - Avatar (md) + name row
 *   - Rating row
 *   - Location + language rows
 *   - Bio lines
 *   - Action buttons
 *
 * Motion: opacity pulse 0.4→0.8→0.4 at 1.5s (same as FeedSkeleton)
 */

import React from "react";
import { motion } from "motion/react";

function SkeletonGuideCard() {
  return (
    <motion.div
      className="bg-white border border-gray-100 rounded-3xl p-6 space-y-4"
      animate={{ opacity: [0.4, 0.8, 0.4] }}
      transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
      aria-hidden="true"
    >
      {/* Avatar + name + bookmark row */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-gray-100 flex-shrink-0" />
          <div className="space-y-1.5">
            <div className="h-3 w-28 rounded-full bg-gray-100" />
            <div className="h-4 w-14 rounded-full bg-gray-100" />
          </div>
        </div>
        <div className="w-8 h-8 rounded-xl bg-gray-100" />
      </div>

      {/* Rating row */}
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 rounded-full bg-gray-100" />
        <div className="h-3 w-10 rounded-full bg-gray-100" />
        <div className="h-3 w-20 rounded-full bg-gray-100" />
      </div>

      {/* Location + language */}
      <div className="space-y-1.5">
        <div className="h-2.5 w-24 rounded-full bg-gray-100" />
        <div className="h-2.5 w-20 rounded-full bg-gray-100" />
      </div>

      {/* Bio */}
      <div className="space-y-1.5">
        <div className="h-3 w-full rounded-full bg-gray-100" />
        <div className="h-3 w-4/5 rounded-full bg-gray-100" />
      </div>

      {/* Divider */}
      <div className="h-px bg-gray-100" />

      {/* Action buttons */}
      <div className="flex gap-2">
        <div className="h-8 flex-1 rounded-xl bg-gray-100" />
        <div className="h-8 flex-1 rounded-xl bg-gray-100" />
      </div>
    </motion.div>
  );
}

interface GuideCardSkeletonProps {
  count?: number;
}

export default function GuideCardSkeleton({ count = 6 }: GuideCardSkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading guides…"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
    >
      {Array.from({ length: count }, (_, i) => (
        <SkeletonGuideCard key={i} />
      ))}
      <span className="sr-only">Loading guides…</span>
    </div>
  );
}
