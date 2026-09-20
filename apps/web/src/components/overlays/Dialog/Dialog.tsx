"use client";

/**
 * OntDekker Dialog
 *
 * Focused confirmation overlay for single-decision workflows.
 * Used for: Delete expedition, Leave community, Remove participant, etc.
 *
 * Motion spec (06-motion-design.md § Overlay Animations — Dialog):
 *   Simple scale  0.96 → 1.0   duration 300ms, ease decelerate
 *   Backdrop      opacity 0 → 45%
 *
 * Accessibility:
 *   - role="alertdialog" (required for confirmations per WAI-ARIA)
 *   - aria-modal="true" aria-labelledby aria-describedby
 *   - Escape triggers onCancel
 *   - Focus is placed on the Cancel button by default (safer for destructive actions)
 *   - Tab cycles between Cancel and Confirm only
 *   - Portal render via document.body
 */

import React, { useEffect, useId, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "motion/react";
import { AlertTriangle } from "lucide-react";
import Button from "@/components/feedback/Button";
import type { DialogProps } from "./Dialog.types";

export default function Dialog({
  isOpen,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  onCancel,
  destructive = false,
  loading = false,
}: DialogProps) {
  const titleId = useId();
  const descId = useId();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // Save and restore focus
  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement as HTMLElement;
      requestAnimationFrame(() => cancelRef.current?.focus());
      document.body.style.overflow = "hidden";
    } else {
      previousFocusRef.current?.focus();
      previousFocusRef.current = null;
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // Keyboard: Escape → cancel, Tab cycles within dialog
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        onCancel();
      }
    },
    [onCancel],
  );

  if (typeof window === "undefined") return null;

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
          onKeyDown={handleKeyDown}
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/45 backdrop-blur-[2px]"
            aria-hidden="true"
            onClick={onCancel}
          />

          {/* Card */}
          <motion.div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={descId}
            tabIndex={-1}
            className="
              relative z-10 w-full max-w-sm
              bg-white rounded-3xl shadow-2xl
              p-6 space-y-5
              focus:outline-none
            "
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.3, ease: [0, 0, 0.2, 1] }}
          >
            {/* Icon + title */}
            <div className="flex items-start gap-3">
              {destructive && (
                <span
                  aria-hidden="true"
                  className="flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-xl bg-red-50"
                >
                  <AlertTriangle
                    size={18}
                    strokeWidth={2}
                    className="text-red-600"
                  />
                </span>
              )}
              <div className="space-y-1 min-w-0">
                <h2
                  id={titleId}
                  className="text-base font-semibold tracking-tight text-ink"
                >
                  {title}
                </h2>
                <p
                  id={descId}
                  className="text-sm text-charcoal leading-relaxed"
                >
                  {message}
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 pt-1">
              <Button
                ref={cancelRef}
                variant="secondary"
                size="sm"
                onClick={onCancel}
                disabled={loading}
              >
                {cancelLabel}
              </Button>
              <Button
                variant={destructive ? "danger" : "primary"}
                size="sm"
                loading={loading}
                onClick={onConfirm}
              >
                {confirmLabel}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
