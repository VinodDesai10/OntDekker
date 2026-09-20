"use client";

/**
 * OntDekker Badge
 *
 * Compact label used to display status, metadata, and classification.
 *
 * Base variants (semantic):
 *   default  → gray    — general labels, tags
 *   success  → emerald — completed, verified, active states
 *   warning  → amber   — alerts, warnings, pending states
 *   info     → blue    — informational labels, coordinates
 *   error    → red     — errors, rejected, removed states
 *
 * Specialised exports:
 *   VerificationBadge — used on guide cards / profiles; always success/emerald
 *   WeightBadge       — packing classification; teal/emerald/amber/rose per spec
 *
 * Accessibility:
 *   - Renders as a <span> — inline and screen-reader-safe
 *   - Does not convey meaning through color alone (text label always present)
 */

import React from "react";
import { ShieldCheck } from "lucide-react";
import type {
  BadgeProps,
  BadgeSize,
  VerificationBadgeProps,
  WeightBadgeProps,
} from "./Badge.types";
import type { PackWeightClassification } from "@/types";

// ---------------------------------------------------------------------------
// Style maps
// ---------------------------------------------------------------------------

const variantClasses: Record<string, string> = {
  default: "bg-gray-100 text-gray-700 border border-gray-200",
  success: "bg-emerald-50 text-emerald-700 border border-emerald-100",
  warning: "bg-amber-50 text-amber-700 border border-amber-100",
  info:    "bg-blue-50 text-blue-700 border border-blue-100",
  error:   "bg-red-50 text-red-700 border border-red-100",
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: "px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded-full",
  md: "px-2.5 py-1 text-xs font-medium rounded-full",
};

// Weight classification colors per design system spec
const weightClasses: Record<PackWeightClassification, string> = {
  ULTRALIGHT: "bg-teal-50 text-teal-700 border border-teal-100",
  LIGHTWEIGHT: "bg-emerald-50 text-emerald-700 border border-emerald-100",
  STANDARD:   "bg-amber-50 text-amber-700 border border-amber-100",
  HEAVY:      "bg-rose-50 text-rose-700 border border-rose-100",
};

const weightLabels: Record<PackWeightClassification, string> = {
  ULTRALIGHT: "Ultralight",
  LIGHTWEIGHT: "Lightweight",
  STANDARD:   "Standard",
  HEAVY:      "Heavy",
};

// ---------------------------------------------------------------------------
// Base Badge
// ---------------------------------------------------------------------------

export default function Badge({
  children,
  variant = "default",
  size = "sm",
  className = "",
}: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 whitespace-nowrap",
        variantClasses[variant],
        sizeClasses[size],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Verification Badge
// ---------------------------------------------------------------------------

export function VerificationBadge({
  label = "Verified",
  size = "sm",
  className = "",
}: VerificationBadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 whitespace-nowrap",
        "bg-emerald-50 text-emerald-700 border border-emerald-100",
        sizeClasses[size],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <ShieldCheck
        className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"}
        aria-hidden="true"
        strokeWidth={2}
      />
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Weight Classification Badge
// ---------------------------------------------------------------------------

export function WeightBadge({
  classification,
  weightGrams,
  size = "sm",
  className = "",
}: WeightBadgeProps) {
  const label = weightLabels[classification];

  const formattedWeight =
    weightGrams !== undefined
      ? weightGrams >= 1000
        ? `${(weightGrams / 1000).toFixed(1)} kg`
        : `${weightGrams} g`
      : null;

  return (
    <span
      className={[
        "inline-flex items-center gap-1 whitespace-nowrap",
        weightClasses[classification],
        sizeClasses[size],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {label}
      {formattedWeight && (
        <span className="opacity-75 font-mono">{formattedWeight}</span>
      )}
    </span>
  );
}
