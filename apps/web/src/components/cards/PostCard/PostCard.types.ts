import type { PostSummary } from "@/types";

export interface PostCardProps {
  post: PostSummary;
  /** Staggered entrance animation index */
  index?: number;
  onClick?: () => void;
  onLikeToggle?: (e: React.MouseEvent) => void;
  onBookmarkToggle?: (e: React.MouseEvent) => void;
}
