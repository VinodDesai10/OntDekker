"use client";

/**
 * OntDekker Drawer
 *
 * Mobile-first bottom sheet overlay. Used for:
 *   - Notifications panel
 *   - Context menus / filter sheets
 *   - Any ancillary content that doesn't warrant a full Modal
 *
 * Motion spec (06-motion-design.md § Overlay Animations — Drawer):
 *   Duration  : 350ms
 *   Panel     : Y  100% → 0    ease decelerate
 *   Backdrop  : opacity 0 → 45%  simultaneously
 *
 * On desktop the drawer still slides from the bottom but caps its height
 * at 80vh and centres horizontally as a max-w-lg panel for consistency.
 *
 * Accessibility:
 *   - role="dialog" aria-modal="true" aria-labelledby
 *   - Escape closes
 *   - Focus moves to the panel on open; restored on close
 *   - Tab trapped inside the panel
 *   - Portal rendered to document.body
 */

import React, { useEffect, useId, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "motion/react";
import { X } from "lucide-react";
import type { DrawerProps } from "./Drawer.types";

const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),' +
  'textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

export default function Drawer({
  isOpen,
  onClose,
  title,
  children,
  className = "",
}: DrawerProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // Save / restore focus + body scroll lock
  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement as HTMLElement;
      document.body.style.overflow = "hidden";
      requestAnimationFrame(() => {
        const first = panelRef.current?.querySelector<HTMLElement>(FOCUSABLE);
        first?.focus();
      });
    } else {
      previousFocusRef.current?.focus();
      previousFocusRef.current = null;
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // Escape + focus trap
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "Tab") {
        const focusables = Array.from(
          panelRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [],
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
    [onClose],
  );

  if (typeof window === "undefined") return null;

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-end justify-center sm:items-end"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/45 backdrop-blur-[2px]"
            aria-hidden="true"
            onClick={onClose}
          />

          {/* Panel — slides up from bottom */}
          <motion.div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            onKeyDown={handleKeyDown}
            className={[
              "relative z-10 w-full sm:max-w-lg",
              "bg-white rounded-t-3xl sm:rounded-3xl shadow-2xl",
              "flex flex-col max-h-[80vh]",
              "focus:outline-none",
              className,
            ]
              .filter(Boolean)
              .join(" ")}
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ duration: 0.35, ease: [0, 0, 0.2, 1] }}
          >
            {/* Drag handle (visual affordance) */}
            <div
              className="flex justify-center pt-3 pb-1 shrink-0"
              aria-hidden="true"
            >
              <span className="w-10 h-1 rounded-full bg-gray-200" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-5 pb-3 pt-1 shrink-0">
              <h2
                id={titleId}
                className="text-base font-semibold tracking-tight text-ink"
              >
                {title}
              </h2>
              <button
                type="button"
                aria-label="Close drawer"
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
            </div>

            {/* Scrollable content */}
            <div className="overflow-y-auto flex-1 px-5 pb-6">
              {children}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
