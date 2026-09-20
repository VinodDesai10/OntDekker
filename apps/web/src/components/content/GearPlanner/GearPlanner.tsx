"use client";

/**
 * GearPlanner
 *
 * Interactive packing calculator for expedition gear lists.
 * Groups items by category (BASE_PACK, CONSUMABLES, WORN_GEAR) with
 * collapsible sections, per-item pack toggle, and total weight classification.
 */

import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Scale, CheckSquare, Square, ChevronDown, ChevronUp, Package } from "lucide-react";
import { WeightBadge } from "@/components/feedback/Badge";
import type { GearItem, GearCategory, PackWeightClassification } from "@/types";
import type { GearPlannerProps } from "./GearPlanner.types";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CATEGORY_ORDER: GearCategory[] = ["BASE_PACK", "CONSUMABLES", "WORN_GEAR"];

const CATEGORY_LABELS: Record<GearCategory, string> = {
  BASE_PACK: "Base Pack",
  CONSUMABLES: "Consumables",
  WORN_GEAR: "Worn Gear",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatWeight(grams: number): string {
  if (grams < 1000) return `${grams}g`;
  return `${(grams / 1000).toFixed(1)}kg`;
}

function classifyWeight(totalGrams: number): PackWeightClassification {
  if (totalGrams < 5000) return "ULTRALIGHT";
  if (totalGrams < 9000) return "LIGHTWEIGHT";
  if (totalGrams < 18000) return "STANDARD";
  return "HEAVY";
}

// ---------------------------------------------------------------------------
// Sub-component: CategorySection
// ---------------------------------------------------------------------------

interface CategorySectionProps {
  category: GearCategory;
  items: GearItem[];
  readOnly: boolean;
  onTogglePacked?: (itemId: string, isPacked: boolean) => void;
}

function CategorySection({
  category,
  items,
  readOnly,
  onTogglePacked,
}: CategorySectionProps) {
  const [isOpen, setIsOpen] = useState(true);

  const categoryWeightGrams = items.reduce(
    (sum, item) => sum + item.weightGrams * item.quantity,
    0
  );

  return (
    <div className="border border-gray-100 rounded-lg overflow-hidden">
      {/* Category header */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full flex items-center gap-2 px-4 py-2.5 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
        aria-expanded={isOpen}
      >
        {isOpen ? (
          <ChevronDown className="w-4 h-4 text-muted-slate shrink-0" aria-hidden="true" />
        ) : (
          <ChevronUp className="w-4 h-4 text-muted-slate shrink-0" aria-hidden="true" />
        )}
        <span className="text-sm font-medium text-charcoal flex-1">
          {CATEGORY_LABELS[category]}
        </span>
        <span className="text-xs text-muted-slate font-mono mr-2">
          {items.length} {items.length === 1 ? "item" : "items"}
        </span>
        <span className="text-xs text-muted-slate font-mono">
          {formatWeight(categoryWeightGrams)}
        </span>
      </button>

      {/* Animated item list */}
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <ul className="divide-y divide-gray-50">
              {items.map((item) => (
                <GearItemRow
                  key={item.id}
                  item={item}
                  readOnly={readOnly}
                  onTogglePacked={onTogglePacked}
                />
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-component: GearItemRow
// ---------------------------------------------------------------------------

interface GearItemRowProps {
  item: GearItem;
  readOnly: boolean;
  onTogglePacked?: (itemId: string, isPacked: boolean) => void;
}

function GearItemRow({ item, readOnly, onTogglePacked }: GearItemRowProps) {
  const lineItemWeight = item.weightGrams * item.quantity;

  return (
    <li
      className={[
        "flex items-center gap-3 px-4 py-2.5 transition-opacity",
        item.isPacked ? "opacity-50" : "opacity-100",
      ].join(" ")}
    >
      {/* Pack toggle checkbox */}
      {!readOnly && (
        <button
          type="button"
          onClick={() => onTogglePacked?.(item.id, !item.isPacked)}
          className="shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-moss-green rounded"
          aria-label={item.isPacked ? `Unpack ${item.name}` : `Pack ${item.name}`}
          aria-pressed={item.isPacked}
        >
          {item.isPacked ? (
            <CheckSquare
              className="w-4 h-4 text-moss-green"
              aria-hidden="true"
            />
          ) : (
            <Square
              className="w-4 h-4 text-muted-slate"
              aria-hidden="true"
            />
          )}
        </button>
      )}

      {/* Item name */}
      <span
        className={[
          "text-sm flex-1 min-w-0 truncate",
          item.isPacked ? "line-through text-muted-slate" : "text-charcoal",
        ].join(" ")}
      >
        {item.name}
      </span>

      {/* Quantity badge */}
      {item.quantity > 1 && (
        <span className="text-[10px] font-mono bg-gray-100 rounded px-1.5 py-0.5 text-charcoal shrink-0">
          x{item.quantity}
        </span>
      )}

      {/* Line-item weight */}
      <span className="text-xs text-muted-slate ml-auto shrink-0 font-mono">
        {formatWeight(lineItemWeight)}
      </span>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Main component: GearPlanner
// ---------------------------------------------------------------------------

export default function GearPlanner({
  items,
  onTogglePacked,
  readOnly = false,
  className = "",
}: GearPlannerProps) {
  // Derived weight stats
  const totalGrams = items.reduce(
    (sum, item) => sum + item.weightGrams * item.quantity,
    0
  );
  const packedCount = items.filter((item) => item.isPacked).length;
  const classification = classifyWeight(totalGrams);

  // Group items by category preserving display order
  const grouped: Record<GearCategory, GearItem[]> = {
    BASE_PACK: [],
    CONSUMABLES: [],
    WORN_GEAR: [],
  };
  for (const item of items) {
    grouped[item.category].push(item);
  }

  // Only render categories that have items
  const activeCategories = CATEGORY_ORDER.filter(
    (cat) => grouped[cat].length > 0
  );

  return (
    <section
      className={["flex flex-col gap-3", className].filter(Boolean).join(" ")}
      aria-label="Gear Planner"
    >
      {/* Header */}
      <div className="flex items-center gap-2 flex-wrap">
        <Scale className="w-4 h-4 text-charcoal shrink-0" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-charcoal">Gear Planner</h2>

        {items.length > 0 && (
          <WeightBadge
            classification={classification}
            weightGrams={totalGrams}
          />
        )}

        {items.length > 0 && (
          <span className="text-xs font-mono text-muted-slate ml-auto">
            ({packedCount} packed / {items.length} total)
          </span>
        )}
      </div>

      {/* Empty state */}
      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-6 gap-2 border border-dashed border-gray-200 rounded-lg">
          <Package className="w-8 h-8 text-gray-300" aria-hidden="true" />
          <p className="text-sm text-muted-slate text-center">
            No gear added yet.
          </p>
        </div>
      ) : (
        /* Category sections */
        <div className="flex flex-col gap-2">
          {activeCategories.map((category) => (
            <CategorySection
              key={category}
              category={category}
              items={grouped[category]}
              readOnly={readOnly}
              onTogglePacked={onTogglePacked}
            />
          ))}
        </div>
      )}
    </section>
  );
}
