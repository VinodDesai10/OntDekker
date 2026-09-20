"use client";

/**
 * OntDekker EditCommunityView
 *
 * Edit form for an existing Community. Only the HEAD (OWNER) can access this.
 *
 * Fields:
 *   - Cover Photo (banner) — optional replacement upload
 *   - Community Name (required, 3–100 chars)
 *   - Description (optional, max 2000 chars)
 *   - Location (optional)
 *   - Visibility — Public / Private toggle
 *   - Requires Approval (for private communities)
 *
 * Save flow:
 *   1. PATCH /communities/{id} with changed text fields
 *   2. If a new banner file was selected → uploadCommunityBanner(id, file)
 *      (returns updated Community with fresh bannerUrl)
 *   3. Prime SWR cache with the final Community record
 *   4. Redirect back to /communities/{id}
 */

import React, { useState, useRef, useCallback, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { useSWRConfig } from "swr";
import useSWR from "swr";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Globe,
  Lock,
  ImagePlus,
  Loader2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";

import {
  updateCommunity,
  uploadCommunityBanner,
} from "@/services/communityApi";
import { swrFetcher, communityKeys } from "@/services/cache";
import { useToast } from "@/hooks/useToast";
import { useAuth } from "@/contexts/AuthContext";
import Button from "@/components/feedback/Button";
import type { Community, CommunityVisibility } from "@/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Rewrite internal Docker hostname so the browser can display the image.
 * http://minio:9000/... → http://localhost:9000/...
 */
function resolveMediaUrl(url: string | null): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.hostname === "minio") {
      parsed.hostname = "localhost";
      parsed.port = "9000";
      return parsed.toString();
    }
    return url;
  } catch {
    return url;
  }
}

// ---------------------------------------------------------------------------
// Banner picker
// ---------------------------------------------------------------------------

interface BannerPickerProps {
  /** Existing remote URL (may be null if no banner set yet) */
  existingUrl: string | null;
  file: File | null;
  previewUrl: string | null;
  onFileSelect: (file: File) => void;
  onClear: () => void;
  disabled?: boolean;
}

function BannerPicker({
  existingUrl,
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

  // What to show: local preview takes priority over existing remote URL
  const displaySrc = previewUrl ?? resolveMediaUrl(existingUrl);

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
            : displaySrc
              ? "border-transparent cursor-pointer"
              : "border-[#EAE7DF] hover:border-gray-400 cursor-pointer bg-gray-50",
        ].join(" ")}
      >
        {displaySrc ? (
          <>
            <img
              src={displaySrc}
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
          Remove new cover photo
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
// EditCommunityView
// ---------------------------------------------------------------------------

export default function EditCommunityView() {
  const router = useRouter();
  const params = useParams();
  const communityId = (params?.id as string) ?? "";
  const { showToast } = useToast();
  const { mutate: globalMutate } = useSWRConfig();
  const { isAuthenticated } = useAuth();

  // ── Fetch the community to pre-fill the form ──────────────────────────────
  const {
    data: community,
    isLoading: communityLoading,
    error: communityError,
    mutate,
  } = useSWR<Community>(
    communityId ? communityKeys.byId(communityId) : null,
    swrFetcher,
    { revalidateOnFocus: false },
  );

  // ── Form state (pre-filled once community loads) ──────────────────────────
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [visibility, setVisibility] = useState<CommunityVisibility>("PUBLIC");
  const [requiresApproval, setRequiresApproval] = useState(false);

  // Sync form fields when community data first arrives
  useEffect(() => {
    if (!community) return;
    setName(community.name);
    setDescription(community.description ?? "");
    setLocation(community.location ?? "");
    setVisibility(community.visibility);
    setRequiresApproval(community.requiresApproval);
  }, [community]);

  // ── Banner state ───────────────────────────────────────────────────────────
  const [bannerFile, setBannerFile] = useState<File | null>(null);
  const [bannerPreview, setBannerPreview] = useState<string | null>(null);

  // ── Submission state ───────────────────────────────────────────────────────
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStep, setSubmitStep] = useState<
    "idle" | "saving" | "uploading_banner" | "done"
  >("idle");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

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
    setSubmitStep("saving");

    try {
      // Step 1: Save text fields
      let updated = await updateCommunity(communityId, {
        name: name.trim(),
        description: description.trim() || null,
        visibility,
        location: location.trim() || null,
        requires_approval: requiresApproval,
      });

      // Step 2: Upload new banner if one was selected
      if (bannerFile) {
        setSubmitStep("uploading_banner");
        updated = await uploadCommunityBanner(communityId, bannerFile);
      }

      // Prime SWR cache so the detail page shows fresh data immediately
      await globalMutate(communityKeys.byId(communityId), updated, {
        revalidate: false,
      });
      // Also revalidate the local mutation so the cache is consistent
      await mutate(updated, { revalidate: false });

      setSubmitStep("done");
      showToast("Community updated successfully!", "success");
      router.push(`/communities/${communityId}`);
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again.";
      setApiError(msg);
      showToast(`Failed to update community: ${msg}`, "error");
      setSubmitStep("idle");
    } finally {
      setIsSubmitting(false);
    }
  }

  const submitLabel =
    submitStep === "saving"
      ? "Saving…"
      : submitStep === "uploading_banner"
        ? "Uploading cover photo…"
        : "Save Changes";

  const displayError = fieldError ?? apiError;

  // ── Loading state ──────────────────────────────────────────────────────────
  if (communityLoading) {
    return (
      <div className="max-w-xl mx-auto pb-20 space-y-6">
        <div className="h-5 w-32 rounded-full bg-gray-100 animate-pulse" />
        <div className="h-8 w-64 rounded-full bg-gray-100 animate-pulse" />
        <div className="h-40 w-full rounded-2xl bg-gray-100 animate-pulse" />
        <div className="h-10 w-full rounded-xl bg-gray-100 animate-pulse" />
        <div className="h-24 w-full rounded-xl bg-gray-100 animate-pulse" />
      </div>
    );
  }

  // ── Error / not-found state ────────────────────────────────────────────────
  if (communityError || !community) {
    return (
      <div className="max-w-xl mx-auto pb-20 space-y-4">
        <button
          type="button"
          onClick={() => router.back()}
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-[#111111] transition-colors"
        >
          <ArrowLeft size={15} strokeWidth={2} aria-hidden="true" />
          Back
        </button>
        <div className="flex flex-col items-center justify-center py-16 text-center space-y-4">
          <p className="text-sm font-semibold text-[#111111]">
            Unable to load this community.
          </p>
          <Button variant="outline" size="sm" icon={RefreshCw} onClick={() => mutate()}>
            Retry
          </Button>
        </div>
      </div>
    );
  }

  // ── Access guard — only HEAD can edit ─────────────────────────────────────
  if (isAuthenticated && community.membershipStatus !== "HEAD") {
    return (
      <div className="max-w-xl mx-auto pb-20 space-y-4">
        <button
          type="button"
          onClick={() => router.back()}
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-[#111111] transition-colors"
        >
          <ArrowLeft size={15} strokeWidth={2} aria-hidden="true" />
          Back
        </button>
        <div className="flex flex-col items-center justify-center py-16 text-center space-y-2">
          <p className="text-sm font-semibold text-[#111111]">Access denied.</p>
          <p className="text-xs text-gray-500">
            Only the community owner can edit community settings.
          </p>
        </div>
      </div>
    );
  }

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
        onClick={() => router.push(`/communities/${communityId}`)}
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-[#111111] mb-6 transition-colors"
      >
        <ArrowLeft size={15} strokeWidth={2} aria-hidden="true" />
        Back to Community
      </button>

      {/* Page header */}
      <div className="space-y-1 mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-[#111111]">
          Edit Community
        </h1>
        <p className="text-sm text-gray-500 truncate">
          {community.name}
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
          existingUrl={community.bannerUrl}
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
            htmlFor="edit-community-name"
            className="block text-sm font-medium text-[#111111]"
          >
            Community Name{" "}
            <span className="text-red-400" aria-hidden="true">
              *
            </span>
          </label>
          <input
            id="edit-community-name"
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
              htmlFor="edit-community-description"
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
            id="edit-community-description"
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
            htmlFor="edit-community-location"
            className="block text-sm font-medium text-[#111111]"
          >
            Location{" "}
            <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <input
            id="edit-community-location"
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

        {/* Requires Approval */}
        {visibility === "PRIVATE" && (
          <motion.div
            className="flex items-start gap-3 bg-amber-50 border border-amber-100 rounded-2xl px-4 py-3"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
          >
            <input
              id="edit-requires-approval"
              type="checkbox"
              checked={requiresApproval}
              onChange={(e) => setRequiresApproval(e.target.checked)}
              disabled={isSubmitting}
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-[#111111] focus:ring-[#111111]"
            />
            <label
              htmlFor="edit-requires-approval"
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
            onClick={() => router.push(`/communities/${communityId}`)}
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
