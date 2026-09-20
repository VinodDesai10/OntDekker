import type { GuideProfileSummary } from "@/types";

export interface GuideCardProps {
  guide: GuideProfileSummary;
  onBookmarkToggle: (e: React.MouseEvent) => void;
  onMessage?: (e: React.MouseEvent) => void;
  onClick: () => void;
  /** Whether this guide is currently bookmarked by the user */
  isBookmarked?: boolean;
  /** Stagger index for view-entry animation */
  index?: number;
}
