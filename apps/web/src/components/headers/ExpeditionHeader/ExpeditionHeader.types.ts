import type { Trip } from "@/types/trip";

export interface ExpeditionHeaderProps {
  trip: Trip;
  onBack: () => void;
}
