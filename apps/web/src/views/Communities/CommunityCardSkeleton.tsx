"use client";

/**
 * CommunityCardSkeleton
 *
 * Animated loading placeholder that matches the exact shape of CommunityCard:
 *   - Name row + category
 *   - Visibility badge placeholder
 *   - Description lines
 *   - Member count + location rows
 *   - Action button
 *
 * Motion: opacity pulse 0.4→0.8→0.4 at 1.5s (same as GuideCardSkeleton)
 */

import { motion } from "motion/react";

function SkeletonCommunityCard() {
  return (
    <motion.div
      className="bg-white border border-gray-100 rounded-3xl p-6 space-y-4"
      animate={{ opacity: [0.4, 0.8, 0.4] }}
      transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
      aria-hidden="true"
    >
      {/* Name + badge row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-1.5">
          <div className="h-3.5 w-36 rounded-full bg-gray-100" />
          <div className="h-2.5 w-20 rounded-full bg-gray-100" />
        </div>
        <div className="h-5 w-14 rounded-full bg-gray-100 flex-shrink-0" />
      </div>

      {/* Description */}
      <div className="space-y-1.5">
        <div className="h-3 w-full rounded-full bg-gray-100" />
        <div className="h-3 w-4/5 rounded-full bg-gray-100" />
      </div>

      {/* Member count + location */}
      <div className="space-y-1.5">
        <div className="h-2.5 w-28 rounded-full bg-gray-100" />
        <div className="h-2.5 w-24 rounded-full bg-gray-100" />
      </div>

      {/* Divider */}
      <div className="h-px bg-gray-100" />

      {/* Action button */}
      <div className="h-8 w-full rounded-xl bg-gray-100" />
    </motion.div>
  );
}

interface CommunityCardSkeletonProps {
  count?: number;
}

export default function CommunityCardSkeleton({
  count = 6,
}: CommunityCardSkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading communities…"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
    >
      {Array.from({ length: count }, (_, i) => (
        <SkeletonCommunityCard key={i} />
      ))}
      <span className="sr-only">Loading communities…</span>
    </div>
  );
}
