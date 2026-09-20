"use client";

/**
 * GalleryTab — CP-TRIP-3D
 *
 * Displays real photos belonging to a trip/expedition.
 * Data source: GET /expeditions/api/v1/expeditions/{id}/gallery
 *              → { expeditionId, photos: GalleryPhoto[], totalPhotos }
 *
 * States:
 *   loading  — skeleton placeholders while the SWR fetch is in flight
 *   error    — error card if the API call fails
 *   empty    — friendly message when the trip has no photos yet
 *   gallery  — responsive grid of real images from the API
 *
 * Image rendering:
 *   - Uses photo.imageUrl directly from the API (no hardcoded/fake URLs)
 *   - Broken/missing images are replaced with a placeholder icon via onError
 *
 * Upload:
 *   - The backend POST /expeditions/api/v1/expeditions/{id}/gallery endpoint
 *     exists but requires a MinIO pre-signed URL workflow not yet implemented.
 *   - This component is READ-ONLY. Upload requires a future MinIO checkpoint.
 *
 * Caching:
 *   - SWR key: expeditionKeys.gallery(expeditionId)
 *   - Follows the existing expedition cache pattern (expeditionKeys.*)
 *   - No manual cache writes in this read-only tab
 */

import React, { useState } from "react";
import useSWR from "swr";
import { motion } from "motion/react";
import { ImageOff, AlertTriangle } from "lucide-react";

import { swrFetcher, expeditionKeys } from "@/services/cache";
import type { GalleryPhoto } from "@/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type GalleryResponse = {
  expeditionId: string;
  photos: GalleryPhoto[];
  totalPhotos: number;
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface GalleryTabProps {
  /** The expedition/trip ID (matches expedition_id in the backend) */
  expeditionId: string;
}

// ---------------------------------------------------------------------------
// GalleryImage — single photo tile with broken-image fallback
// ---------------------------------------------------------------------------

function GalleryImage({ photo }: { photo: GalleryPhoto }) {
  const [broken, setBroken] = useState(false);

  if (broken) {
    return (
      <div
        className="relative overflow-hidden rounded-2xl bg-gray-100 aspect-video flex flex-col items-center justify-center gap-1"
        data-testid={`gallery-photo-broken-${photo.id}`}
        aria-label={photo.caption ?? "Gallery photo (unavailable)"}
      >
        <ImageOff
          size={28}
          strokeWidth={1}
          className="text-gray-300"
          aria-hidden="true"
        />
        {photo.caption && (
          <p className="text-xs text-gray-400 px-2 text-center line-clamp-1">
            {photo.caption}
          </p>
        )}
      </div>
    );
  }

  return (
    <div
      className="relative overflow-hidden rounded-2xl bg-gray-100 aspect-video group"
      data-testid={`gallery-photo-${photo.id}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={photo.imageUrl}
        alt={photo.caption ?? "Gallery photo"}
        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        onError={() => setBroken(true)}
      />
      {photo.caption && (
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-3 py-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          <p className="text-xs text-white line-clamp-2">{photo.caption}</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// GalleryTab
// ---------------------------------------------------------------------------

export default function GalleryTab({ expeditionId }: GalleryTabProps) {
  const { data, isLoading, error } = useSWR<GalleryResponse>(
    expeditionKeys.gallery(expeditionId),
    swrFetcher,
    { revalidateOnFocus: false },
  );

  // ── Loading ──────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <motion.div
        className="py-6 grid grid-cols-1 sm:grid-cols-2 gap-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.25 }}
        data-testid="gallery-loading"
      >
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="rounded-2xl bg-gray-100 aspect-video animate-pulse" />
        ))}
      </motion.div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <motion.div
        className="py-12 text-center space-y-2 bg-white border border-red-100 rounded-3xl p-8 shadow-2xs"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        data-testid="gallery-error"
      >
        <AlertTriangle
          size={36}
          strokeWidth={1}
          className="text-red-300 mx-auto"
          aria-hidden="true"
        />
        <p className="text-sm font-semibold text-ink">Failed to load gallery.</p>
        <p className="text-xs text-muted-slate max-w-xs mx-auto">
          Unable to fetch photos. Please try again later.
        </p>
      </motion.div>
    );
  }

  const photos: GalleryPhoto[] = data?.photos ?? [];

  // ── Empty ────────────────────────────────────────────────────────────────
  if (photos.length === 0) {
    return (
      <motion.div
        className="py-12 text-center space-y-2 bg-white border border-gray-100 rounded-3xl p-8 shadow-2xs"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        data-testid="gallery-empty"
      >
        <ImageOff
          size={36}
          strokeWidth={1}
          className="text-gray-300 mx-auto"
          aria-hidden="true"
        />
        <p className="text-sm font-semibold text-ink">No photos yet.</p>
        <p className="text-xs text-muted-slate max-w-xs mx-auto">
          Photos shared by expedition members will appear here.
        </p>
      </motion.div>
    );
  }

  // ── Gallery ──────────────────────────────────────────────────────────────
  return (
    <motion.div
      className="py-6 grid grid-cols-1 sm:grid-cols-2 gap-4"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      data-testid="gallery-grid"
    >
      {photos.map((photo) => (
        <GalleryImage key={photo.id} photo={photo} />
      ))}
    </motion.div>
  );
}
