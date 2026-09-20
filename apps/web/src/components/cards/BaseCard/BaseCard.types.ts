export interface BaseCardProps {
  children: React.ReactNode;
  /** Click handler — makes the card interactive when provided */
  onClick?: () => void;
  /** Additional Tailwind classes */
  className?: string;
  /**
   * When true, applies hover scale + shadow micro-interaction.
   * Automatically true when onClick is provided.
   */
  interactive?: boolean;
  /** aria-label for the card when it is used as a clickable element */
  ariaLabel?: string;
}
