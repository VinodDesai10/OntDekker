"use client";

/**
 * OntDekker Avatar
 *
 * Displays a circular user image with an optional presence indicator.
 * Falls back to an initial-letter placeholder when no image is provided.
 *
 * Sizes (from design system):
 *   xs  → w-6  h-6    (24 px)  — notification badges, comment threads
 *   sm  → w-8  h-8    (32 px)  — inline mentions, compact lists
 *   md  → w-12 h-12   (48 px)  — cards, guide listings
 *   lg  → w-16 h-16   (64 px)  — sidebar profile, community headers
 *   xl  → w-32 h-32  (128 px)  — profile page hero
 *
 * Status indicator:
 *   online  → moss-green dot
 *   offline → muted-slate dot
 *   none    → no indicator
 *
 * Accessibility:
 *   - <img> with descriptive alt text
 *   - Status dot is aria-hidden; screen-reader label is on the wrapper
 */

import React from "react";
import type { AvatarProps } from "./Avatar.types";

// ---------------------------------------------------------------------------
// Style maps
// ---------------------------------------------------------------------------

const sizeClasses: Record<string, string> = {
  xs: "w-6 h-6 text-[9px]",
  sm: "w-8 h-8 text-[11px]",
  md: "w-12 h-12 text-base",
  lg: "w-16 h-16 text-xl",
  xl: "w-32 h-32 text-4xl",
};

/** Dot size + position relative to the avatar ring */
const statusDotClasses: Record<string, string> = {
  xs: "w-1.5 h-1.5 bottom-0 right-0",
  sm: "w-2 h-2 bottom-0 right-0",
  md: "w-2.5 h-2.5 bottom-0.5 right-0.5",
  lg: "w-3 h-3 bottom-0.5 right-0.5",
  xl: "w-4 h-4 bottom-1 right-1",
};

const statusColorClasses: Record<string, string> = {
  online: "bg-moss-green",
  offline: "bg-muted-slate",
  none: "",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Derive up to 2 initials from a display name or alt string */
function getInitials(alt: string): string {
  const parts = alt.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return alt.charAt(0).toUpperCase();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Avatar({
  src,
  alt,
  size = "md",
  status = "none",
  className = "",
}: AvatarProps) {
  const hasSrc = Boolean(src);
  const hasStatus = status !== "none";

  return (
    <span
      className={[
        "relative inline-flex flex-shrink-0",
        sizeClasses[size],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      aria-label={hasStatus ? `${alt} — ${status}` : undefined}
    >
      {/* Image or initials fallback */}
      {hasSrc ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={src!}
          alt={alt}
          className="w-full h-full rounded-full object-cover bg-gray-100"
          loading="lazy"
        />
      ) : (
        <span
          aria-hidden="true"
          className={[
            "w-full h-full rounded-full",
            "flex items-center justify-center",
            "bg-gray-200 text-charcoal font-semibold select-none",
          ].join(" ")}
        >
          {getInitials(alt)}
        </span>
      )}

      {/* Status indicator dot */}
      {hasStatus && (
        <span
          aria-hidden="true"
          className={[
            "absolute rounded-full ring-2 ring-white",
            statusDotClasses[size],
            statusColorClasses[status],
          ].join(" ")}
        />
      )}
    </span>
  );
}
