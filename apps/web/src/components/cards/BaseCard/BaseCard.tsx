"use client";

/**
 * OntDekker BaseCard
 *
 * Reusable card surface that all content cards are built upon.
 *
 * Design system spec (04-design-system.md § Cards):
 *   Surface  : bg-white border border-gray-100 rounded-3xl p-6 shadow-xs
 *   Hover    : shadow-md scale-[1.002]  duration 200ms standard ease
 *   Click    : scale 0.99              duration 100ms instant ease (via motion)
 *
 * Usage:
 *   <BaseCard onClick={...} interactive>
 *     …content…
 *   </BaseCard>
 */

import React from "react";
import { motion } from "motion/react";
import type { BaseCardProps } from "./BaseCard.types";

export default function BaseCard({
  children,
  onClick,
  className = "",
  interactive,
  ariaLabel,
}: BaseCardProps) {
  const isInteractive = interactive ?? Boolean(onClick);

  const base = [
    "bg-white border border-gray-100 rounded-3xl p-6",
    "shadow-xs",
    "transition-shadow duration-[var(--duration-responsive)] ease-[var(--ease-standard)]",
    isInteractive
      ? "cursor-pointer hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
      : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  if (!isInteractive) {
    return <div className={base}>{children}</div>;
  }

  return (
    <motion.div
      className={base}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={ariaLabel}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
      whileHover={{ scale: 1.002 }}
      whileTap={{ scale: 0.99 }}
      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
    >
      {children}
    </motion.div>
  );
}
