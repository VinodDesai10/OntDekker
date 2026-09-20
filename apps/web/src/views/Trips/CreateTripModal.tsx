"use client";

/**
 * OntDekker CreateTripModal
 *
 * Create Trip form with full validation:
 *   - Title, destination, description, cover image URL
 *   - Start / end dates (end >= start)
 *   - Budget >= 0
 *   - Max participants >= 1
 *   - Public or Community trip toggle
 *   - If community trip: community ID input
 */

import React, { useState } from "react";
import { X, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { useSWRConfig } from "swr";
import { FormField, TextInput, TextareaInput } from "@/components/forms";
import Button from "@/components/feedback/Button";
import { createTrip } from "@/services/tripsApi";
import { tripKeys } from "@/services/cache";
import { useToast } from "@/hooks/useToast";
import type { CreateTripRequest } from "@/types/trip";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated?: () => void;
}

interface FormState {
  title: string;
  destination: string;
  description: string;
  coverImageUrl: string;
  startDate: string;
  endDate: string;
  budget: string;
  maxParticipants: string;
  visibility: "PUBLIC" | "PRIVATE";
  isCommunityTrip: boolean;
  communityId: string;
}

const DEFAULT: FormState = {
  title: "",
  destination: "",
  description: "",
  coverImageUrl: "",
  startDate: "",
  endDate: "",
  budget: "",
  maxParticipants: "1",
  visibility: "PUBLIC",
  isCommunityTrip: false,
  communityId: "",
};

type FormErrors = Partial<Record<keyof FormState, string>>;

function validate(form: FormState): FormErrors {
  const errors: FormErrors = {};
  if (!form.title.trim()) errors.title = "Title is required.";
  else if (form.title.trim().length < 3) errors.title = "Title must be at least 3 characters.";
  if (!form.destination.trim()) errors.destination = "Destination is required.";

  const budget = parseFloat(form.budget);
  if (form.budget !== "" && (isNaN(budget) || budget < 0)) {
    errors.budget = "Budget must be 0 or greater.";
  }

  const max = parseInt(form.maxParticipants, 10);
  if (isNaN(max) || max < 1) errors.maxParticipants = "Must be at least 1 participant.";

  if (form.startDate && form.endDate && form.endDate < form.startDate) {
    errors.endDate = "End date cannot be before start date.";
  }

  if (form.isCommunityTrip && !form.communityId.trim()) {
    errors.communityId = "Community ID is required for community trips.";
  }

  return errors;
}

export default function CreateTripModal({ open, onClose, onCreated }: Props) {
  const [form, setForm] = useState<FormState>(DEFAULT);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const { showToast } = useToast();
  const { mutate } = useSWRConfig();

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: undefined }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate(form);
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      return;
    }

    const payload: CreateTripRequest = {
      title: form.title.trim(),
      destination: form.destination.trim(),
      description: form.description.trim() || null,
      coverImageUrl: form.coverImageUrl.trim() || null,
      startDate: form.startDate || null,
      endDate: form.endDate || null,
      budget: form.budget !== "" ? parseFloat(form.budget) : null,
      maxParticipants: parseInt(form.maxParticipants, 10),
      visibility: form.visibility,
      communityId: form.isCommunityTrip ? form.communityId.trim() : null,
    };

    setSubmitting(true);
    try {
      await createTrip(payload);
      showToast("Trip created!", "success");
      setForm(DEFAULT);
      setErrors({});
      // Revalidate both the public trips list and the user's own trips list
      // so the new trip appears immediately on both /trips and /my-trips,
      // regardless of which page opened this modal.
      await Promise.all([
        mutate(
          (key) =>
            Array.isArray(key) && key[0] === tripKeys.all()[0],
          undefined,
          { revalidate: true },
        ),
        mutate(
          (key) =>
            Array.isArray(key) && key[0] === tripKeys.mine()[0],
          undefined,
          { revalidate: true },
        ),
      ]);
      onCreated?.();
      onClose();
    } catch {
      showToast("Failed to create trip. Please try again.", "error");
    } finally {
      setSubmitting(false);
    }
  }

  function handleClose() {
    if (!submitting) {
      setForm(DEFAULT);
      setErrors({});
      onClose();
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
          />

          {/* Modal panel */}
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.2, ease: [0, 0, 0.2, 1] }}
          >
            <div
              className="w-full max-w-lg max-h-[90vh] overflow-y-auto bg-white rounded-2xl shadow-2xl"
              role="dialog"
              aria-modal="true"
              aria-labelledby="create-trip-title"
            >
              {/* Header */}
              <div className="sticky top-0 bg-white z-10 flex items-center justify-between px-6 pt-6 pb-4 border-b border-gray-100">
                <h2 id="create-trip-title" className="text-base font-semibold text-ink">
                  Create a Trip
                </h2>
                <button
                  type="button"
                  onClick={handleClose}
                  className="p-1.5 rounded-lg text-muted-slate hover:text-ink hover:bg-gray-100 transition-colors"
                  aria-label="Close"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
                {/* Title */}
                <TextInput
                  label="Title"
                  required
                  placeholder="e.g. Dolomites Autumn Route"
                  value={form.title}
                  onChange={(e) => set("title", e.target.value)}
                  error={errors.title}
                />

                {/* Destination */}
                <TextInput
                  label="Destination"
                  required
                  placeholder="e.g. South Tyrol, Italy"
                  value={form.destination}
                  onChange={(e) => set("destination", e.target.value)}
                  error={errors.destination}
                />

                {/* Description */}
                <TextareaInput
                  label="Description"
                  placeholder="Describe your trip..."
                  value={form.description}
                  onChange={(e) => set("description", e.target.value)}
                  rows={3}
                  maxLength={5000}
                  showCount
                />

                {/* Cover image URL */}
                <TextInput
                  label="Cover Image URL"
                  placeholder="https://..."
                  value={form.coverImageUrl}
                  onChange={(e) => set("coverImageUrl", e.target.value)}
                  hint="Paste a public image URL"
                />

                {/* Dates */}
                <div className="grid grid-cols-2 gap-3">
                  <FormField label="Start Date" htmlFor="start-date">
                    <input
                      id="start-date"
                      type="date"
                      value={form.startDate}
                      onChange={(e) => set("startDate", e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-ink focus:outline-none focus:bg-white focus:border-ink focus:ring-1 focus:ring-ink transition-all"
                    />
                  </FormField>
                  <FormField label="End Date" htmlFor="end-date" error={errors.endDate}>
                    <input
                      id="end-date"
                      type="date"
                      value={form.endDate}
                      min={form.startDate || undefined}
                      onChange={(e) => set("endDate", e.target.value)}
                      className={[
                        "w-full bg-gray-50 border rounded-xl px-4 py-2.5 text-sm text-ink focus:outline-none focus:bg-white focus:border-ink focus:ring-1 focus:ring-ink transition-all",
                        errors.endDate ? "border-red-300" : "border-gray-200",
                      ].join(" ")}
                    />
                  </FormField>
                </div>

                {/* Budget + Max participants */}
                <div className="grid grid-cols-2 gap-3">
                  <TextInput
                    label="Budget (USD)"
                    type="number"
                    min={0}
                    step={1}
                    placeholder="0"
                    value={form.budget}
                    onChange={(e) => set("budget", e.target.value)}
                    error={errors.budget}
                    hint="Per person estimate"
                  />
                  <TextInput
                    label="Max Participants"
                    required
                    type="number"
                    min={1}
                    placeholder="1"
                    value={form.maxParticipants}
                    onChange={(e) => set("maxParticipants", e.target.value)}
                    error={errors.maxParticipants}
                  />
                </div>

                {/* Visibility */}
                <FormField label="Visibility" htmlFor="visibility-select">
                  <select
                    id="visibility-select"
                    value={form.visibility}
                    onChange={(e) => set("visibility", e.target.value as "PUBLIC" | "PRIVATE")}
                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-ink focus:outline-none focus:bg-white focus:border-ink focus:ring-1 focus:ring-ink transition-all"
                  >
                    <option value="PUBLIC">Public — anyone can join</option>
                    <option value="PRIVATE">Private — join request required</option>
                  </select>
                </FormField>

                {/* Community trip toggle */}
                <div className="flex items-center justify-between py-1">
                  <div>
                    <p className="text-sm font-medium text-ink">Community Trip</p>
                    <p className="text-xs text-muted-slate">Associate this trip with a community</p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={form.isCommunityTrip}
                    onClick={() => set("isCommunityTrip", !form.isCommunityTrip)}
                    className={[
                      "relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent cursor-pointer",
                      "transition-colors duration-150",
                      form.isCommunityTrip ? "bg-ink" : "bg-gray-200",
                    ].join(" ")}
                  >
                    <span
                      aria-hidden="true"
                      className={[
                        "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform duration-150",
                        form.isCommunityTrip ? "translate-x-4" : "translate-x-0",
                      ].join(" ")}
                    />
                  </button>
                </div>

                {/* Community ID input (shown when community trip) */}
                {form.isCommunityTrip && (
                  <TextInput
                    label="Community ID"
                    required
                    placeholder="Paste community UUID"
                    value={form.communityId}
                    onChange={(e) => set("communityId", e.target.value)}
                    error={errors.communityId}
                    hint="Only community heads and co-heads can create community trips"
                  />
                )}

                {/* Actions */}
                <div className="flex items-center justify-end gap-3 pt-2 border-t border-gray-100">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleClose}
                    disabled={submitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    disabled={submitting}
                  >
                    {submitting ? (
                      <span className="flex items-center gap-2">
                        <Loader2 size={14} className="animate-spin" />
                        Creating…
                      </span>
                    ) : (
                      "Create Trip"
                    )}
                  </Button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
