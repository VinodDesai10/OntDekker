"use client";

/**
 * TripCardSkeleton — loading skeleton matching TripCard shape:
 * cover image, destination+title, dates+participants, organiser.
 */

import React from "react";
import { motion } from "motion/react";

function SkeletonTripCard() {
  return (
    <motion.div
      className="bg-white border border-gray-100 rounded-3xl overflow-hidden"
      animate={{ opacity: [0.4, 0.8, 0.4] }}
      transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
      aria-hidden="true"
    >
      {/* Cover image */}
      <div className="h-36 w-full bg-gray-100" />
      {/* Content */}
      <div className="p-4 space-y-3">
        <div className="h-2.5 w-20 rounded-full bg-gray-100" />
        <div className="h-4 w-full rounded-full bg-gray-100" />
        <div className="grid grid-cols-2 gap-2">
          <div className="h-2.5 w-full rounded-full bg-gray-100" />
          <div className="h-2.5 w-full rounded-full bg-gray-100" />
          <div className="h-2.5 col-span-2 w-3/5 rounded-full bg-gray-100" />
        </div>
        <div className="h-3 w-32 rounded-full bg-gray-100" />
      </div>
    </motion.div>
  );
}

export default function TripCardSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div
      role="status"
      aria-label="Loading trips…"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
    >
      {Array.from({ length: count }, (_, i) => (
        <SkeletonTripCard key={i} />
      ))}
      <span className="sr-only">Loading trips…</span>
    </div>
  );
}
