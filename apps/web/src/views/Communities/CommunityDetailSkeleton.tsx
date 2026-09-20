"use client";

/**
 * CommunityDetailSkeleton
 *
 * Animated loading placeholder that mirrors the exact shape of
 * CommunityDetailView:
 *
 *   1. Banner (full-width, 320 px, rounded-b-3xl)
 *   2. Avatar (128 × 128, circular, overlaps banner by -mt-16)
 *      — rendered as first child of container-main, matching the view
 *   3. Name line + meta chips
 *   4. Description lines
 *   5. Action button placeholder
 *   6. Members section header
 *   7. Rules section header + card
 *
 * Motion: opacity pulse 0.4 → 0.8 → 0.4 at 1.5 s (consistent with all
 * other OntDekker skeletons).
 */

import { motion } from "motion/react";

export default function CommunityDetailSkeleton() {
  return (
    <motion.div
      className="pb-20"
      animate={{ opacity: [0.4, 0.8, 0.4] }}
      transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
      aria-hidden="true"
      role="status"
      aria-label="Loading community…"
    >
      {/* ── Banner ───────────────────────────────────────────────────────── */}
      <div className="h-80 w-full rounded-b-3xl bg-gray-100" />

      <div className="container-main space-y-6 pt-6">
        {/* ── Name + meta chips ───────────────────────────────────────────── */}
        <div className="space-y-2">
          <div className="h-6 w-56 rounded-full bg-gray-100" />
          <div className="flex items-center gap-3 flex-wrap">
            <div className="h-3 w-14 rounded-full bg-gray-100" />
            <div className="h-3 w-20 rounded-full bg-gray-100" />
            <div className="h-3 w-18 rounded-full bg-gray-100" />
          </div>
        </div>

        {/* ── Description ─────────────────────────────────────────────────── */}
        <div className="space-y-1.5">
          <div className="h-3 w-full rounded-full bg-gray-100" />
          <div className="h-3 w-5/6 rounded-full bg-gray-100" />
          <div className="h-3 w-4/6 rounded-full bg-gray-100" />
        </div>

        {/* ── Action buttons row ───────────────────────────────────────────── */}
        <div className="flex items-center gap-2">
          <div className="h-9 w-28 rounded-xl bg-gray-100" />
        </div>

        {/* ── Members section ─────────────────────────────────────────────── */}
        <div className="space-y-3">
          <div className="h-4 w-24 rounded-full bg-gray-100" />
          <div className="bg-white border border-gray-100 rounded-3xl px-5 divide-y divide-gray-100 shadow-sm">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="py-3 flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-gray-200 flex-shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-3 w-28 bg-gray-100 rounded-full" />
                  <div className="h-2.5 w-16 bg-gray-100 rounded-full" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Rules section ───────────────────────────────────────────────── */}
        <div className="space-y-3">
          <div className="h-4 w-32 rounded-full bg-gray-100" />
          <div className="bg-white border border-gray-100 rounded-3xl p-5 space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="space-y-1.5 py-3 border-b border-gray-100 last:border-0"
              >
                <div className="h-3.5 w-32 rounded-full bg-gray-100" />
                <div className="h-3 w-full rounded-full bg-gray-100" />
                <div className="h-3 w-4/5 rounded-full bg-gray-100" />
              </div>
            ))}
          </div>
        </div>
      </div>

      <span className="sr-only">Loading community…</span>
    </motion.div>
  );
}
