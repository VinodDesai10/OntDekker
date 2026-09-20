"use client";

/**
 * OntDekker GuideCard
 *
 * Guide discovery card used in the Guides directory.
 *
 * Information displayed:
 *   - Cover image (top strip)
 *   - Avatar (md)
 *   - Display name + VerificationBadge when VERIFIED
 *   - Star rating (mono) + review count
 *   - Price per day
 *   - Cities (first 2) + languages (first 2)
 *   - Specializations (chips)
 *   - Bio excerpt (2-line clamp)
 *
 * Actions:
 *   Bookmark — spring scale 1→1.2→1 (organic spring)
 *   View Profile — onClick navigates to guide portfolio
 */

import React from "react";
import { motion } from "motion/react";
import { Bookmark, Star, MapPin, Languages, DollarSign, Tag } from "lucide-react";
import Avatar from "@/components/feedback/Avatar";
import { VerificationBadge } from "@/components/feedback/Badge";
import Button from "@/components/feedback/Button";
import BaseCard from "@/components/cards/BaseCard";
import type { GuideCardProps } from "./GuideCard.types";

export default function GuideCard({
  guide,
  onBookmarkToggle,
  onClick,
  isBookmarked = false,
  index = 0,
}: GuideCardProps) {
  const isVerified = guide.verificationStatus === "VERIFIED";

  // First 2 location labels
  const cities = guide.locations
    .slice(0, 2)
    .map((l) => l.city ?? l.region ?? l.country)
    .filter(Boolean)
    .join(", ");

  // First 2 languages
  const langs = guide.languages.slice(0, 2).map((l) => l.language).join(", ");

  // First 3 specialization chips
  const specs = guide.specializations?.slice(0, 3) ?? [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0, 0, 0.2, 1], delay: index * 0.05 }}
    >
      <BaseCard onClick={onClick} ariaLabel={`View ${guide.displayName ?? "Guide"}'s profile`}>
        <div className="space-y-4">
          {/* Top row: avatar + name + bookmark */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <Avatar
                src={guide.profileImageUrl}
                alt={guide.displayName ?? "Guide"}
                size="md"
              />
              <div className="min-w-0">
                <p className="text-sm font-semibold text-ink truncate">
                  {guide.displayName ?? "Guide"}
                </p>
                {isVerified && (
                  <VerificationBadge size="sm" className="mt-0.5" />
                )}
              </div>
            </div>

            {/* Bookmark button */}
            <motion.button
              type="button"
              aria-label={isBookmarked ? "Remove bookmark" : "Bookmark guide"}
              aria-pressed={isBookmarked}
              onClick={onBookmarkToggle}
              className={[
                "flex-shrink-0 flex items-center justify-center",
                "w-8 h-8 rounded-xl border",
                "transition-colors duration-[var(--duration-responsive)]",
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
                isBookmarked
                  ? "bg-amber-50 border-amber-200 text-amber-600"
                  : "bg-white border-gray-100 text-muted-slate hover:text-ink hover:border-gray-200",
              ].join(" ")}
              whileTap={{ scale: 0.85 }}
              animate={isBookmarked ? { scale: [1, 1.2, 1] } : { scale: 1 }}
              transition={{ duration: 0.35, ease: [0.34, 1.56, 0.64, 1] }}
            >
              <Bookmark
                size={15}
                strokeWidth={2}
                fill={isBookmarked ? "currentColor" : "none"}
                aria-hidden="true"
              />
            </motion.button>
          </div>

          {/* Rating + price row */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {guide.rating !== null && (
              <>
                <Star
                  size={13}
                  strokeWidth={2}
                  fill="currentColor"
                  className="text-amber-400"
                  aria-hidden="true"
                />
                <span className="text-xs font-mono font-medium text-ink">
                  {guide.rating.toFixed(1)}
                </span>
                <span className="text-[10px] font-mono text-muted-slate">
                  ({guide.reviewCount})
                </span>
              </>
            )}
            {guide.yearsExperience !== null && (
              <span className="ml-auto text-[10px] font-mono uppercase tracking-wider text-muted-slate">
                {guide.yearsExperience} yrs exp
              </span>
            )}
            {guide.pricePerDay !== null && guide.pricePerDay !== undefined && (
              <span className="ml-auto flex items-center gap-0.5 text-[10px] font-mono font-semibold text-ink">
                <DollarSign size={9} strokeWidth={2} aria-hidden="true" />
                {guide.pricePerDay}/day
              </span>
            )}
          </div>

          {/* Location + languages metadata */}
          <div className="flex flex-col gap-1 text-[10px] font-mono uppercase tracking-wider text-muted-slate">
            {cities && (
              <span className="flex items-center gap-1.5">
                <MapPin size={10} strokeWidth={2} aria-hidden="true" />
                {cities}
              </span>
            )}
            {langs && (
              <span className="flex items-center gap-1.5">
                <Languages size={10} strokeWidth={2} aria-hidden="true" />
                {langs}
              </span>
            )}
          </div>

          {/* Specialization chips */}
          {specs.length > 0 && (
            <div className="flex flex-wrap gap-1.5" aria-label="Specializations">
              {specs.map((s) => (
                <span
                  key={s.id}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-100 text-[10px] font-medium text-charcoal"
                >
                  <Tag size={8} strokeWidth={2} aria-hidden="true" />
                  {s.category}
                </span>
              ))}
            </div>
          )}

          {/* Bio excerpt */}
          {guide.bio && (
            <p className="text-xs text-charcoal leading-relaxed line-clamp-2">
              {guide.bio}
            </p>
          )}

          {/* Divider */}
          <div className="border-t border-gray-100" aria-hidden="true" />

          {/* Action buttons */}
          <div
            className="flex items-center gap-2"
            onClick={(e) => e.stopPropagation()}
          >
            <Button
              variant="primary"
              size="sm"
              onClick={onClick}
              className="flex-1"
            >
              View Profile
            </Button>
          </div>
        </div>
      </BaseCard>
    </motion.div>
  );
}
