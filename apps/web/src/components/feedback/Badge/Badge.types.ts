import type React from "react";
import type { PackWeightClassification } from "@/types";

export type BadgeVariant = "default" | "success" | "warning" | "info" | "error";
export type BadgeSize = "sm" | "md";

export interface BadgeProps {
  children: React.ReactNode;
  /** Semantic color variant — defaults to "default" */
  variant?: BadgeVariant;
  /** Size — defaults to "sm" */
  size?: BadgeSize;
  /** Additional Tailwind classes */
  className?: string;
}

/** Props for the specialised Verification badge */
export interface VerificationBadgeProps {
  /** Label text — defaults to "Verified" */
  label?: string;
  size?: BadgeSize;
  className?: string;
}

/** Props for the pack weight classification badge */
export interface WeightBadgeProps {
  classification: PackWeightClassification;
  /** Total weight in grams (displayed alongside the label) */
  weightGrams?: number;
  size?: BadgeSize;
  className?: string;
}
