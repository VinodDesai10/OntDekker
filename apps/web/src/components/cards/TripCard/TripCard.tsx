"use client";

/**
 * OntDekker TripCard
 *
 * Displays a trip summary card in the Trips grid.
 * Data: TripSummary (from /api/v1/trips or /api/v1/users/me/trips)
 *
 * Displays:
 *   - Cover image
 *   - Status badge
 *   - Destination + title
 *   - Dates
 *   - Budget
 *   - Participants count / max
 *   - Host name
 */

import React from "react";
import { motion } from "motion/react";
import { CalendarDays, Wallet, Users, MapPin } from "lucide-react";
import Badge from "@/components/feedback/Badge";
import type { BadgeVariant } from "@/components/feedback/Badge";
import BaseCard from "@/components/cards/BaseCard";
import type { TripCardProps } from "./TripCard.types";
import type { TripStatus } from "@/types/trip";

const STATUS_CONFIG: Record<TripStatus, { variant: BadgeVariant; label: string }> = {
  DRAFT:      { variant: "default",  label: "Draft" },
  PUBLISHED:  { variant: "info",     label: "Open" },
  ACTIVE:     { variant: "success",  label: "Active" },
  COMPLETED:  { variant: "default",  label: "Completed" },
  CANCELLED:  { variant: "error",    label: "Cancelled" },
  ARCHIVED:   { variant: "default",  label: "Archived" },
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatBudget(budget: number | null): string {
  if (budget === null || budget === undefined) return "Budget TBD";
  return `$${Number(budget).toLocaleString()}`;
}

export default function TripCard({ trip, onClick, index = 0 }: TripCardProps) {
  const statusCfg = STATUS_CONFIG[trip.status] ?? STATUS_CONFIG.DRAFT;

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0, 0, 0.2, 1], delay: index * 0.05 }}
    >
      <BaseCard
        onClick={onClick}
        ariaLabel={`Open trip: ${trip.title}`}
        className="p-0 overflow-hidden space-y-0"
      >
        {/* Cover image */}
        <div className="h-36 w-full overflow-hidden bg-gray-100 relative">
          {trip.coverImageUrl ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={trip.coverImageUrl}
              alt={trip.destination}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gray-100">
              <MapPin size={24} strokeWidth={1.5} className="text-gray-300" aria-hidden="true" />
            </div>
          )}
          <div className="absolute top-3 right-3">
            <Badge variant={statusCfg.variant} size="sm">
              {statusCfg.label}
            </Badge>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3">
          {/* Destination + title */}
          <div>
            <p className="text-[10px] font-mono uppercase tracking-wider text-muted-slate">
              {trip.destination}
            </p>
            <h3 className="text-sm font-semibold tracking-tight text-ink leading-snug mt-0.5">
              {trip.title}
            </h3>
          </div>

          {/* Metadata grid */}
          <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-muted-slate">
            {/* Dates */}
            <span className="flex items-center gap-1">
              <CalendarDays size={10} strokeWidth={2} aria-hidden="true" />
              <span>{trip.startDate ? formatDate(trip.startDate) : "Date TBD"}</span>
            </span>

            {/* Budget */}
            <span className="flex items-center gap-1">
              <Wallet size={10} strokeWidth={2} aria-hidden="true" />
              <span>{formatBudget(trip.budget)}</span>
            </span>

            {/* Participants */}
            <span className="flex items-center gap-1 col-span-2">
              <Users size={10} strokeWidth={2} aria-hidden="true" />
              <span>
                {trip.currentParticipantsCount} / {trip.maxParticipants} participants
              </span>
            </span>
          </div>

          {/* Host name */}
          {trip.hostName && (
            <p className="text-xs text-charcoal">
              <span className="text-muted-slate">hosted by </span>
              {trip.hostName}
            </p>
          )}
        </div>
      </BaseCard>
    </motion.div>
  );
}
