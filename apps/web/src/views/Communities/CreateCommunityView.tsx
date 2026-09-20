"use client";

/**
 * OntDekker CreateCommunityView
 *
 * Full-page form for creating a new Community.
 *
 * Fields:
 *   - Cover Photo (banner) — optional image upload
 *   - Community Name (required, 3–100 chars)
 *   - Description (optional, max 2000 chars)
 *   - Location (optional)
 *   - Visibility — Public / Private toggle
 *   - Requires Approval (for private communities)
 *
 * Create flow:
 *   1. POST /communities/api/v1/communities  →  get community.id
 *   2. If banner selected → uploadCommunityBanner(id, file)
 *      The banner upload returns the updated Community record with bannerUrl set.
 *   3. Revalidate SWR cache for the new community so the detail page
 *      immediately shows the correct bannerUrl on first load.
 *   4. Redirect to /communities/{id}
 */

import React, { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSWRConfig } from "swr";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Globe,
  Lock,
  ImagePlus,
  Loader2,
  AlertCircle,
} from "lucide-react";

import {
  createCommunity,
  uploadCommunityBanner,
} from "@/services/communityApi";
import { communityKeys } from "@/services/cache";
import { useToast } from "@/hooks/useToast";
import type { CommunityVisibility } from "@/types";

// ---------------------------------------------------------------------------
// Banner image picker
// ---------------------------------------------------------------------------

interface BannerPickerProps {
  file: File | null;
  previewUrl: string | null;
  onFileSelect: (file: File) => void;
  onClear: () => void;
  disabled?: boolean;
}

function BannerPicker({
  file,
  previewUrl,
  onFileSelect,
  onClear,
  disabled,
}: BannerPickerProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    onFileSelect(selected);
    e.target.value = "";
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (disabled) return;
      const dropped = e.dataTransfer.files[0];
      if (dropped && dropped.type.startsWith("image/")) {
        onFileSelect(dropped);
      }
    },
    [disabled, onFileSelect],
  );

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-[#111111]">
        Cover Photo{" "}
        <span className="text-gray-400 font-normal">(optional)</span>
      </label>

      <button
        type="button"
        aria-label="Upload community cover photo"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className={[
          "relative w-full h-40 rounded-2xl overflow-hidden",
          "border-2 border-dashed transition-colors duration-150",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#111111]",
          disabled
            ? "opacity-50 cursor-not-allowed border-gray-200"
            : previewUrl
              ? "border-transparent cursor-pointer"
              : "border-[#EAE7DF] hover:border-gray-400 cursor-pointer bg-gray-50",
        ].join(" ")}
      >
        {previewUrl ? (
          <>
            <img
              src={previewUrl}
              alt="Cover photo preview"
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-black/20 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
              <div className="flex items-center gap-1.5 bg-white/90 rounded-xl px-3 py-1.5">
                <ImagePlus
                  size={14}
                  className="text-[#111111]"
                  aria-hidden="true"
                />
                <span className="text-xs font-medium text-[#111111]">
                  Change cover
                </span>
              </div>
            </div>
          </>
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center gap-2">
            <ImagePlus
              size={22}
              strokeWidth={1.5}
              className="text-gray-300"
              aria-hidden="true"
            />
            <span className="text-xs text-gray-400">
              Drag & drop or click to upload a cover photo
            </span>
            <span className="text-[10px] text-gray-300">
              JPEG, PNG, or WebP · Recommended: 1200 × 400 px
            </span>
          </div>
        )}
      </button>

      {file && (
        <button
          type="button"
          disabled={disabled}
          onClick={onClear}
          className="text-xs text-red-500 hover:text-red-700 transition-colors"
        >
          Remove cover photo
        </button>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/heic"
        className="sr-only"
        onChange={handleChange}
        disabled={disabled}
        aria-label="Select cover photo file"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Visibility toggle
// ---------------------------------------------------------------------------

function VisibilityToggle({
  value,
  onChange,
  disabled,
}: {
  value: CommunityVisibility;
  onChange: (v: CommunityVisibility) => void;
  disabled?: boolean;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Community visibility"
      className="flex rounded-2xl border border-[#EAE7DF] overflow-hidden"
    >
      {(["PUBLIC", "PRIVATE"] as CommunityVisibility[]).map((v) => {
        const isSelected = value === v;
        const Icon = v === "PUBLIC" ? Globe : Lock;
        return (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={isSelected}
            disabled={disabled}
            onClick={() => onChange(v)}
            className={[
              "flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition-all duration-150",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#111111]",
              isSelected
                ? "bg-[#111111] text-white"
                : "bg-white text-gray-600 hover:bg-gray-50",
              disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
            ].join(" ")}
          >
            <Icon size={14} strokeWidth={2} aria-hidden="true" />
            {v === "PUBLIC" ? "Public" : "Private"}
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// CreateCommunityView
// ---------------------------------------------------------------------------

export default function CreateCommunityView() {
  const router = useRouter();
  const { showToast } = useToast();
  const { mutate: globalMutate } = useSWRConfig();

  // ── Form state ─────────────────────────────────────────────────────────────
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [visibility, setVisibility] = useState<CommunityVisibility>("PUBLIC");
  const [requiresApproval, setRequiresApproval] = useState(false);

  // ── Banner state ───────────────────────────────────────────────────────────
  const [bannerFile, setBannerFile] = useState<File | null>(null);
  const [bannerPreview, setBannerPreview] = useState<string | null>(null);

  // ── Submission state ───────────────────────────────────────────────────────
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStep, setSubmitStep] = useState<
    "idle" | "creating" | "uploading_banner" | "done"
  >("idle");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  // ── Banner handlers ────────────────────────────────────────────────────────
  const handleBannerSelect = useCallback((file: File) => {
    setBannerFile(file);
    setBannerPreview(URL.createObjectURL(file));
  }, []);

  const handleBannerClear = useCallback(() => {
    if (bannerPreview) URL.revokeObjectURL(bannerPreview);
    setBannerFile(null);
    setBannerPreview(null);
  }, [bannerPreview]);

  // ── Validation ─────────────────────────────────────────────────────────────
  function validate(): boolean {
    const trimmed = name.trim();
    if (trimmed.length < 3) {
      setFieldError("Community name must be at least 3 characters.");
      return false;
    }
    if (trimmed.length > 100) {
      setFieldError("Community name must be 100 characters or fewer.");
      return false;
    }
    if (description.length > 2000) {
      setFieldError("Description must be 2000 characters or fewer.");
      return false;
    }
    if (location.length > 255) {
      setFieldError("Location must be 255 characters or fewer.");
      return false;
    }
    return true;
  }

  // ── Submission ─────────────────────────────────────────────────────────────
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFieldError(null);
    setApiError(null);

    if (!validate()) return;

    setIsSubmitting(true);
    setSubmitStep("creating");

    try {
      // Step 1: Create the community
      const community = await createCommunity({
        name: name.trim(),
        description: description.trim() || null,
        visibility,
        location: location.trim() || null,
        requires_approval: requiresApproval,
      });

      const communityId = community.id;

      // Step 2: Upload banner if provided.
      // uploadCommunityBanner returns the updated Community with bannerUrl set.
      // We prime the SWR cache with this updated record so the detail page
      // does NOT show a broken/missing image on first render — it gets the
      // correct bannerUrl immediately without a round-trip revalidation.
      let finalCommunity = community;
      if (bannerFile) {
        setSubmitStep("uploading_banner");
        finalCommunity = await uploadCommunityBanner(communityId, bannerFile);
      }

      // Prime the SWR cache for the detail page with the fully-updated record.
      // revalidate: false — we trust the response from uploadCommunityBanner.
      await globalMutate(communityKeys.byId(communityId), finalCommunity, {
        revalidate: false,
      });

      setSubmitStep("done");
      showToast("Community created successfully!", "success");
      router.push(`/communities/${communityId}`);
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again.";
      setApiError(msg);
      showToast(`Failed to create community: ${msg}`, "error");
      setSubmitStep("idle");
    } finally {
      setIsSubmitting(false);
    }
  }

  const submitLabel =
    submitStep === "creating"
      ? "Creating community…"
      : submitStep === "uploading_banner"
        ? "Uploading cover photo…"
        : "Create Community";

  const displayError = fieldError ?? apiError;

  return (
    <motion.div
      className="max-w-xl mx-auto pb-20"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0, 0, 0.2, 1] }}
    >
      {/* Back navigation */}
      <button
        type="button"
        onClick={() => router.back()}
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-[#111111] mb-6 transition-colors"
      >
        <ArrowLeft size={15} strokeWidth={2} aria-hidden="true" />
        Back to Communities
      </button>

      {/* Page header */}
      <div className="space-y-1 mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-[#111111]">
          Create a Community
        </h1>
        <p className="text-sm text-gray-500">
          Bring together travellers around a shared interest or destination.
        </p>
      </div>

      {/* Error banner */}
      {displayError && (
        <motion.div
          role="alert"
          className="flex items-start gap-2.5 bg-red-50 border border-red-100 rounded-2xl px-4 py-3 text-sm text-red-700 mb-6"
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <AlertCircle
            size={16}
            className="flex-shrink-0 mt-0.5"
            aria-hidden="true"
          />
          {displayError}
        </motion.div>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-6">
        {/* Cover Photo */}
        <BannerPicker
          file={bannerFile}
          previewUrl={bannerPreview}
          onFileSelect={handleBannerSelect}
          onClear={handleBannerClear}
          disabled={isSubmitting}
        />

        {/* Divider */}
        <div className="border-t border-[#EAE7DF]" aria-hidden="true" />

        {/* Community Name */}
        <div className="space-y-1.5">
          <label
            htmlFor="community-name"
            className="block text-sm font-medium text-[#111111]"
          >
            Community Name{" "}
            <span className="text-red-400" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="community-name"
            type="text"
            required
            minLength={3}
            maxLength={100}
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setFieldError(null);
            }}
            disabled={isSubmitting}
            placeholder="e.g. Alpine Explorers"
            className="w-full rounded-xl border border-[#EAE7DF] bg-white px-3.5 py-2.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
          />
          <p className="text-xs text-gray-400">3–100 characters.</p>
        </div>

        {/* Description */}
        <div className="space-y-1.5">
          <div className="flex items-baseline justify-between">
            <label
              htmlFor="community-description"
              className="block text-sm font-medium text-[#111111]"
            >
              Description{" "}
              <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <span className="text-xs text-gray-400">
              {description.length}/2000
            </span>
          </div>
          <textarea
            id="community-description"
            maxLength={2000}
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isSubmitting}
            placeholder="What is this community about? Who should join?"
            className="w-full resize-none rounded-xl border border-[#EAE7DF] bg-white px-3.5 py-2.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
          />
        </div>

        {/* Location */}
        <div className="space-y-1.5">
          <label
            htmlFor="community-location"
            className="block text-sm font-medium text-[#111111]"
          >
            Location{" "}
            <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <input
            id="community-location"
            type="text"
            maxLength={255}
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            disabled={isSubmitting}
            placeholder="e.g. Alps, Europe"
            className="w-full rounded-xl border border-[#EAE7DF] bg-white px-3.5 py-2.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
          />
        </div>

        {/* Divider */}
        <div className="border-t border-[#EAE7DF]" aria-hidden="true" />

        {/* Visibility */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-[#111111]">Visibility</p>
          <VisibilityToggle
            value={visibility}
            onChange={(v) => {
              setVisibility(v);
              if (v === "PUBLIC") setRequiresApproval(false);
            }}
            disabled={isSubmitting}
          />
          <p className="text-xs text-gray-400">
            {visibility === "PUBLIC"
              ? "Anyone can discover and browse this community."
              : "Only members can see this community's content."}
          </p>
        </div>

        {/* Requires Approval — shown only when Private */}
        {visibility === "PRIVATE" && (
          <motion.div
            className="flex items-start gap-3 bg-amber-50 border border-amber-100 rounded-2xl px-4 py-3"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
          >
            <input
              id="requires-approval"
              type="checkbox"
              checked={requiresApproval}
              onChange={(e) => setRequiresApproval(e.target.checked)}
              disabled={isSubmitting}
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-[#111111] focus:ring-[#111111]"
            />
            <label
              htmlFor="requires-approval"
              className="text-sm text-[#111111] cursor-pointer"
            >
              <span className="font-medium">Require approval to join</span>
              <p className="text-xs text-gray-500 mt-0.5">
                New member requests must be approved before they can
                participate.
              </p>
            </label>
          </motion.div>
        )}

        {/* Submit */}
        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className={[
              "flex-1 flex items-center justify-center gap-2",
              "rounded-xl bg-[#111111] text-white text-sm font-semibold",
              "py-3 px-6 transition-all duration-150",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#111111]",
              isSubmitting
                ? "opacity-70 cursor-not-allowed"
                : "hover:bg-[#2a2a2a] active:scale-[0.98]",
            ].join(" ")}
          >
            {isSubmitting && (
              <Loader2
                size={16}
                className="animate-spin"
                aria-hidden="true"
              />
            )}
            {submitLabel}
          </button>

          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => router.back()}
            className={[
              "rounded-xl border border-[#EAE7DF] bg-white text-[#111111] text-sm font-medium",
              "py-3 px-5 transition-all duration-150",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#111111]",
              isSubmitting
                ? "opacity-50 cursor-not-allowed"
                : "hover:bg-gray-50",
            ].join(" ")}
          >
            Cancel
          </button>
        </div>
      </form>
    </motion.div>
  );
}
