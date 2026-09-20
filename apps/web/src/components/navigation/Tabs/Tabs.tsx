"use client";

/**
 * OntDekker Tabs
 *
 * Horizontal tab strip with an animated sliding ink indicator below the
 * active tab.  Used throughout the platform for workspace sub-navigation:
 *
 *   Communities  → Feed | Expeditions | Members | About
 *   Expedition   → Overview | Discussion | Packing | Gallery | Members
 *   Guides       → Discover | My Guides
 *   Profile      → Journal | Saved | Settings
 *
 * Motion:
 *   - Sliding underline uses `layoutId` on a `motion.span` so framer handles
 *     the FLIP animation automatically when the active tab changes.
 *   - Duration: 300ms, ease: standard cubic-bezier(0.4, 0, 0.2, 1)
 *
 * Mobile:
 *   - `overflow-x-auto scrollbar-none whitespace-nowrap` per design system
 *
 * Accessibility:
 *   - role="tablist" on the container
 *   - role="tab" on each button
 *   - aria-selected on the active tab
 *   - Keyboard: ArrowLeft / ArrowRight cycles tabs; Home / End jumps to ends
 */

import React, { useRef, useCallback } from "react";
import { motion } from "motion/react";
import type { TabsProps } from "./Tabs.types";

// Unique layout ID prefix so multiple Tabs instances on the same page don't
// share the same indicator animation target.
let instanceCounter = 0;

export default function Tabs({
  tabs,
  activeTabId,
  onChange,
  className = "",
}: TabsProps) {
  const layoutId = useRef(`tabs-indicator-${instanceCounter++}`).current;
  const listRef = useRef<HTMLDivElement>(null);

  // ── Keyboard navigation ────────────────────────────────────────────────
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, currentIndex: number) => {
      const enabledTabs = tabs.filter((t) => !t.disabled);
      const enabledIndex = enabledTabs.findIndex((t) => t.id === tabs[currentIndex].id);

      let nextEnabled: typeof tabs[number] | undefined;

      if (e.key === "ArrowRight") {
        e.preventDefault();
        nextEnabled = enabledTabs[(enabledIndex + 1) % enabledTabs.length];
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        nextEnabled =
          enabledTabs[(enabledIndex - 1 + enabledTabs.length) % enabledTabs.length];
      } else if (e.key === "Home") {
        e.preventDefault();
        nextEnabled = enabledTabs[0];
      } else if (e.key === "End") {
        e.preventDefault();
        nextEnabled = enabledTabs[enabledTabs.length - 1];
      }

      if (nextEnabled) {
        onChange(nextEnabled.id);
        // Move focus to the newly activated tab button
        const btn = listRef.current?.querySelector<HTMLButtonElement>(
          `[data-tab-id="${nextEnabled.id}"]`,
        );
        btn?.focus();
      }
    },
    [tabs, onChange],
  );

  return (
    <div
      ref={listRef}
      role="tablist"
      aria-label="Section navigation"
      className={[
        "relative flex",
        "overflow-x-auto scrollbar-none",
        "border-b border-[var(--color-border)]",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {tabs.map((tab, index) => {
        const isActive = tab.id === activeTabId;
        const isDisabled = tab.disabled ?? false;
        const Icon = tab.icon;

        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            data-tab-id={tab.id}
            aria-selected={isActive}
            aria-disabled={isDisabled}
            tabIndex={isActive ? 0 : -1}
            disabled={isDisabled}
            onClick={() => !isDisabled && onChange(tab.id)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            className={[
              "relative flex items-center gap-1.5 whitespace-nowrap",
              "px-4 py-2.5 text-sm font-medium",
              "transition-colors duration-[var(--duration-responsive)]",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-ink",
              isDisabled
                ? "opacity-40 cursor-not-allowed"
                : "cursor-pointer",
              isActive
                ? "text-ink"
                : "text-charcoal hover:text-ink",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {/* Icon */}
            {Icon && (
              <Icon
                className="w-4 h-4 flex-shrink-0"
                aria-hidden
              />
            )}

            {/* Label */}
            <span>{tab.label}</span>

            {/* Count badge */}
            {tab.count !== undefined && tab.count > 0 && (
              <span
                aria-hidden="true"
                className={[
                  "inline-flex items-center justify-center",
                  "min-w-[18px] h-[18px] px-1 rounded-full",
                  "text-[10px] font-bold font-mono leading-none",
                  isActive
                    ? "bg-ink text-white"
                    : "bg-gray-100 text-charcoal",
                ].join(" ")}
              >
                {tab.count > 99 ? "99+" : tab.count}
              </span>
            )}

            {/* Animated active indicator — slides between tabs via layoutId */}
            {isActive && (
              <motion.span
                layoutId={layoutId}
                className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full bg-ink"
                transition={{
                  type: "tween",
                  duration: 0.3,
                  ease: [0.4, 0, 0.2, 1],
                }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
