export type ToastType = "success" | "info" | "error";

export interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
}

/** Props for a single rendered toast */
export interface ToastProps {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}

/** The value provided by ToastContext */
export interface ToastContextValue {
  /** Show a toast — returns the generated ID */
  showToast: (message: string, type?: ToastType) => string;
  /** Programmatically dismiss a toast by ID */
  dismissToast: (id: string) => void;
}
