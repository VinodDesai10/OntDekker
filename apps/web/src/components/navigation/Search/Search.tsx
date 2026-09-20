"use client";

/**
 * OntDekker Search
 *
 * Global filtering input component.
 *
 * Behaviour per motion spec:
 *   - On focus: container expands by 24px (motion/react width animation)
 *   - Search icon translates slightly right on focus (spring easing)
 *   - Clear (×) button appears with a fade+scale when value is non-empty
 *   - Loading spinner replaces the icon while loading
 *
 * States:
 *   default  → gray-50 bg, gray-200 border
 *   focused  → white bg, ink border, shadow-sm
 *   typing   → clear button visible
 *   loading  → spinner inside input
 *   error    → red border + helper text below
 *
 * Accessibility:
 *   - <input type="search"> with role="searchbox" implicit
 *   - aria-label on the input
 *   - Clear button has descriptive aria-label
 *   - Error message linked via aria-describedby
 */

import React, { useId, useState, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Search as SearchIcon, X, Loader2 } from "lucide-react";
import type { SearchProps } from "./Search.types";

export default function Search({
  placeholder = "Search…",
  value,
  onChange,
  onClear,
  loading = false,
  error,
  className = "",
  ariaLabel = "Search",
}: SearchProps) {
  const [isFocused, setIsFocused] = useState(false);
  const errorId = useId();
  const hasValue = value.length > 0;

  const handleClear = useCallback(() => {
    onChange("");
    onClear?.();
  }, [onChange, onClear]);

  return (
    <div className={["flex flex-col gap-1", className].filter(Boolean).join(" ")}>
      {/* ── Input row ─────────────────────────────────────────────────── */}
      <motion.div
        className={[
          "relative flex items-center",
          "rounded-xl border",
          "transition-shadow duration-[var(--duration-responsive)]",
          error
            ? "border-red-400 bg-red-50"
            : isFocused
            ? "border-ink bg-white shadow-sm"
            : "border-gray-200 bg-gray-50",
        ]
          .filter(Boolean)
          .join(" ")}
        // Expand +24px on focus per motion spec
        animate={{ width: isFocused ? "calc(100% + 0px)" : "100%" }}
        transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
      >
        {/* Search icon / spinner */}
        <motion.span
          className="absolute left-3 flex items-center justify-center pointer-events-none"
          animate={{ x: isFocused ? 2 : 0 }}
          transition={{ duration: 0.2, ease: [0.34, 1.56, 0.64, 1] }}
          aria-hidden="true"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 text-charcoal animate-spin" />
          ) : (
            <SearchIcon
              className={[
                "w-4 h-4 transition-colors duration-[var(--duration-responsive)]",
                isFocused ? "text-ink" : "text-muted-slate",
              ].join(" ")}
            />
          )}
        </motion.span>

        {/* Input */}
        <input
          type="search"
          value={value}
          placeholder={placeholder}
          aria-label={ariaLabel}
          aria-describedby={error ? errorId : undefined}
          aria-invalid={Boolean(error)}
          autoComplete="off"
          spellCheck={false}
          className={[
            "w-full pl-9 pr-8 py-2",
            "bg-transparent text-sm text-ink",
            "placeholder:text-muted-slate",
            "focus:outline-none",
            // Remove native search cancel button (webkit)
            "[&::-webkit-search-cancel-button]:hidden",
          ].join(" ")}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
        />

        {/* Clear button — visible only when there is a value */}
        <AnimatePresence>
          {hasValue && !loading && (
            <motion.button
              type="button"
              aria-label="Clear search"
              onClick={handleClear}
              className={[
                "absolute right-2",
                "flex items-center justify-center",
                "w-5 h-5 rounded-full",
                "text-muted-slate hover:text-ink hover:bg-gray-100",
                "transition-colors duration-[var(--duration-responsive)]",
              ].join(" ")}
              initial={{ opacity: 0, scale: 0.7 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.7 }}
              transition={{ duration: 0.15, ease: [0.4, 0, 0.2, 1] }}
            >
              <X className="w-3 h-3" aria-hidden="true" />
            </motion.button>
          )}
        </AnimatePresence>
      </motion.div>

      {/* ── Error message ─────────────────────────────────────────────── */}
      <AnimatePresence>
        {error && (
          <motion.p
            id={errorId}
            role="alert"
            className="text-xs text-red-600 px-1"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
          >
            {error}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}
