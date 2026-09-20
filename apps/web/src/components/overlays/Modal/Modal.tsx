"use client";

/**
 * OntDekker Modal
 *
 * General-purpose overlay container used for create/edit/invite workflows.
 *
 * Motion spec (06-motion-design.md § Overlay Animations):
 *   Backdrop : opacity  0 → 45%    duration 300ms, ease standard
 *   Card     : scale  0.95 → 1.0   duration 300ms, ease decelerate
 *              opacity   0 → 1
 *
 * Accessibility:
 *   - role="dialog" aria-modal="true" aria-labelledby
 *   - Focus trap: Tab / Shift+Tab cycle inside the modal only
 *   - Escape closes (unless persistent)
 *   - Restores focus to the trigger element on close
 *   - Rendered in a React Portal so it sits above all stacking contexts
 *
 * Usage:
 *   <Modal isOpen={open} onClose={() => setOpen(false)} title="Invite Guide">
 *     …content…
 *   </Modal>
 */

import React, {
  useCallback,
  useEffect,
  useId,
  useRef,
} from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "motion/react";
import { X } from "lucide-react";
import type { ModalProps } from "./Modal.types";

// ---------------------------------------------------------------------------
// Focusable selector used by the focus trap
// ---------------------------------------------------------------------------
const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),' +
  'textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

const sizeClasses: Record<string, string> = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Modal({
  isOpen,
  onClose,
  title,
  children,
  size = "md",
  persistent = false,
  className = "",
}: ModalProps) {
  const titleId = useId();
  const cardRef = useRef<HTMLDivElement>(null);
  // Remember the element that had focus before the modal opened
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // ── Save / restore focus ─────────────────────────────────────────────────
  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement as HTMLElement;
      // Move focus into the card on the next tick so the card is rendered
      requestAnimationFrame(() => {
        const firstFocusable = cardRef.current?.querySelector<HTMLElement>(FOCUSABLE);
        firstFocusable?.focus();
      });
    } else {
      previousFocusRef.current?.focus();
      previousFocusRef.current = null;
    }
  }, [isOpen]);

  // ── Keyboard handling (Escape + focus trap) ───────────────────────────────
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === "Escape" && !persistent) {
        onClose();
        return;
      }
      if (e.key === "Tab") {
        const focusables = Array.from(
          cardRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [],
        );
        if (!focusables.length) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    },
    [onClose, persistent],
  );

  // ── Prevent body scroll while open ───────────────────────────────────────
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // ── Render ────────────────────────────────────────────────────────────────
  if (typeof window === "undefined") return null;

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        // Full-screen backdrop
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
          aria-hidden="false"
        >
          {/* Backdrop — semi-transparent black per design system */}
          <div
            className="absolute inset-0 bg-black/45 backdrop-blur-[2px]"
            aria-hidden="true"
            onClick={persistent ? undefined : onClose}
          />

          {/* Modal card */}
          <motion.div
            ref={cardRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            onKeyDown={handleKeyDown}
            tabIndex={-1}
            className={[
              "relative z-10 w-full",
              sizeClasses[size],
              "bg-white rounded-3xl shadow-2xl",
              "flex flex-col max-h-[90vh]",
              "focus:outline-none",
              className,
            ]
              .filter(Boolean)
              .join(" ")}
            initial={{ opacity: 0, scale: 0.95, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 8 }}
            transition={{ duration: 0.3, ease: [0, 0, 0.2, 1] }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-gray-100 shrink-0">
              <h2
                id={titleId}
                className="text-base font-semibold tracking-tight text-ink"
              >
                {title}
              </h2>
              {!persistent && (
                <button
                  type="button"
                  aria-label="Close modal"
                  onClick={onClose}
                  className="
                    flex items-center justify-center
                    w-7 h-7 rounded-lg
                    text-muted-slate hover:text-ink hover:bg-gray-100
                    transition-colors duration-[var(--duration-responsive)]
                    focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink
                  "
                >
                  <X size={16} strokeWidth={2} aria-hidden="true" />
                </button>
              )}
            </div>

            {/* Scrollable content area */}
            <div className="overflow-y-auto flex-1 px-6 py-5">
              {children}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
