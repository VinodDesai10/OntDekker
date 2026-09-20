export interface SearchProps {
  placeholder?: string;
  value: string;
  onChange: (query: string) => void;
  onClear?: () => void;
  /** Shows a spinner inside the input */
  loading?: boolean;
  /** Red border + helper text */
  error?: string;
  /** Additional Tailwind classes on the wrapper */
  className?: string;
  /** aria-label for the input */
  ariaLabel?: string;
}
