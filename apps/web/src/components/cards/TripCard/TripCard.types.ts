import type { TripSummary } from "@/types/trip";

export interface TripCardProps {
  trip: TripSummary;
  onClick: () => void;
  /** Stagger index for view-entry animation */
  index?: number;
}
