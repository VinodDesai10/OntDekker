"use client";

/**
 * PackingTab — Expedition workspace packing list tab.
 *
 * Loads the gear list for an expedition, supports:
 *   - Loading skeleton while data fetches
 *   - Error state on API failure
 *   - Empty state with "Add Gear Item" for active participants
 *   - Full gear list with weight summary badge
 *   - Toggle packed/unpacked state per item (item owner or organiser)
 *   - Delete item (item owner or organiser)
 *   - Add new item (active participants only)
 *
 * Authorization mirrors backend rules:
 *   GET     : any participant
 *   POST    : active participant
 *   PATCH   : item owner or organiser/co-organiser
 *   DELETE  : item owner or organiser/co-organiser
 *
 * Identity: item ownership checked via item.addedBy === myParticipant.user_id
 * (user_id on TripParticipant is the JWT sub — same as addedBy in gear items)
 */

import React, { useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import { motion } from "motion/react";
import {
  Backpack,
  CheckCircle,
  Circle,
  Scale,
  Trash2,
} from "lucide-react";

import { WeightBadge } from "@/components/feedback/Badge";
import { swrFetcher, expeditionKeys } from "@/services/cache";
import { addGearItem, updateGearItem, deleteGearItem } from "@/services/gearApi";
import type { AddGearItemRequest } from "@/services/gearApi";
import { useToast } from "@/hooks/useToast";

import type { GearItem, PackWeightSummary } from "@/types";
import type { TripParticipant } from "@/types/trip";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GearListResponse {
  expeditionId: string;
  items: GearItem[];
  summary: PackWeightSummary;
}

export interface PackingTabProps {
  expeditionId: string;
  /** Null when the user is not authenticated or not yet loaded */
  myParticipant: TripParticipant | null;
}

// ---------------------------------------------------------------------------
// PackingTab
// ---------------------------------------------------------------------------

export default function PackingTab({ expeditionId, myParticipant }: PackingTabProps) {
  const { showToast } = useToast();
  const { mutate } = useSWRConfig();

  // Packing state
  const [addName, setAddName] = useState("");
  const [addWeightGrams, setAddWeightGrams] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [adding, setAdding] = useState(false);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const gearKey = expeditionKeys.gear(expeditionId);

  const { data, isLoading, error } = useSWR<GearListResponse>(
    gearKey,
    swrFetcher,
    { revalidateOnFocus: false },
  );

  const gearList = data?.items ?? [];
  const summary = data?.summary ?? null;

  // An active participant can add items
  const isActiveParticipant = myParticipant?.status === "ACTIVE";
  // An organiser or co-organiser can also delete/edit others' items
  const isOrganiserRole =
    myParticipant?.role === "ORGANIZER" || myParticipant?.role === "CO_ORGANIZER";

  /** Can the current user toggle/delete this item?  */
  function canMutateItem(item: GearItem): boolean {
    if (!myParticipant || myParticipant.status !== "ACTIVE") return false;
    if (item.addedBy === myParticipant.user_id) return true;
    return isOrganiserRole;
  }

  async function handleToggle(item: GearItem) {
    if (togglingId || deletingId) return;
    setTogglingId(item.id);
    try {
      await updateGearItem(expeditionId, item.id, { isPacked: !item.isPacked });
      await mutate(gearKey);
    } catch {
      showToast("Failed to update item. Please try again.", "error");
    } finally {
      setTogglingId(null);
    }
  }

  async function handleDelete(itemId: string) {
    if (togglingId || deletingId) return;
    setDeletingId(itemId);
    try {
      await deleteGearItem(expeditionId, itemId);
      await mutate(gearKey);
    } catch {
      showToast("Failed to delete item. Please try again.", "error");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const trimmedName = addName.trim();
    if (!trimmedName) return;
    if (adding) return;
    setAdding(true);
    try {
      const payload: AddGearItemRequest = {
        name: trimmedName,
        ...(addWeightGrams !== "" && {
          weightGrams: Math.max(0, parseInt(addWeightGrams, 10) || 0),
        }),
      };
      await addGearItem(expeditionId, payload);
      await mutate(gearKey);
      setAddName("");
      setAddWeightGrams("");
      setShowAddForm(false);
    } catch {
      showToast("Failed to add item. Please try again.", "error");
    } finally {
      setAdding(false);
    }
  }

  // Loading skeleton
  if (isLoading) {
    return (
      <motion.div
        className="py-6 space-y-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.25 }}
        data-testid="packing-loading"
      >
        <div className="h-12 rounded-2xl bg-gray-100 animate-pulse" />
        <div className="bg-white border border-gray-100 rounded-3xl p-5 space-y-3 shadow-2xs">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 rounded-xl bg-gray-100 animate-pulse" />
          ))}
        </div>
      </motion.div>
    );
  }

  // Error state
  if (error) {
    return (
      <motion.div
        className="py-12 text-center space-y-2 bg-white border border-gray-100 rounded-3xl p-8 shadow-2xs"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        data-testid="packing-error"
      >
        <Backpack size={36} strokeWidth={1} className="text-red-300 mx-auto" aria-hidden="true" />
        <p className="text-sm font-semibold text-ink">Failed to load packing list.</p>
        <p className="text-xs text-muted-slate max-w-xs mx-auto">
          Please refresh the page or try again later.
        </p>
      </motion.div>
    );
  }

  // Empty state
  if (gearList.length === 0) {
    return (
      <motion.div
        className="py-6 space-y-4"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        data-testid="packing-empty"
      >
        <div className="py-12 text-center space-y-2 bg-white border border-gray-100 rounded-3xl p-8 shadow-2xs">
          <Backpack size={36} strokeWidth={1} className="text-gray-300 mx-auto" aria-hidden="true" />
          <p className="text-sm font-semibold text-ink">No gear added yet.</p>
          <p className="text-xs text-muted-slate max-w-xs mx-auto">
            Gear items added by expedition members will appear here.
          </p>
        </div>
        {isActiveParticipant && (
          <AddGearForm
            showAddForm={showAddForm}
            onToggleForm={() => setShowAddForm((v) => !v)}
            addName={addName}
            addWeightGrams={addWeightGrams}
            onNameChange={setAddName}
            onWeightChange={setAddWeightGrams}
            onSubmit={handleAdd}
            adding={adding}
          />
        )}
      </motion.div>
    );
  }

  return (
    <motion.div
      className="py-6 space-y-4"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      data-testid="packing-list"
    >
      {/* Weight summary bar */}
      {summary && (
        <div className="flex items-center justify-between bg-white border border-gray-100 rounded-2xl p-4 shadow-2xs">
          <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-muted-slate">
            <Scale size={14} aria-hidden="true" />
            Total Pack Weight
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-slate font-mono">
              {summary.packedItemsCount}/{summary.totalItemsCount} packed
            </span>
            <WeightBadge
              classification={summary.classification}
              weightGrams={summary.totalWeightGrams}
            />
          </div>
        </div>
      )}

      {/* Gear items */}
      <div className="bg-white border border-gray-100 rounded-3xl p-5 space-y-3 shadow-2xs">
        <h4 className="text-xs font-semibold text-ink uppercase tracking-wider font-mono">
          Gear List
        </h4>
        <div className="divide-y divide-gray-100">
          {gearList.map((item) => {
            const canMutate = canMutateItem(item);
            const isToggling = togglingId === item.id;
            const isDeleting = deletingId === item.id;

            return (
              <div
                key={item.id}
                className="py-3 flex items-center justify-between text-sm gap-3"
                data-testid={`gear-item-${item.id}`}
              >
                {/* Toggle checkbox button — only rendered for users who can mutate */}
                {canMutate ? (
                  <button
                    type="button"
                    aria-label={item.isPacked ? `Unpack ${item.name}` : `Pack ${item.name}`}
                    aria-pressed={item.isPacked}
                    disabled={isToggling || isDeleting}
                    onClick={() => handleToggle(item)}
                    className="flex-shrink-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500 rounded-full disabled:opacity-50"
                  >
                    {isToggling ? (
                      <span
                        className="block h-4 w-4 rounded-full border-2 border-emerald-500 border-t-transparent animate-spin"
                        aria-hidden="true"
                      />
                    ) : item.isPacked ? (
                      <CheckCircle size={16} className="text-green-600" aria-hidden="true" />
                    ) : (
                      <Circle size={16} className="text-gray-300" aria-hidden="true" />
                    )}
                  </button>
                ) : (
                  /* Read-only packed indicator for non-mutators */
                  <span className="flex-shrink-0" aria-hidden="true">
                    {item.isPacked ? (
                      <CheckCircle size={16} className="text-green-600 opacity-50" />
                    ) : (
                      <Circle size={16} className="text-gray-300 opacity-50" />
                    )}
                  </span>
                )}

                {/* Name */}
                <span
                  className={`flex-1 min-w-0 truncate ${
                    item.isPacked ? "text-ink font-medium line-through text-opacity-60" : "text-gray-700"
                  }`}
                >
                  {item.name}
                </span>

                {/* Weight */}
                <span className="text-xs font-mono text-muted-slate whitespace-nowrap">
                  {item.weightGrams > 0
                    ? item.weightGrams >= 1000
                      ? `${(item.weightGrams / 1000).toFixed(2)} kg`
                      : `${item.weightGrams} g`
                    : "—"}
                </span>

                {/* Delete button — only for owner/organiser */}
                {canMutate && (
                  <button
                    type="button"
                    aria-label={`Delete ${item.name}`}
                    disabled={isDeleting || isToggling}
                    onClick={() => handleDelete(item.id)}
                    className="flex-shrink-0 text-gray-300 hover:text-red-500 transition-colors disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 rounded"
                  >
                    {isDeleting ? (
                      <span
                        className="block h-3.5 w-3.5 rounded-full border-2 border-red-400 border-t-transparent animate-spin"
                        aria-hidden="true"
                      />
                    ) : (
                      <Trash2 size={13} aria-hidden="true" />
                    )}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Add item form — active participants only */}
      {isActiveParticipant && (
        <AddGearForm
          showAddForm={showAddForm}
          onToggleForm={() => setShowAddForm((v) => !v)}
          addName={addName}
          addWeightGrams={addWeightGrams}
          onNameChange={setAddName}
          onWeightChange={setAddWeightGrams}
          onSubmit={handleAdd}
          adding={adding}
        />
      )}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// AddGearForm — inline form for adding a new gear item
// ---------------------------------------------------------------------------

interface AddGearFormProps {
  showAddForm: boolean;
  onToggleForm: () => void;
  addName: string;
  addWeightGrams: string;
  onNameChange: (v: string) => void;
  onWeightChange: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  adding: boolean;
}

function AddGearForm({
  showAddForm,
  onToggleForm,
  addName,
  addWeightGrams,
  onNameChange,
  onWeightChange,
  onSubmit,
  adding,
}: AddGearFormProps) {
  return (
    <div data-testid="add-gear-section">
      {!showAddForm ? (
        <button
          type="button"
          onClick={onToggleForm}
          className="w-full flex items-center justify-center gap-2 rounded-2xl border border-dashed border-gray-200 py-3 text-xs font-medium text-muted-slate hover:border-gray-400 hover:text-ink transition-colors"
          data-testid="add-gear-toggle"
        >
          <span aria-hidden="true" className="text-base leading-none">+</span>
          Add Gear Item
        </button>
      ) : (
        <form
          onSubmit={onSubmit}
          className="bg-white border border-gray-100 rounded-2xl p-4 shadow-2xs space-y-3"
          data-testid="add-gear-form"
        >
          <p className="text-xs font-semibold text-ink uppercase tracking-wider font-mono">
            Add Gear Item
          </p>
          <div className="flex flex-col gap-2">
            <input
              type="text"
              placeholder="Item name (e.g. Sleeping Bag)"
              value={addName}
              onChange={(e) => onNameChange(e.target.value)}
              required
              maxLength={200}
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-ink placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              aria-label="Gear item name"
              data-testid="add-gear-name"
            />
            <input
              type="number"
              placeholder="Weight in grams (optional)"
              value={addWeightGrams}
              onChange={(e) => onWeightChange(e.target.value)}
              min={0}
              max={50000}
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-ink placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              aria-label="Gear item weight in grams"
              data-testid="add-gear-weight"
            />
          </div>
          <div className="flex items-center gap-2 justify-end">
            <button
              type="button"
              onClick={onToggleForm}
              disabled={adding}
              className="text-xs text-gray-500 hover:text-ink transition-colors disabled:opacity-50 px-3 py-1.5"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!addName.trim() || adding}
              className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-700 transition-colors disabled:opacity-50"
              data-testid="add-gear-submit"
            >
              {adding ? (
                <>
                  <span className="h-3 w-3 rounded-full border-2 border-white border-t-transparent animate-spin" aria-hidden="true" />
                  Adding…
                </>
              ) : (
                "Add Item"
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
