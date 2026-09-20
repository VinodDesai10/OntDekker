import type { CommunitySummary } from "@/types";

export interface CommunityCardProps {
  community: CommunitySummary;
  onClick: () => void;
  /** Stagger index for view-entry animation */
  index?: number;
}
