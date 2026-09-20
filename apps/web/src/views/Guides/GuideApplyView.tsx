"use client";

/**
 * OntDekker GuideApplyView
 *
 * Full-page guide application form.
 *
 * Two-step flow (matching the backend state machine):
 *   Step 1: User fills in the form and clicks "Save Draft"
 *           → POST /guides/api/v1/guides/apply  (creates DRAFT)
 *   Step 2: User clicks "Submit Application"
 *           → POST /guides/api/v1/guides/apply/{id}/submit  (DRAFT → SUBMITTED)
 *
 * Fields (from GuideApplicationCreate schema):
 *   - biography        (required, 100–3000 chars)
 *   - areas_covered    (optional, max 1000 chars)
 *   - languages        (optional, max 500 chars)
 *   - experience_years (optional, 0–80)
 *   - certifications   (optional, max 1000 chars)
 *   - identity_document_url (optional, max 500 chars — MinIO URL)
 *
 * States:
 *   - idle           — showing the form
 *   - saving         — POST in-flight
 *   - submitting     — submit POST in-flight
 *   - success        — SUBMITTED successfully
 *   - error          — API error with message
 */

import React, { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSWRConfig } from "swr";
import { motion, AnimatePresence } from "motion/react";
import {
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Loader2,
  MapPin,
  Globe,
  Briefcase,
  Award,
  FileText,
  Link as LinkIcon,
} from "lucide-react";

import {
  applyForGuide,
  submitGuideApplication,
} from "@/services/guideApi";
import { guideKeys } from "@/services/cache";

import type { GuideApplicationCreate, GuideApplicationResponse } from "@/types";

// ---------------------------------------------------------------------------
// Character counter
// ---------------------------------------------------------------------------

function CharCount({
  current,
  max,
  min,
}: {
  current: number;
  max: number;
  min?: number;
}) {
  const isTooShort = min !== undefined && current > 0 && current < min;
  const isTooLong = current > max;
  const colorClass = isTooLong
    ? "text-red-500"
    : isTooShort
    ? "text-amber-500"
    : "text-muted-slate";

  return (
    <span className={`text-[10px] font-mono ${colorClass}`}>
      {current}/{max}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Field label component
// ---------------------------------------------------------------------------

function FieldLabel({
  htmlFor,
  label,
  required,
  description,
}: {
  htmlFor: string;
  label: string;
  required?: boolean;
  description?: string;
}) {
  return (
    <div className="space-y-0.5">
      <label htmlFor={htmlFor} className="block text-sm font-medium text-ink">
        {label}
        {required && (
          <span className="ml-1 text-red-500" aria-hidden="true">
            *
          </span>
        )}
      </label>
      {description && (
        <p className="text-xs text-muted-slate">{description}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Success state
// ---------------------------------------------------------------------------

function SuccessState({ onBack }: { onBack: () => void }) {
  return (
    <motion.div
      className="flex flex-col items-center justify-center py-20 gap-6 text-center"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: [0, 0, 0.2, 1] }}
      data-testid="success-state"
    >
      <div className="w-16 h-16 rounded-full bg-green-50 flex items-center justify-center">
        <CheckCircle2
          size={32}
          strokeWidth={1.5}
          className="text-green-500"
          aria-hidden="true"
        />
      </div>
      <div className="space-y-2 max-w-sm">
        <h2 className="text-xl font-bold text-ink">Application Submitted!</h2>
        <p className="text-sm text-charcoal">
          Your guide application has been submitted for review. Our team
          will review it and get back to you. This typically takes 2–5
          business days.
        </p>
      </div>
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-ink text-white text-sm font-medium hover:bg-ink/90 transition-colors"
        >
          Back to Guides
        </button>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Error banner
// ---------------------------------------------------------------------------

function ErrorBanner({ message }: { message: string }) {
  return (
    <motion.div
      role="alert"
      className="flex items-start gap-3 bg-red-50 border border-red-100 rounded-2xl px-4 py-3"
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <AlertCircle
        size={16}
        strokeWidth={2}
        className="flex-shrink-0 text-red-500 mt-0.5"
        aria-hidden="true"
      />
      <p className="text-sm text-red-700">{message}</p>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// GuideApplyView
// ---------------------------------------------------------------------------

type FormState = "idle" | "saving" | "submitting" | "success" | "error";

export default function GuideApplyView() {
  const router = useRouter();
  const { mutate } = useSWRConfig();

  // Form fields — matching GuideApplicationCreate exactly
  const [biography, setBiography] = useState("");
  const [areasCovered, setAreasCovered] = useState("");
  const [languages, setLanguages] = useState("");
  const [experienceYears, setExperienceYears] = useState<string>("");
  const [certifications, setCertifications] = useState("");
  const [identityDocumentUrl, setIdentityDocumentUrl] = useState("");

  // Validation errors per-field
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const [formState, setFormState] = useState<FormState>("idle");
  const [apiError, setApiError] = useState<string>("");
  const [draftApplication, setDraftApplication] =
    useState<GuideApplicationResponse | null>(null);

  // ── Validation ─────────────────────────────────────────────────────────────

  const validate = useCallback((): boolean => {
    const errors: Record<string, string> = {};

    if (!biography.trim()) {
      errors.biography = "Biography is required.";
    } else if (biography.trim().length < 100) {
      errors.biography = `Biography must be at least 100 characters (currently ${biography.trim().length}).`;
    } else if (biography.trim().length > 3000) {
      errors.biography = "Biography cannot exceed 3000 characters.";
    }

    if (areasCovered && areasCovered.length > 1000) {
      errors.areas_covered = "Areas covered cannot exceed 1000 characters.";
    }

    if (languages && languages.length > 500) {
      errors.languages = "Languages cannot exceed 500 characters.";
    }

    if (experienceYears !== "") {
      const years = parseInt(experienceYears, 10);
      if (isNaN(years) || years < 0) {
        errors.experience_years = "Experience years must be a positive number.";
      } else if (years > 80) {
        errors.experience_years = "Experience years cannot exceed 80.";
      }
    }

    if (certifications && certifications.length > 1000) {
      errors.certifications = "Certifications cannot exceed 1000 characters.";
    }

    if (identityDocumentUrl && identityDocumentUrl.length > 500) {
      errors.identity_document_url =
        "Document URL cannot exceed 500 characters.";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }, [biography, areasCovered, languages, experienceYears, certifications, identityDocumentUrl]);

  // ── Build payload ───────────────────────────────────────────────────────────

  const buildPayload = useCallback((): GuideApplicationCreate => {
    const payload: GuideApplicationCreate = {
      biography: biography.trim(),
    };
    if (areasCovered.trim()) payload.areas_covered = areasCovered.trim();
    if (languages.trim()) payload.languages = languages.trim();
    if (experienceYears !== "") {
      payload.experience_years = parseInt(experienceYears, 10);
    }
    if (certifications.trim()) payload.certifications = certifications.trim();
    if (identityDocumentUrl.trim())
      payload.identity_document_url = identityDocumentUrl.trim();
    return payload;
  }, [biography, areasCovered, languages, experienceYears, certifications, identityDocumentUrl]);

  // ── Submit handler ──────────────────────────────────────────────────────────

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setApiError("");

      if (!validate()) return;

      try {
        // Step 1: Create DRAFT
        setFormState("saving");
        const draft = await applyForGuide(buildPayload());
        setDraftApplication(draft);

        // Step 2: Submit DRAFT → SUBMITTED
        setFormState("submitting");
        await submitGuideApplication(draft.id);

        // Invalidate any cached guide queries
        await mutate(guideKeys.myConnections());

        setFormState("success");
      } catch (err: unknown) {
        setFormState("error");
        const errorObj = err as { response?: { data?: { detail?: string } }; message?: string };
        const detail =
          errorObj?.response?.data?.detail ??
          errorObj?.message ??
          "Failed to submit application. Please try again.";
        setApiError(typeof detail === "string" ? detail : "Failed to submit application.");
      }
    },
    [validate, buildPayload, mutate],
  );

  // ── Render ─────────────────────────────────────────────────────────────────

  const isSubmitting = formState === "saving" || formState === "submitting";

  if (formState === "success") {
    return (
      <div className="container-main py-8">
        <SuccessState onBack={() => router.push("/guides")} />
      </div>
    );
  }

  return (
    <motion.div
      className="container-main py-8 pb-20"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0, 0, 0.2, 1] }}
    >
      {/* ── Back navigation ────────────────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => router.back()}
        className="inline-flex items-center gap-1.5 text-sm text-muted-slate hover:text-ink transition-colors mb-6"
        aria-label="Go back"
      >
        <ArrowLeft size={16} strokeWidth={2} aria-hidden="true" />
        Back
      </button>

      {/* ── Page header ────────────────────────────────────────────────────── */}
      <div className="mb-8 space-y-1">
        <p className="text-xs font-mono uppercase tracking-widest text-muted-slate">
          Guides
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-ink">
          Become a Guide
        </h1>
        <p className="text-sm text-muted-slate max-w-xl">
          Share your expertise with travelers around the world. Complete the
          form below — our team will review your application within 2–5
          business days.
        </p>
      </div>

      {/* ── API Error ──────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {formState === "error" && apiError && (
          <div className="mb-6">
            <ErrorBanner message={apiError} />
          </div>
        )}
      </AnimatePresence>

      {/* ── Form ───────────────────────────────────────────────────────────── */}
      <form onSubmit={handleSubmit} noValidate>
        <div className="space-y-8 max-w-2xl">
          {/* ── Biography ──────────────────────────────────────────────────── */}
          <div className="space-y-2">
            <div className="flex items-end justify-between">
              <FieldLabel
                htmlFor="biography"
                label="Biography"
                required
                description="Tell travelers about yourself, your guiding style, and what makes your experiences unique."
              />
              <CharCount
                current={biography.length}
                max={3000}
                min={100}
              />
            </div>
            <div className="relative">
              <FileText
                size={14}
                strokeWidth={2}
                className="absolute left-3 top-3 text-muted-slate pointer-events-none"
                aria-hidden="true"
              />
              <textarea
                id="biography"
                name="biography"
                value={biography}
                onChange={(e) => setBiography(e.target.value)}
                rows={6}
                maxLength={3000}
                placeholder="I am a certified mountain guide with over 10 years of experience leading expeditions across the Himalayas and the Alps…"
                aria-required="true"
                aria-describedby={
                  fieldErrors.biography ? "biography-error" : undefined
                }
                className={[
                  "w-full pl-8 pr-4 py-2.5 rounded-xl border text-sm resize-none",
                  "focus:outline-none focus:ring-2 focus:ring-ink/20 focus:border-ink",
                  "transition-all duration-[var(--duration-responsive)]",
                  "placeholder:text-muted-slate",
                  fieldErrors.biography
                    ? "border-red-300 bg-red-50"
                    : "border-gray-200 bg-white",
                ].join(" ")}
              />
            </div>
            {fieldErrors.biography && (
              <p id="biography-error" className="text-xs text-red-600" role="alert">
                {fieldErrors.biography}
              </p>
            )}
          </div>

          {/* ── Areas Covered ──────────────────────────────────────────────── */}
          <div className="space-y-2">
            <div className="flex items-end justify-between">
              <FieldLabel
                htmlFor="areas_covered"
                label="Areas Covered"
                description="Which regions, countries, or cities do you guide in?"
              />
              <CharCount current={areasCovered.length} max={1000} />
            </div>
            <div className="relative">
              <MapPin
                size={14}
                strokeWidth={2}
                className="absolute left-3 top-2.5 text-muted-slate pointer-events-none"
                aria-hidden="true"
              />
              <textarea
                id="areas_covered"
                name="areas_covered"
                value={areasCovered}
                onChange={(e) => setAreasCovered(e.target.value)}
                rows={3}
                maxLength={1000}
                placeholder="Nepal (Everest Base Camp, Langtang), Nepal (Annapurna Circuit), Switzerland (Swiss Alps)…"
                className={[
                  "w-full pl-8 pr-4 py-2.5 rounded-xl border text-sm resize-none",
                  "focus:outline-none focus:ring-2 focus:ring-ink/20 focus:border-ink",
                  "transition-all duration-[var(--duration-responsive)]",
                  "placeholder:text-muted-slate",
                  fieldErrors.areas_covered
                    ? "border-red-300 bg-red-50"
                    : "border-gray-200 bg-white",
                ].join(" ")}
              />
            </div>
            {fieldErrors.areas_covered && (
              <p className="text-xs text-red-600" role="alert">
                {fieldErrors.areas_covered}
              </p>
            )}
          </div>

          {/* ── Languages ──────────────────────────────────────────────────── */}
          <div className="space-y-2">
            <FieldLabel
              htmlFor="languages"
              label="Languages Spoken"
              description="List the languages you can guide in, separated by commas."
            />
            <div className="relative">
              <Globe
                size={14}
                strokeWidth={2}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-slate pointer-events-none"
                aria-hidden="true"
              />
              <input
                id="languages"
                name="languages"
                type="text"
                value={languages}
                onChange={(e) => setLanguages(e.target.value)}
                maxLength={500}
                placeholder="English, Hindi, Japanese, French…"
                className={[
                  "w-full pl-8 pr-4 py-2.5 rounded-xl border text-sm",
                  "focus:outline-none focus:ring-2 focus:ring-ink/20 focus:border-ink",
                  "transition-all duration-[var(--duration-responsive)]",
                  "placeholder:text-muted-slate",
                  fieldErrors.languages
                    ? "border-red-300 bg-red-50"
                    : "border-gray-200 bg-white",
                ].join(" ")}
              />
            </div>
            {fieldErrors.languages && (
              <p className="text-xs text-red-600" role="alert">
                {fieldErrors.languages}
              </p>
            )}
          </div>

          {/* ── Experience Years ────────────────────────────────────────────── */}
          <div className="space-y-2">
            <FieldLabel
              htmlFor="experience_years"
              label="Years of Experience"
              description="How many years have you been guiding professionally? (0–80)"
            />
            <div className="relative max-w-xs">
              <Briefcase
                size={14}
                strokeWidth={2}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-slate pointer-events-none"
                aria-hidden="true"
              />
              <input
                id="experience_years"
                name="experience_years"
                type="number"
                value={experienceYears}
                onChange={(e) => setExperienceYears(e.target.value)}
                min={0}
                max={80}
                placeholder="e.g. 5"
                className={[
                  "w-full pl-8 pr-4 py-2.5 rounded-xl border text-sm",
                  "focus:outline-none focus:ring-2 focus:ring-ink/20 focus:border-ink",
                  "transition-all duration-[var(--duration-responsive)]",
                  "placeholder:text-muted-slate",
                  fieldErrors.experience_years
                    ? "border-red-300 bg-red-50"
                    : "border-gray-200 bg-white",
                ].join(" ")}
              />
            </div>
            {fieldErrors.experience_years && (
              <p className="text-xs text-red-600" role="alert">
                {fieldErrors.experience_years}
              </p>
            )}
          </div>

          {/* ── Certifications ─────────────────────────────────────────────── */}
          <div className="space-y-2">
            <div className="flex items-end justify-between">
              <FieldLabel
                htmlFor="certifications"
                label="Certifications & Qualifications"
                description="List any relevant certifications, licenses, or qualifications."
              />
              <CharCount current={certifications.length} max={1000} />
            </div>
            <div className="relative">
              <Award
                size={14}
                strokeWidth={2}
                className="absolute left-3 top-3 text-muted-slate pointer-events-none"
                aria-hidden="true"
              />
              <textarea
                id="certifications"
                name="certifications"
                value={certifications}
                onChange={(e) => setCertifications(e.target.value)}
                rows={3}
                maxLength={1000}
                placeholder="IFMGA Mountain Guide Certification, Wilderness First Responder, PADI Divemaster…"
                className={[
                  "w-full pl-8 pr-4 py-2.5 rounded-xl border text-sm resize-none",
                  "focus:outline-none focus:ring-2 focus:ring-ink/20 focus:border-ink",
                  "transition-all duration-[var(--duration-responsive)]",
                  "placeholder:text-muted-slate",
                  fieldErrors.certifications
                    ? "border-red-300 bg-red-50"
                    : "border-gray-200 bg-white",
                ].join(" ")}
              />
            </div>
            {fieldErrors.certifications && (
              <p className="text-xs text-red-600" role="alert">
                {fieldErrors.certifications}
              </p>
            )}
          </div>

          {/* ── Identity Document URL ───────────────────────────────────────── */}
          <div className="space-y-2">
            <FieldLabel
              htmlFor="identity_document_url"
              label="Identity Document URL"
              description="Upload your identity document to MinIO storage first, then paste the resulting URL here for KYC verification."
            />
            <div className="relative">
              <LinkIcon
                size={14}
                strokeWidth={2}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-slate pointer-events-none"
                aria-hidden="true"
              />
              <input
                id="identity_document_url"
                name="identity_document_url"
                type="url"
                value={identityDocumentUrl}
                onChange={(e) => setIdentityDocumentUrl(e.target.value)}
                maxLength={500}
                placeholder="https://storage.ontdekker.com/kyc/document.pdf"
                className={[
                  "w-full pl-8 pr-4 py-2.5 rounded-xl border text-sm",
                  "focus:outline-none focus:ring-2 focus:ring-ink/20 focus:border-ink",
                  "transition-all duration-[var(--duration-responsive)]",
                  "placeholder:text-muted-slate",
                  fieldErrors.identity_document_url
                    ? "border-red-300 bg-red-50"
                    : "border-gray-200 bg-white",
                ].join(" ")}
              />
            </div>
            {fieldErrors.identity_document_url && (
              <p className="text-xs text-red-600" role="alert">
                {fieldErrors.identity_document_url}
              </p>
            )}
          </div>

          {/* ── Submit actions ──────────────────────────────────────────────── */}
          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className={[
                "inline-flex items-center justify-center gap-2",
                "px-6 py-2.5 rounded-xl bg-ink text-white text-sm font-medium",
                "hover:bg-ink/90 transition-colors",
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
                "disabled:opacity-60 disabled:cursor-not-allowed",
              ].join(" ")}
              aria-label="Submit guide application"
            >
              {isSubmitting ? (
                <>
                  <Loader2
                    size={15}
                    strokeWidth={2}
                    className="animate-spin"
                    aria-hidden="true"
                  />
                  {formState === "saving"
                    ? "Saving draft…"
                    : "Submitting…"}
                </>
              ) : (
                "Submit Application"
              )}
            </button>

            <button
              type="button"
              onClick={() => router.back()}
              disabled={isSubmitting}
              className="px-4 py-2.5 rounded-xl border border-gray-200 text-sm text-charcoal hover:bg-gray-50 transition-colors disabled:opacity-60"
            >
              Cancel
            </button>
          </div>

          {/* Required fields note */}
          <p className="text-[11px] text-muted-slate">
            <span className="text-red-500 mr-1">*</span>
            Required fields
          </p>
        </div>
      </form>
    </motion.div>
  );
}
