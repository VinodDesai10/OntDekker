"use client";

/**
 * OntDekker GuidePortfolioView
 *
 * Full guide profile page. Navigated to from GuidesView via
 * router.push(`/guides/${guide.id}`).
 *
 * Sections:
 *   1. Cover image + avatar + name + verification badge
 *   2. Bio, locations, languages, specializations, availability, years experience, price
 *   3. Rating summary
 *   4. Contact CTA
 *
 * All data fetched from the guide-service API — no hardcoded fallback data.
 */

import React, { useState } from "react";
import useSWR from "swr";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Bookmark,
  Star,
  MapPin,
  Languages,
  Wifi,
  WifiOff,
  Clock,
  ShieldCheck,
  Tag,
  DollarSign,
  Send,
  AlertCircle,
} from "lucide-react";

import Avatar from "@/components/feedback/Avatar";
import Button from "@/components/feedback/Button";
import { VerificationBadge } from "@/components/feedback/Badge";

import { swrFetcher, guideKeys } from "@/services/cache";
import { bookmarkGuide, unbookmarkGuide } from "@/services/guideApi";

import { useRouter, useParams } from "next/navigation";
import { useAppState } from "@/contexts/AppStateProvider";
import { useToast } from "@/hooks/useToast";

import type {
  GuideProfile,
  GuideRatingSummary,
  GuideReview,
  GuideReviewListResponse,
  ApiResponse,
} from "@/types";

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function ProfileSkeleton() {
  return (
    <div className="animate-pulse pb-20" aria-busy="true" aria-label="Loading guide profile">
      {/* Cover */}
      <div className="h-52 w-full bg-gray-100" />
      <div className="container-main pt-4 space-y-4">
        {/* Avatar row */}
        <div className="flex items-end justify-between -mt-12">
          <div className="w-20 h-20 rounded-full bg-gray-200 ring-4 ring-white" />
          <div className="flex gap-2 pb-2">
            <div className="w-8 h-8 rounded-xl bg-gray-200" />
            <div className="w-28 h-8 rounded-xl bg-gray-200" />
          </div>
        </div>
        {/* Name */}
        <div className="space-y-2">
          <div className="h-6 w-40 rounded bg-gray-200" />
          <div className="h-4 w-60 rounded bg-gray-100" />
        </div>
        {/* Bio */}
        <div className="space-y-2">
          <div className="h-4 w-full rounded bg-gray-100" />
          <div className="h-4 w-3/4 rounded bg-gray-100" />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Not found state
// ---------------------------------------------------------------------------

function ProfileNotFound({ onBack }: { onBack: () => void }) {
  return (
    <div className="container-main py-20 flex flex-col items-center gap-4 text-center">
      <AlertCircle size={36} strokeWidth={1} className="text-gray-300" aria-hidden="true" />
      <div className="space-y-1">
        <p className="text-sm font-semibold text-ink">Guide not found.</p>
        <p className="text-xs text-muted-slate">
          This guide profile may have been removed or doesn&apos;t exist.
        </p>
      </div>
      <Button variant="outline" size="sm" icon={ArrowLeft} onClick={onBack}>
        Back to Guides
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Rating dimension bar
// ---------------------------------------------------------------------------

function RatingBar({ label, value }: { label: string; value: number | null }) {
  const pct = value != null ? Math.round((value / 5) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-charcoal w-28 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-amber-400 transition-all duration-500"
          style={{ width: `${pct}%` }}
          aria-hidden="true"
        />
      </div>
      <span className="text-xs font-mono text-muted-slate w-6 text-right">
        {value != null ? value.toFixed(1) : "—"}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Review Item
// ---------------------------------------------------------------------------

function ReviewItem({ review }: { review: GuideReview }) {
  // reviewer is optional — guide-service returns reviewer_id only.
  // When user-service integration is available, reviewer will be populated.
  const reviewerName = review.reviewer?.displayName ?? "Traveler";
  const reviewerAvatar = review.reviewer?.avatarUrl ?? undefined;

  return (
    <div className="space-y-2 py-4 border-b border-gray-100 last:border-0">
      <div className="flex items-center gap-2">
        <Avatar
          src={reviewerAvatar}
          alt={reviewerName}
          size="xs"
        />
        <span className="text-xs font-medium text-ink">{reviewerName}</span>
        <div className="flex items-center gap-0.5 ml-auto">
          {[1, 2, 3, 4, 5].map((s) => (
            <Star
              key={s}
              size={10}
              strokeWidth={2}
              fill={s <= review.ratingOverall ? "currentColor" : "none"}
              className={s <= review.ratingOverall ? "text-amber-400" : "text-gray-200"}
              aria-hidden="true"
            />
          ))}
        </div>
      </div>
      {review.comment && (
        <p className="text-xs text-charcoal leading-relaxed">{review.comment}</p>
      )}
      {review.wouldRecommend && (
        <p className="text-[10px] font-mono uppercase tracking-wider text-moss-green flex items-center gap-1">
          <ShieldCheck size={10} strokeWidth={2} aria-hidden="true" /> Would recommend
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// GuidePortfolioView
// ---------------------------------------------------------------------------

export default function GuidePortfolioView() {
  const router = useRouter();
  const params = useParams();
  const { state } = useAppState();
  const { showToast } = useToast();

  const guideId = (params.id as string) ?? "";
  const isBookmarked = state.savedGuides.some((g) => g.id === guideId);
  const [contactRequested, setContactRequested] = useState(false);

  // ── SWR data fetches ────────────────────────────────────────────────────────
  const { data: profileResponse, isLoading } = useSWR<ApiResponse<GuideProfile>>(
    guideId ? guideKeys.byId(guideId) : null,
    swrFetcher,
    { revalidateOnFocus: false },
  );

  const { data: ratingSummary } = useSWR<GuideRatingSummary>(
    guideId ? guideKeys.ratingSummary(guideId) : null,
    swrFetcher,
    { revalidateOnFocus: false },
  );

  const { data: reviewsData } = useSWR<GuideReviewListResponse>(
    guideId ? guideKeys.reviews(guideId) : null,
    swrFetcher,
    { revalidateOnFocus: false },
  );

  // ── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) return <ProfileSkeleton />;

  // ── Not found ──────────────────────────────────────────────────────────────
  const profile = profileResponse?.data;
  if (!profile) return <ProfileNotFound onBack={() => router.push("/guides")} />;

  // ── Derived state ──────────────────────────────────────────────────────────
  const isVerified = profile.verificationStatus === "VERIFIED";
  const availability = profile.availability;
  const isAvailable = availability?.status === "AVAILABLE";
  const reviews = reviewsData?.items ?? [];
  const specs = profile.specializations ?? [];

  // Display name: prefer profile.displayName, fall back to user record or placeholder.
  // guide-service currently returns display_name: null until user-service integration lands.
  const displayName =
    profile.displayName ??
    profile.user?.displayName ??
    "Guide Profile";
  const avatarSrc =
    profile.user?.avatarUrl ??
    profile.profileImageUrl ??
    undefined;

  async function handleBookmark() {
    try {
      if (isBookmarked) {
        await unbookmarkGuide(guideId);
        showToast("Bookmark removed.", "info");
      } else {
        await bookmarkGuide(guideId);
        showToast(`${displayName} bookmarked!`, "success");
      }
    } catch {
      showToast("Could not update bookmark. Please try again.", "error");
    }
  }

  function handleContact() {
    setContactRequested(true);
    showToast(
      `Contact request sent to ${displayName}. They will be notified.`,
      "success",
    );
  }

  return (
    <motion.div
      className="pb-20"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0, 0, 0.2, 1] }}
    >
      {/* ── Cover image ────────────────────────────────────────────────── */}
      <div className="relative h-52 w-full overflow-hidden bg-gray-100">
        {profile.coverImageUrl ? (
          <img
            src={profile.coverImageUrl}
            alt=""
            aria-hidden="true"
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-gray-100 to-gray-200" />
        )}

        {/* Back button */}
        <button
          type="button"
          aria-label="Go back"
          onClick={() => router.back()}
          className="
            absolute top-4 left-4
            flex items-center justify-center
            w-8 h-8 rounded-xl
            bg-white/80 backdrop-blur-sm text-ink
            hover:bg-white shadow-xs
            transition-all duration-[var(--duration-responsive)]
            focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink
          "
        >
          <ArrowLeft size={16} strokeWidth={2} aria-hidden="true" />
        </button>
      </div>

      <div className="container-main space-y-6 pt-0">
        {/* ── Avatar row ────────────────────────────────────────────────── */}
        <div className="flex items-end justify-between -mt-12">
          <Avatar
            src={avatarSrc}
            alt={displayName}
            size="xl"
            className="ring-4 ring-white shadow-sm"
          />
          <div className="flex items-center gap-2 pb-2">
            <Button
              variant="outline"
              size="sm"
              icon={Bookmark}
              iconOnly
              onClick={handleBookmark}
              aria-label={isBookmarked ? "Remove bookmark" : "Bookmark guide"}
              className={isBookmarked ? "text-amber-600 border-amber-200 bg-amber-50" : ""}
            />
            <Button
              variant={contactRequested ? "outline" : "primary"}
              size="sm"
              icon={Send}
              onClick={handleContact}
              className={contactRequested ? "border-green-200 bg-green-50 text-green-700" : ""}
            >
              {contactRequested ? "Request Sent" : "Contact Guide"}
            </Button>
          </div>
        </div>

        {/* ── Identity ──────────────────────────────────────────────────── */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold tracking-tight text-ink">{displayName}</h1>
            {isVerified && <VerificationBadge size="sm" />}
          </div>

          {/* Meta chips */}
          <div className="flex items-center gap-3 flex-wrap text-[10px] font-mono uppercase tracking-wider text-muted-slate">
            {profile.locations.slice(0, 2).map((loc) => (
              <span key={loc.id} className="flex items-center gap-1">
                <MapPin size={10} strokeWidth={2} aria-hidden="true" />
                {[loc.city, loc.country].filter(Boolean).join(", ")}
              </span>
            ))}
            {profile.languages.slice(0, 3).map((lang) => (
              <span key={lang.id} className="flex items-center gap-1">
                <Languages size={10} strokeWidth={2} aria-hidden="true" />
                {lang.language}
              </span>
            ))}
            {profile.yearsExperience != null && (
              <span className="flex items-center gap-1">
                <Clock size={10} strokeWidth={2} aria-hidden="true" />
                {profile.yearsExperience} yrs exp
              </span>
            )}
            {profile.pricePerDay != null && (
              <span className="flex items-center gap-1 text-ink font-semibold">
                <DollarSign size={10} strokeWidth={2} aria-hidden="true" />
                {profile.pricePerDay}/day
              </span>
            )}
            {availability && (
              <span
                className={`flex items-center gap-1 ${
                  isAvailable ? "text-moss-green font-semibold" : "text-muted-slate"
                }`}
              >
                {isAvailable ? (
                  <Wifi size={10} strokeWidth={2} aria-hidden="true" />
                ) : (
                  <WifiOff size={10} strokeWidth={2} aria-hidden="true" />
                )}
                {availability.status.charAt(0) + availability.status.slice(1).toLowerCase()}
              </span>
            )}
          </div>
        </div>

        {/* ── Specializations ───────────────────────────────────────────── */}
        {specs.length > 0 && (
          <div className="flex flex-wrap gap-2" aria-label="Specializations">
            {specs.map((s) => (
              <span
                key={s.id}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-gray-100 text-xs font-medium text-charcoal"
              >
                <Tag size={10} strokeWidth={2} aria-hidden="true" />
                {s.category}
              </span>
            ))}
          </div>
        )}

        {/* ── Bio ───────────────────────────────────────────────────────── */}
        {profile.bio && (
          <p className="text-sm text-charcoal leading-relaxed max-w-2xl">{profile.bio}</p>
        )}

        {/* ── Rating summary ────────────────────────────────────────────── */}
        {(profile.rating != null || ratingSummary) && (
          <section aria-label="Rating summary" className="space-y-3">
            <h2 className="text-sm font-semibold text-ink">Rating &amp; Reviews</h2>
            <div className="bg-white border border-gray-100 rounded-3xl p-5 space-y-4 shadow-2xs">
              <div className="flex items-center gap-3">
                <Star
                  size={18}
                  strokeWidth={2}
                  fill="currentColor"
                  className="text-amber-400"
                  aria-hidden="true"
                />
                <span className="text-2xl font-bold font-mono text-ink">
                  {(ratingSummary?.averageOverall ?? profile.rating)?.toFixed(1) ?? "—"}
                </span>
                <span className="text-sm text-muted-slate">
                  from {ratingSummary?.reviewCount ?? profile.reviewCount} reviews
                </span>
                {ratingSummary?.wouldRecommendPercentage != null && (
                  <span className="ml-auto text-xs text-moss-green font-semibold">
                    {Math.round(ratingSummary.wouldRecommendPercentage)}% recommend
                  </span>
                )}
              </div>

              {ratingSummary && (
                <div className="space-y-2">
                  <RatingBar label="Knowledge" value={ratingSummary.averageKnowledge} />
                  <RatingBar label="Friendliness" value={ratingSummary.averageFriendliness} />
                  <RatingBar label="Communication" value={ratingSummary.averageCommunication} />
                  <RatingBar label="Safety" value={ratingSummary.averageSafety} />
                  <RatingBar label="Professionalism" value={ratingSummary.averageProfessionalism} />
                </div>
              )}
            </div>
          </section>
        )}

        {/* ── Reviews list ──────────────────────────────────────────────── */}
        {reviews.length > 0 && (
          <section aria-label="Reviews" className="space-y-3">
            <h2 className="text-sm font-semibold text-ink">Recent Feedback</h2>
            <div className="bg-white border border-gray-100 rounded-3xl px-5 divide-y divide-gray-100 shadow-2xs">
              {reviews.map((review) => (
                <ReviewItem key={review.id} review={review} />
              ))}
            </div>
          </section>
        )}

        {/* ── All locations ─────────────────────────────────────────────── */}
        {profile.locations.length > 0 && (
          <section aria-label="Areas covered" className="space-y-3">
            <h2 className="text-sm font-semibold text-ink">Areas Covered</h2>
            <div className="flex flex-wrap gap-2">
              {profile.locations.map((loc) => (
                <span
                  key={loc.id}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-gray-200 bg-white text-xs text-charcoal"
                >
                  <MapPin size={10} strokeWidth={2} aria-hidden="true" />
                  {[loc.city, loc.region, loc.country].filter(Boolean).join(", ")}
                </span>
              ))}
            </div>
          </section>
        )}
      </div>
    </motion.div>
  );
}
