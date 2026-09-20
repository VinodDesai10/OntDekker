"use client";

/**
 * StoryComposer — Create Story Form Component
 *
 * Supports:
 *  - Visibility toggle: Global (PUBLIC) / Community (COMMUNITY)
 *  - Community selector: populated from the user's real memberships only
 *  - Text fields: title, content, location
 *  - Image selection: multi-file picker (jpeg, png, webp, heic)
 *  - Local previews before publishing
 *  - Remove individual images before publishing
 *  - After create: presign → PUT to MinIO → register, per image
 *  - Per-image upload progress bar
 *  - Graceful per-image error messages
 *  - SWR feed revalidation on successful creation (text-only and with images)
 *
 * Visibility semantics (match backend PostVisibility enum):
 *   "GLOBAL"    → sent as visibility="PUBLIC", community_id=null
 *   "COMMUNITY" → sent as visibility="COMMUNITY", community_id=<selected>
 *
 * Upload orchestration (FC-2.3 backend workflow):
 *  1. createPost()                          → receives post_id
 *  2. generateMediaUploadUrl(postId, file)  → { uploadUrl, objectKey }
 *  3. uploadFileToMinIO(uploadUrl, file)    → binary PUT directly to MinIO
 *  4. registerPostMedia(postId, objectKey)  → persists metadata in feed_db
 *  5. mutate() / onUploadComplete()         → refresh feed
 */

import React, { useRef, useState, useCallback } from "react";
import { Send, ImagePlus, X, AlertCircle, Globe, Users } from "lucide-react";
import { generateMediaUploadUrl, uploadFileToMinIO, registerPostMedia } from "@/services/feedApi";
import type { CreatePostRequest, PostVisibility } from "@/types";

// ---------------------------------------------------------------------------
// Local types
// ---------------------------------------------------------------------------

interface SelectedImage {
  /** Stable local key for React reconciliation */
  key: string;
  file: File;
  /** Object URL for preview — revoked after submit */
  previewUrl: string;
  /** 0–100 during upload, null when not yet started */
  progress: number | null;
  /** Set if this image's upload failed */
  error: string | null;
}

/**
 * UI-level visibility choice.
 * "GLOBAL" maps to PostVisibility "PUBLIC" on the backend.
 * "COMMUNITY" maps to PostVisibility "COMMUNITY" on the backend.
 */
type VisibilityChoice = "GLOBAL" | "COMMUNITY";

interface StoryComposerProps {
  user: { email: string; id: string } | null;
  onSubmit: (payload: CreatePostRequest) => Promise<string>;
  onUploadComplete: () => Promise<void>;
  /** Communities where the current user is an active member (from real API) */
  communities: { id: string; name: string }[];
}

// ---------------------------------------------------------------------------
// Allowed MIME types (must match backend validation)
// ---------------------------------------------------------------------------

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/heic"];
const ALLOWED_ACCEPT = ALLOWED_TYPES.join(",");
const MAX_IMAGES = 10;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function StoryComposer({
  user,
  onSubmit,
  onUploadComplete,
  communities,
}: StoryComposerProps) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [location, setLocation] = useState("");

  // Visibility choice — defaults to GLOBAL (public feed)
  const [visibilityChoice, setVisibilityChoice] = useState<VisibilityChoice>("GLOBAL");
  const [selectedCommunityId, setSelectedCommunityId] = useState("");

  const [selectedImages, setSelectedImages] = useState<SelectedImage[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [uploadingImages, setUploadingImages] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Image selection ───────────────────────────────────────────────────────

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    // Reset the input so the same file can be re-selected after removal
    e.target.value = "";

    const valid = files.filter((f) => ALLOWED_TYPES.includes(f.type));
    const invalid = files.filter((f) => !ALLOWED_TYPES.includes(f.type));

    if (invalid.length > 0) {
      console.warn("Unsupported file type(s) ignored:", invalid.map((f) => f.name));
    }

    setSelectedImages((prev) => {
      const remaining = MAX_IMAGES - prev.length;
      const toAdd = valid.slice(0, remaining).map((file) => ({
        key: `${file.name}-${file.size}-${Date.now()}-${Math.random()}`,
        file,
        previewUrl: URL.createObjectURL(file),
        progress: null,
        error: null,
      }));
      return [...prev, ...toAdd];
    });
  }

  function removeImage(key: string) {
    setSelectedImages((prev) => {
      const image = prev.find((i) => i.key === key);
      if (image) URL.revokeObjectURL(image.previewUrl);
      return prev.filter((i) => i.key !== key);
    });
  }

  function updateImageState(
    key: string,
    patch: Partial<Pick<SelectedImage, "progress" | "error">>,
  ) {
    setSelectedImages((prev) =>
      prev.map((img) => (img.key === key ? { ...img, ...patch } : img)),
    );
  }

  // ── Upload a single image ────────────────────────────────────────────────

  const uploadSingleImage = useCallback(
    async (postId: string, image: SelectedImage, displayOrder: number) => {
      updateImageState(image.key, { progress: 0, error: null });

      // Step 2 — generate presigned URL
      const { uploadUrl, objectKey } = await generateMediaUploadUrl(postId, {
        filename: image.file.name,
        content_type: image.file.type,
      });

      // Step 3 — upload binary to MinIO with progress
      await uploadFileToMinIO(uploadUrl, image.file, (pct) =>
        updateImageState(image.key, { progress: pct }),
      );

      // Step 4 — register with the feed service
      await registerPostMedia(postId, {
        object_key: objectKey,
        display_order: displayOrder,
        alt_text: null,
      });

      updateImageState(image.key, { progress: 100 });
    },
    [],
  );

  // ── Visibility change handler ─────────────────────────────────────────────

  function handleVisibilityChange(choice: VisibilityChoice) {
    setVisibilityChoice(choice);
    // Reset community selection when switching back to GLOBAL
    if (choice === "GLOBAL") {
      setSelectedCommunityId("");
    }
  }

  // ── Form submit ──────────────────────────────────────────────────────────

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() && !content.trim()) return;

    // Validate community selection when COMMUNITY visibility is chosen
    if (visibilityChoice === "COMMUNITY" && !selectedCommunityId) {
      // Form validation will surface this — do not proceed
      return;
    }

    setSubmitting(true);
    let postId: string;

    // Map UI choice to backend PostVisibility value
    const backendVisibility: PostVisibility =
      visibilityChoice === "COMMUNITY" ? "COMMUNITY" : "PUBLIC";

    try {
      // Step 1 — create the post
      postId = await onSubmit({
        title: title.trim() || "Travel Note",
        content: content.trim(),
        location: location.trim() || null,
        visibility: backendVisibility,
        communityId: visibilityChoice === "COMMUNITY" ? selectedCommunityId : null,
        tags: [],
      });
    } catch {
      setSubmitting(false);
      return; // onSubmit shows the toast and calls mutate() on success
    }

    // If there are images, upload them all sequentially
    if (selectedImages.length > 0) {
      setUploadingImages(true);
      let allSucceeded = true;

      for (let i = 0; i < selectedImages.length; i++) {
        const img = selectedImages[i];
        try {
          await uploadSingleImage(postId, img, i);
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Upload failed";
          updateImageState(img.key, { error: message });
          allSucceeded = false;
        }
      }

      setUploadingImages(false);

      if (!allSucceeded) {
        // Leave the form open so user can see which images failed
        setSubmitting(false);
        return;
      }
    }

    // All done — clean up and refresh the feed
    selectedImages.forEach((img) => URL.revokeObjectURL(img.previewUrl));
    setTitle("");
    setContent("");
    setLocation("");
    setVisibilityChoice("GLOBAL");
    setSelectedCommunityId("");
    setSelectedImages([]);
    setOpen(false);
    setSubmitting(false);

    // Step 5 — refresh the feed (includes updated media)
    await onUploadComplete();
  }

  function handleCancel() {
    selectedImages.forEach((img) => URL.revokeObjectURL(img.previewUrl));
    setSelectedImages([]);
    setTitle("");
    setContent("");
    setLocation("");
    setVisibilityChoice("GLOBAL");
    setSelectedCommunityId("");
    setOpen(false);
  }

  // ── Derived state ─────────────────────────────────────────────────────────

  const isWorking = submitting || uploadingImages;
  const hasContent = title.trim().length > 0 || content.trim().length > 0;
  const anyFailed = selectedImages.some((img) => img.error !== null);
  const communityRequired = visibilityChoice === "COMMUNITY";
  const communityMissing = communityRequired && !selectedCommunityId;
  const canSubmit = hasContent && !anyFailed && !communityMissing;

  return (
    <div className="rounded-2xl border border-[#EAE7DF] bg-white p-5 space-y-4 shadow-2xs">
      {/* Collapsed trigger row */}
      <div className="flex items-center gap-3">
        <div className="size-10 rounded-full bg-[#111111] text-white flex items-center justify-center font-bold text-sm shrink-0">
          {user?.email.charAt(0).toUpperCase() ?? "U"}
        </div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="w-full text-left rounded-xl border border-[#EAE7DF] bg-[#FBF9F4] px-4 py-2.5 text-sm text-gray-500 hover:border-gray-300 transition-colors"
        >
          Share your story, expedition note, or travel recommendation…
        </button>
      </div>

      {/* Expanded form */}
      {open && (
        <form
          onSubmit={handleSubmit}
          className="space-y-4 pt-2 border-t border-[#EAE7DF]"
        >
          {/* ── Visibility Toggle ────────────────────────────────────────── */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-500 mr-1">Post to:</span>
            <button
              type="button"
              onClick={() => handleVisibilityChange("GLOBAL")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                visibilityChoice === "GLOBAL"
                  ? "bg-[#111111] text-white"
                  : "bg-white border border-[#EAE7DF] text-gray-600 hover:bg-gray-50"
              }`}
            >
              <Globe size={12} />
              Global
            </button>
            <button
              type="button"
              onClick={() => handleVisibilityChange("COMMUNITY")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                visibilityChoice === "COMMUNITY"
                  ? "bg-[#111111] text-white"
                  : "bg-white border border-[#EAE7DF] text-gray-600 hover:bg-gray-50"
              }`}
            >
              <Users size={12} />
              Community
            </button>
          </div>

          {/* ── Community Selector (only shown when COMMUNITY is selected) ── */}
          {visibilityChoice === "COMMUNITY" && (
            <div className="space-y-1.5">
              {communities.length === 0 ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-xs text-amber-700 flex items-start gap-2">
                  <AlertCircle size={14} className="shrink-0 mt-0.5" />
                  <span>
                    You are not a member of any community yet. Join a community
                    first to post there.
                  </span>
                </div>
              ) : (
                <select
                  value={selectedCommunityId}
                  onChange={(e) => setSelectedCommunityId(e.target.value)}
                  required={communityRequired}
                  className="w-full rounded-xl border border-[#EAE7DF] bg-white px-3.5 py-2 text-sm text-gray-700 outline-none focus:border-[#111111]"
                >
                  <option value="">— Select a community —</option>
                  {communities.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}

          {/* Title */}
          <input
            type="text"
            placeholder="Story Title (e.g. Hidden Trails of the Pyrenees)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-xl border border-[#EAE7DF] px-3.5 py-2 text-sm text-[#111111] placeholder:text-gray-400 outline-none focus:border-[#111111]"
          />

          {/* Content */}
          <textarea
            rows={3}
            placeholder="Tell your travel story or ask a question to the community..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full rounded-xl border border-[#EAE7DF] p-3.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none focus:border-[#111111] resize-none"
          />

          {/* Location */}
          <input
            type="text"
            placeholder="Location (e.g. Chamonix, France)"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="w-full rounded-xl border border-[#EAE7DF] px-3.5 py-2 text-xs text-[#111111] placeholder:text-gray-400 outline-none focus:border-[#111111]"
          />

          {/* ── Image previews ─────────────────────────────────────────────── */}
          {selectedImages.length > 0 && (
            <div className="grid grid-cols-3 gap-2">
              {selectedImages.map((img) => (
                <div
                  key={img.key}
                  className="relative rounded-xl overflow-hidden bg-gray-100 aspect-square"
                >
                  {/* Preview */}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={img.previewUrl}
                    alt={img.file.name}
                    className="w-full h-full object-cover"
                  />

                  {/* Remove button — hidden while uploading */}
                  {img.progress === null && !isWorking && (
                    <button
                      type="button"
                      aria-label={`Remove ${img.file.name}`}
                      onClick={() => removeImage(img.key)}
                      className="absolute top-1.5 right-1.5 size-5 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-black/80 transition-colors"
                    >
                      <X size={11} strokeWidth={2.5} />
                    </button>
                  )}

                  {/* Progress bar overlay */}
                  {img.progress !== null && img.error === null && (
                    <div className="absolute inset-x-0 bottom-0 bg-black/40 px-2 py-1.5">
                      <div className="h-1 w-full rounded-full bg-white/30 overflow-hidden">
                        <div
                          className="h-full bg-white rounded-full transition-all duration-150"
                          style={{ width: `${img.progress}%` }}
                        />
                      </div>
                      <p className="text-[10px] text-white/80 text-center mt-0.5">
                        {img.progress < 100 ? `${img.progress}%` : "Done"}
                      </p>
                    </div>
                  )}

                  {/* Error overlay */}
                  {img.error && (
                    <div className="absolute inset-0 bg-red-900/60 flex flex-col items-center justify-center gap-1 p-1.5">
                      <AlertCircle size={16} className="text-white" />
                      <p className="text-[10px] text-white text-center leading-tight line-clamp-2">
                        {img.error}
                      </p>
                      <button
                        type="button"
                        onClick={() => removeImage(img.key)}
                        className="text-[10px] text-white/80 underline"
                      >
                        Remove
                      </button>
                    </div>
                  )}
                </div>
              ))}

              {/* Add more slot */}
              {selectedImages.length < MAX_IMAGES && !isWorking && (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="aspect-square rounded-xl border-2 border-dashed border-[#EAE7DF] flex flex-col items-center justify-center gap-1 text-gray-400 hover:border-gray-400 hover:text-gray-600 transition-colors"
                  aria-label="Add more photos"
                >
                  <ImagePlus size={18} />
                  <span className="text-[10px]">Add more</span>
                </button>
              )}
            </div>
          )}

          {/* Bottom bar */}
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-2">
              {/* Add Photos button */}
              {!isWorking && selectedImages.length < MAX_IMAGES && (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-[#EAE7DF] bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:border-gray-300 hover:text-[#111111] transition-colors"
                  aria-label="Add photos"
                >
                  <ImagePlus size={13} />
                  {selectedImages.length > 0 ? `${selectedImages.length} photo${selectedImages.length > 1 ? "s" : ""}` : "Add Photos"}
                </button>
              )}

              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept={ALLOWED_ACCEPT}
                multiple
                className="sr-only"
                onChange={handleFileChange}
                aria-hidden="true"
              />
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCancel}
                disabled={isWorking}
                className="px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-[#111111] disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isWorking || !canSubmit}
                className="inline-flex items-center gap-1.5 rounded-xl bg-[#111111] px-4 py-2 text-xs font-semibold text-white hover:bg-[#333333] transition-colors disabled:opacity-50"
              >
                <Send size={13} />
                {uploadingImages
                  ? "Uploading photos…"
                  : submitting
                    ? "Publishing…"
                    : "Publish Post"}
              </button>
            </div>
          </div>

          {/* Community required hint */}
          {communityRequired && communityMissing && communities.length > 0 && (
            <p className="text-xs text-amber-600 flex items-center gap-1.5">
              <AlertCircle size={12} />
              Please select a community before publishing.
            </p>
          )}

          {/* Failed uploads hint */}
          {anyFailed && (
            <p className="text-xs text-red-600 flex items-center gap-1.5">
              <AlertCircle size={12} />
              Some photos failed to upload. Remove them and try again, or publish without them.
            </p>
          )}
        </form>
      )}
    </div>
  );
}
