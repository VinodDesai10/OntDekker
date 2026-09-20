"use client";

/**
 * OntDekker Toast System
 *
 * Three exports:
 *   ToastProvider   — Context provider; wraps the app shell
 *   ToastContainer  — Renders active toasts in a portal at bottom-right
 *   Toast           — Individual toast item (internal, used by Container)
 *
 * Motion spec (06-motion-design.md § Notification Animations — Toast):
 *   Entry : Y 24px → 0, opacity 0 → 1,  duration 250ms, ease decelerate
 *   Exit  : opacity 1 → 0, Y 0 → 8px,   duration 200ms, ease accelerate
 *   Auto-close : 4 000 ms
 *
 * Types: success (moss-green) | info (ozone-blue) | error (red)
 *
 * Accessibility:
 *   - aria-live="polite" on the container (aria-live="assertive" for error)
 *   - role="status" on each toast
 *   - Dismiss button with aria-label
 *   - Toasts do not steal keyboard focus
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "motion/react";
import { CheckCircle, Info, AlertCircle, X } from "lucide-react";
import type { ToastContextValue, ToastItem, ToastProps, ToastType } from "./Toast.types";

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const ToastContext = createContext<ToastContextValue | null>(null);

// ---------------------------------------------------------------------------
// Single Toast item
// ---------------------------------------------------------------------------

type LucideIconType = React.ComponentType<{ size?: number | string; strokeWidth?: number | string; className?: string }>;

const TYPE_STYLES: Record<ToastType, { bg: string; border: string; icon: LucideIconType }> = {
  success: {
    bg: "bg-white",
    border: "border-emerald-200",
    icon: CheckCircle,
  },
  info: {
    bg: "bg-white",
    border: "border-blue-200",
    icon: Info,
  },
  error: {
    bg: "bg-white",
    border: "border-red-200",
    icon: AlertCircle,
  },
};

const ICON_COLOR: Record<ToastType, string> = {
  success: "text-moss-green",
  info: "text-ozone-blue",
  error: "text-red-600",
};

function Toast({ toast, onDismiss }: ToastProps) {
  const { id, message, type } = toast;
  const styles = TYPE_STYLES[type];
  const Icon = styles.icon;

  return (
    <motion.div
      layout
      role="status"
      aria-live={type === "error" ? "assertive" : "polite"}
      aria-atomic="true"
      className={[
        "flex items-start gap-3",
        "w-full max-w-sm px-4 py-3",
        "rounded-2xl border shadow-sm",
        styles.bg,
        styles.border,
      ].join(" ")}
      initial={{ opacity: 0, y: 24, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1, transition: { duration: 0.25, ease: [0, 0, 0.2, 1] } }}
      exit={{ opacity: 0, y: 8, scale: 0.97, transition: { duration: 0.2, ease: [0.4, 0, 1, 1] } }}
      transition={{ layout: { duration: 0.2 } }}
    >
      {/* Type icon */}
      <Icon
        size={18}
        strokeWidth={2}
        className={`flex-shrink-0 mt-0.5 ${ICON_COLOR[type]}`}
      />

      {/* Message */}
      <p className="flex-1 text-sm text-ink leading-snug">{message}</p>

      {/* Dismiss button */}
      <button
        type="button"
        aria-label="Dismiss notification"
        onClick={() => onDismiss(id)}
        className="
          flex-shrink-0 flex items-center justify-center
          w-5 h-5 rounded-lg -mr-1 -mt-0.5
          text-muted-slate hover:text-ink hover:bg-gray-100
          transition-colors duration-[var(--duration-responsive)]
        "
      >
        <X size={13} strokeWidth={2} aria-hidden="true" />
      </button>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// ToastContainer — renders the stack into a portal
// ---------------------------------------------------------------------------

function ToastContainer({ toasts, onDismiss }: { toasts: ToastItem[]; onDismiss: (id: string) => void }) {
  if (typeof window === "undefined" || !toasts.length) return null;

  return createPortal(
    <div
      aria-label="Notifications"
      className="
        fixed bottom-5 right-5 z-[60]
        flex flex-col gap-2 items-end
        pointer-events-none
      "
    >
      <AnimatePresence mode="popLayout" initial={false}>
        {toasts.map((t) => (
          <div key={t.id} className="pointer-events-auto w-full">
            <Toast toast={t} onDismiss={onDismiss} />
          </div>
        ))}
      </AnimatePresence>
    </div>,
    document.body,
  );
}

// ---------------------------------------------------------------------------
// ToastProvider
// ---------------------------------------------------------------------------

let _idCounter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  // Store timeout handles so we can clear them on manual dismiss
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const handle = timersRef.current.get(id);
    if (handle) {
      clearTimeout(handle);
      timersRef.current.delete(id);
    }
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = "info"): string => {
      const id = `toast-${++_idCounter}`;
      setToasts((prev) => [...prev, { id, message, type }]);
      // Auto-dismiss after 4 000 ms per motion spec
      const handle = setTimeout(() => dismissToast(id), 4000);
      timersRef.current.set(id, handle);
      return id;
    },
    [dismissToast],
  );

  return (
    <ToastContext.Provider value={{ showToast, dismissToast }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Internal hook (use the public useToast from hooks/useToast.ts instead)
// ---------------------------------------------------------------------------

export function useToastContext(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToastContext must be used inside <ToastProvider>");
  return ctx;
}
