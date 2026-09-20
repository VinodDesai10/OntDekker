export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Heading shown in the modal header */
  title: string;
  children: React.ReactNode;
  /**
   * Maximum width of the modal card.
   * Defaults to "md" (max-w-lg).
   */
  size?: "sm" | "md" | "lg" | "xl";
  /**
   * When true the modal cannot be closed by clicking the backdrop
   * and Escape is ignored.
   */
  persistent?: boolean;
  /** Additional Tailwind classes on the card */
  className?: string;
}
