"use client";

/**
 * OntDekker CommunityCard
 *
 * Community discovery card used in the Communities directory.
 *
 * Information displayed:
 *   - Community name
 *   - Description (2-line clamp)
 *   - Member count (mono)
 *   - Visibility badge (PUBLIC / PRIVATE)
 *   - Location (if available, mono uppercase)
 *   - Logo / profile photo (if available)
 *
 * Action:
 *   View — onClick navigates to /communities/[id]
 */

import React from "react";
import { motion } from "motion/react";
import { Users, MapPin, Lock, Globe } from "lucide-react";
import BaseCard from "@/components/cards/BaseCard";
import Badge from "@/components/feedback/Badge";
import Button from "@/components/feedback/Button";
import type { CommunityCardProps } from "./CommunityCard.types";

export default function CommunityCard({
  community,
  onClick,
  index = 0,
}: CommunityCardProps) {
  const isPrivate = community.visibility === "PRIVATE";

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0, 0, 0.2, 1], delay: index * 0.05 }}
    >
      <BaseCard
        onClick={onClick}
        ariaLabel={`View ${community.name} community`}
      >
        <div className="space-y-4">
          {/* Top row: monogram + name + visibility badge */}
          <div className="flex items-start gap-3">
            {/* Name monogram — replaces the removed logo avatar */}
            <div
              className="w-10 h-10 rounded-xl bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center flex-shrink-0 border border-gray-100"
              aria-hidden="true"
            >
              <span className="text-sm font-bold text-gray-500 leading-none">
                {community.name.slice(0, 1).toUpperCase()}
              </span>
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold text-ink truncate">
                  {community.name}
                </p>
                <Badge
                  variant={isPrivate ? "warning" : "success"}
                  size="sm"
                  className="flex-shrink-0"
                >
                  {isPrivate ? (
                    <Lock size={9} strokeWidth={2.5} aria-hidden="true" />
                  ) : (
                    <Globe size={9} strokeWidth={2.5} aria-hidden="true" />
                  )}
                  {isPrivate ? "Private" : "Public"}
                </Badge>
              </div>
            </div>
          </div>

          {/* Description */}
          {community.description && (
            <p className="text-xs text-charcoal leading-relaxed line-clamp-2">
              {community.description}
            </p>
          )}

          {/* Metadata row: member count + location */}
          <div className="flex flex-col gap-1 text-[10px] font-mono uppercase tracking-wider text-muted-slate">
            <span className="flex items-center gap-1.5">
              <Users size={10} strokeWidth={2} aria-hidden="true" />
              {community.memberCount.toLocaleString()}{" "}
              {community.memberCount === 1 ? "member" : "members"}
            </span>
            {community.location && (
              <span className="flex items-center gap-1.5">
                <MapPin size={10} strokeWidth={2} aria-hidden="true" />
                {community.location}
              </span>
            )}
          </div>

          {/* Divider */}
          <div className="border-t border-gray-100" aria-hidden="true" />

          {/* Action */}
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
              View Community
            </Button>
          </div>
        </div>
      </BaseCard>
    </motion.div>
  );
}
