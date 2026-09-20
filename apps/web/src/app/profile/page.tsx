"use client";

/**
 * /profile — My Profile Page
 *
 * Fetches the authenticated user's private profile via GET /users/me.
 * Displays all fields from PrivateProfileResponse.
 * Handles lazy profile creation (first-time users get a profile auto-created).
 *
 * Sections:
 *   - Cover image + avatar (with upload triggers)
 *   - Display name, username, bio, location
 *   - Interests list
 *   - Travel preferences summary
 *   - Reputation/badge summary
 *   - My Posts (CP-POST-3)
 *
 * Uses TanStack Query for data fetching and cache invalidation.
 * Avatar and Cover uploads update the profile cache on success.
 */

import Link from "next/link";
import Image from "next/image";
import { useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Camera,
  MapPin,
  Pencil,
  Star,
  Award,
  Loader2,
  AlertTriangle,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  getMyProfile,
  uploadAvatar,
  uploadCover,
  UPLOAD_ACCEPTED_MIME_TYPES,
  UPLOAD_MAX_BYTES,
  type PrivateProfileResponse,
} from "@/services/users";
import { getMyPosts } from "@/services/feedApi";
import { feedKeys } from "@/services/cache/feedCache";
import { ApiError } from "@/services/api";
import { cn } from "@/lib/utils";
import type { RawPost, RawPostListResponse } from "@/views/Feed/types";

/** Stable TanStack Query key for the current user's private profile. */
export const MY_PROFILE_KEY = ["profile", "me"] as const;

const ACCEPTED_TYPES = UPLOAD_ACCEPTED_MIME_TYPES.join(",");

// ---------------------------------------------------------------------------
// Upload image button — reusable for avatar and cover
// ---------------------------------------------------------------------------

interface ImageUploadTriggerProps {
  label: string;
  accept: string;
  loading: boolean;
  onFile: (file: File) => void;
  className?: string;
  children: React.ReactNode;
}

function ImageUploadTrigger({
  label,
  accept,
  loading,
  onFile,
  className,
  children,
}: ImageUploadTriggerProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) onFile(file);
    // Reset input so re-selecting the same file triggers onChange
    e.target.value = "";
  }

  return (
    <button
      type="button"
      aria-label={label}
      disabled={loading}
      onClick={() => inputRef.current?.click()}
      className={cn(
        "flex items-center justify-center transition disabled:opacity-50",
        className
      )}
    >
      {loading ? (
        <Loader2 className="size-4 animate-spin" aria-hidden />
      ) : (
        children
      )}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="sr-only"
        aria-hidden
        tabIndex={-1}
        onChange={handleChange}
      />
    </button>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function ProfileSkeleton() {
  return (
    <div aria-label="Loading profile" aria-live="polite">
      <div className="h-36 animate-pulse rounded-xl bg-[#EAE7DF]" />
      <div className="mt-[-2.5rem] ml-4 size-20 animate-pulse rounded-full border-4 border-white bg-[#EAE7DF]" />
      <div className="mt-4 space-y-2 px-1">
        <div className="h-5 w-40 animate-pulse rounded bg-[#EAE7DF]" />
        <div className="h-4 w-28 animate-pulse rounded bg-[#EAE7DF]" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

function ProfileError({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center gap-3 py-16 text-center">
      <AlertTriangle className="size-8 text-[#F59E0B]" aria-hidden />
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// My Posts Section
// ---------------------------------------------------------------------------

/** A single post summary row displayed on the Profile page */
function ProfilePostCard({ post }: { post: RawPost }) {
  const formattedDate = new Date(post.createdAt).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <article className="rounded-xl border border-[#EAE7DF] bg-white p-4 space-y-2 hover:border-gray-300 transition-colors">
      {/* Cover image */}
      {post.coverImageUrl && (
        <div className="w-full h-32 overflow-hidden rounded-lg bg-[#EAE7DF]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={post.coverImageUrl}
            alt={post.title}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        </div>
      )}

      {/* Title */}
      <h3 className="text-sm font-semibold text-[#111111] leading-snug line-clamp-2">
        {post.title}
      </h3>

      {/* Location */}
      {post.location && (
        <p className="flex items-center gap-1 text-[11px] font-mono uppercase tracking-wider text-gray-400">
          <MapPin className="size-3" aria-hidden />
          {post.location}
        </p>
      )}

      {/* Tags */}
      {post.tagList && post.tagList.length > 0 && (
        <div className="flex flex-wrap gap-1" aria-label="Post tags">
          {post.tagList.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="rounded-full border border-[#EAE7DF] bg-[#FBF9F4] px-2 py-0.5 text-[10px] text-gray-600"
            >
              {tag}
            </span>
          ))}
          {post.tagList.length > 3 && (
            <span className="rounded-full border border-[#EAE7DF] bg-[#FBF9F4] px-2 py-0.5 text-[10px] text-gray-600">
              +{post.tagList.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Meta row */}
      <div className="flex items-center justify-between text-[11px] text-gray-400 pt-1">
        <div className="flex items-center gap-3">
          <span>
            {post.likeCount.toLocaleString()} {post.likeCount === 1 ? "like" : "likes"}
          </span>
          <span>
            {post.commentCount.toLocaleString()} {post.commentCount === 1 ? "comment" : "comments"}
          </span>
        </div>
        <span>{formattedDate}</span>
      </div>

      {/* Visibility badge */}
      <div>
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
            post.visibility === "PUBLIC"
              ? "bg-green-50 text-green-700 border border-green-200"
              : post.visibility === "COMMUNITY"
                ? "bg-blue-50 text-blue-700 border border-blue-200"
                : "bg-gray-50 text-gray-600 border border-gray-200"
          )}
        >
          {post.visibility === "PUBLIC"
            ? "Global"
            : post.visibility === "COMMUNITY"
              ? "Community"
              : "Private"}
        </span>
      </div>
    </article>
  );
}

/** Posts section loading skeleton */
function PostsSkeleton() {
  return (
    <div className="space-y-3" aria-label="Loading posts">
      {Array.from({ length: 2 }).map((_, i) => (
        <div key={i} className="rounded-xl border border-[#EAE7DF] bg-white p-4 space-y-2">
          <div className="h-4 w-3/4 animate-pulse rounded bg-[#EAE7DF]" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-[#EAE7DF]" />
          <div className="h-3 w-1/4 animate-pulse rounded bg-[#EAE7DF]" />
        </div>
      ))}
    </div>
  );
}

/** My Posts section — fetches the authenticated user's own posts */
function MyPostsSection() {
  const {
    data,
    isLoading,
    isError,
  } = useQuery({
    queryKey: feedKeys.myPosts({ limit: 20, offset: 0 }),
    queryFn: () => getMyPosts({ limit: 20, offset: 0 }),
    staleTime: 30_000,
    retry: false,
  });

  return (
    <section aria-labelledby="my-posts-heading">
      <div className="mb-3 flex items-center gap-2">
        <FileText className="size-4 text-[#111111]" aria-hidden />
        <h2
          id="my-posts-heading"
          className="text-sm font-semibold text-[#111111]"
        >
          My Posts
        </h2>
        {data && (
          <span className="ml-auto text-xs text-gray-400">
            {data.total} {data.total === 1 ? "post" : "posts"}
          </span>
        )}
      </div>

      {isLoading && <PostsSkeleton />}

      {isError && (
        <p className="text-sm text-gray-400 py-4 text-center">
          Could not load posts. Please refresh.
        </p>
      )}

      {!isLoading && !isError && data && data.posts.length === 0 && (
        <div className="rounded-xl border border-dashed border-[#EAE7DF] bg-[#FBF9F4] p-8 text-center space-y-2">
          <FileText className="size-8 mx-auto text-gray-300" aria-hidden />
          <p className="text-sm font-medium text-gray-500">No posts yet.</p>
          <p className="text-xs text-gray-400">
            Share your first travel story with the community.
          </p>
          <Link
            href="/feed"
            className="inline-block mt-2 text-xs text-[#111111] underline underline-offset-4 hover:text-gray-600"
          >
            Go to Feed to create a story
          </Link>
        </div>
      )}

      {!isLoading && !isError && data && data.posts.length > 0 && (
        <div className="space-y-3">
          {data.posts.map((post) => (
            <ProfilePostCard key={post.id} post={post} />
          ))}
          {data.hasMore && (
            <p className="text-center text-xs text-gray-400 pt-1">
              Showing {data.posts.length} of {data.total} posts.{" "}
              <Link href="/feed" className="underline underline-offset-4 hover:text-gray-600">
                See all in Feed
              </Link>
            </p>
          )}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Main profile view
// ---------------------------------------------------------------------------

function ProfileView({ profile }: { profile: PrivateProfileResponse }) {
  const queryClient = useQueryClient();

  // ----- Avatar upload mutation -----
  const avatarMutation = useMutation({
    mutationFn: (file: File) => uploadAvatar(file),
    onSuccess: (data) => {
      // Update the cache with the freshly returned presigned URL.
      // The backend now also returns a presigned URL on GET /users/me, so
      // after the next page load the URL will be regenerated correctly.
      queryClient.setQueryData<PrivateProfileResponse>(MY_PROFILE_KEY, (old) =>
        old ? { ...old, avatar_url: data.presigned_url } : old
      );
    },
  });

  // ----- Cover upload mutation -----
  const coverMutation = useMutation({
    mutationFn: (file: File) => uploadCover(file),
    onSuccess: (data) => {
      queryClient.setQueryData<PrivateProfileResponse>(MY_PROFILE_KEY, (old) =>
        old ? { ...old, cover_url: data.presigned_url } : old
      );
    },
  });

  function handleAvatarFile(file: File) {
    if (file.size > UPLOAD_MAX_BYTES) {
      alert("Image must be under 5 MB.");
      return;
    }
    if (!UPLOAD_ACCEPTED_MIME_TYPES.includes(file.type as typeof UPLOAD_ACCEPTED_MIME_TYPES[number])) {
      alert("Accepted formats: JPEG, PNG, WebP.");
      return;
    }
    avatarMutation.mutate(file);
  }

  function handleCoverFile(file: File) {
    if (file.size > UPLOAD_MAX_BYTES) {
      alert("Image must be under 5 MB.");
      return;
    }
    if (!UPLOAD_ACCEPTED_MIME_TYPES.includes(file.type as typeof UPLOAD_ACCEPTED_MIME_TYPES[number])) {
      alert("Accepted formats: JPEG, PNG, WebP.");
      return;
    }
    coverMutation.mutate(file);
  }

  const uploadError =
    (avatarMutation.error instanceof ApiError
      ? avatarMutation.error.message
      : avatarMutation.error
        ? "Avatar upload failed."
        : null) ??
    (coverMutation.error instanceof ApiError
      ? coverMutation.error.message
      : coverMutation.error
        ? "Cover upload failed."
        : null);

  return (
    <div className="space-y-6">
      {/* Upload error */}
      {uploadError && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {uploadError}
        </div>
      )}

      {/* Cover + avatar header */}
      <div className="relative">
        {/* Cover image */}
        <div className="group relative h-36 overflow-hidden rounded-xl bg-[#EAE7DF]">
          {profile.cover_url ? (
            <Image
              src={profile.cover_url}
              alt="Cover image"
              fill
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 768px"
            />
          ) : (
            <div className="h-full w-full bg-gradient-to-br from-[#EAE7DF] to-[#d5d0c8]" />
          )}
          {/* Cover upload overlay */}
          <div className="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition group-hover:bg-black/20 group-hover:opacity-100">
            <ImageUploadTrigger
              label="Change cover image"
              accept={ACCEPTED_TYPES}
              loading={coverMutation.isPending}
              onFile={handleCoverFile}
              className="rounded-full bg-black/50 p-2 text-white hover:bg-black/70"
            >
              <Camera className="size-5" aria-hidden />
            </ImageUploadTrigger>
          </div>
        </div>

        {/* Avatar */}
        <div className="absolute -bottom-10 left-4">
          <div className="group relative size-20 overflow-hidden rounded-full border-4 border-white bg-[#EAE7DF]">
            {profile.avatar_url ? (
              <Image
                src={profile.avatar_url}
                alt={`${profile.display_name} avatar`}
                fill
                className="object-cover"
                sizes="80px"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-2xl font-bold text-gray-400">
                {profile.display_name?.charAt(0)?.toUpperCase() ?? "?"}
              </div>
            )}
            {/* Avatar upload overlay */}
            <div className="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition group-hover:bg-black/30 group-hover:opacity-100">
              <ImageUploadTrigger
                label="Change avatar"
                accept={ACCEPTED_TYPES}
                loading={avatarMutation.isPending}
                onFile={handleAvatarFile}
                className="rounded-full p-1.5 text-white"
              >
                <Camera className="size-4" aria-hidden />
              </ImageUploadTrigger>
            </div>
          </div>
        </div>
      </div>

      {/* Identity row */}
      <div className="flex items-start justify-between pt-10">
        <div className="space-y-0.5">
          <h1 className="text-xl font-bold text-[#111111]">
            {profile.display_name}
          </h1>
          <p className="text-sm text-gray-500">@{profile.username}</p>
          {(profile.city || profile.country) && (
            <p className="flex items-center gap-1 text-sm text-gray-400">
              <MapPin className="size-3.5" aria-hidden />
              {[profile.city, profile.country].filter(Boolean).join(", ")}
            </p>
          )}
        </div>
        <Link href="/profile/edit">
          <Button variant="outline" size="sm">
            <Pencil className="size-3.5" aria-hidden />
            <span className="ml-1.5">Edit</span>
          </Button>
        </Link>
      </div>

      {/* Bio */}
      {profile.bio && (
        <p className="text-sm leading-relaxed text-gray-600">{profile.bio}</p>
      )}

      {/* Divider */}
      <hr className="border-[#EAE7DF]" />

      {/* Interests */}
      <section aria-labelledby="interests-heading">
        <div className="mb-3 flex items-center justify-between">
          <h2
            id="interests-heading"
            className="text-sm font-semibold text-[#111111]"
          >
            Interests
          </h2>
          <Link
            href="/profile/interests"
            className="text-xs text-gray-400 underline-offset-4 hover:underline"
          >
            Edit
          </Link>
        </div>
        {profile.interests.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {profile.interests.map(({ interest }) => (
              <span
                key={interest}
                className="rounded-full border border-[#EAE7DF] bg-white px-3 py-1 text-xs text-[#111111]"
              >
                {interest}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">
            No interests added yet.{" "}
            <Link
              href="/profile/interests"
              className="underline-offset-4 hover:underline"
            >
              Add some
            </Link>
          </p>
        )}
      </section>

      {/* Travel preferences */}
      <section aria-labelledby="prefs-heading">
        <div className="mb-3 flex items-center justify-between">
          <h2
            id="prefs-heading"
            className="text-sm font-semibold text-[#111111]"
          >
            Travel preferences
          </h2>
          <Link
            href="/profile/preferences"
            className="text-xs text-gray-400 underline-offset-4 hover:underline"
          >
            Edit
          </Link>
        </div>
        {profile.preferences ? (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            {profile.preferences.travel_style && (
              <>
                <dt className="text-gray-400">Style</dt>
                <dd className="text-[#111111]">
                  {profile.preferences.travel_style}
                </dd>
              </>
            )}
            {profile.preferences.budget && (
              <>
                <dt className="text-gray-400">Budget</dt>
                <dd className="text-[#111111]">{profile.preferences.budget}</dd>
              </>
            )}
            {profile.preferences.adventure_level && (
              <>
                <dt className="text-gray-400">Adventure</dt>
                <dd className="text-[#111111]">
                  {profile.preferences.adventure_level}
                </dd>
              </>
            )}
            {profile.preferences.languages &&
              profile.preferences.languages.length > 0 && (
                <>
                  <dt className="text-gray-400">Languages</dt>
                  <dd className="text-[#111111]">
                    {profile.preferences.languages.join(", ")}
                  </dd>
                </>
              )}
          </dl>
        ) : (
          <p className="text-sm text-gray-400">
            No preferences set yet.{" "}
            <Link
              href="/profile/preferences"
              className="underline-offset-4 hover:underline"
            >
              Set preferences
            </Link>
          </p>
        )}
      </section>

      {/* Reputation summary — only if data exists */}
      {profile.reputation && (
        <>
          <hr className="border-[#EAE7DF]" />
          <section aria-labelledby="rep-heading">
            <h2
              id="rep-heading"
              className="mb-3 text-sm font-semibold text-[#111111]"
            >
              Reputation
            </h2>
            <div className="grid grid-cols-3 gap-3">
              {[
                {
                  label: "Explorer",
                  value: profile.reputation.explorer_score,
                  icon: <Star className="size-4 text-[#F59E0B]" />,
                },
                {
                  label: "Community",
                  value: profile.reputation.community_score,
                  icon: <Star className="size-4 text-[#F59E0B]" />,
                },
                {
                  label: "Review",
                  value: profile.reputation.review_score,
                  icon: <Star className="size-4 text-[#F59E0B]" />,
                },
              ].map(({ label, value, icon }) => (
                <div
                  key={label}
                  className="flex flex-col items-center rounded-lg border border-[#EAE7DF] bg-white p-3 text-center"
                >
                  {icon}
                  <span className="mt-1 text-base font-bold text-[#111111]">
                    {value}
                  </span>
                  <span className="text-xs text-gray-400">{label}</span>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {/* Badges — only if earned */}
      {profile.badges.length > 0 && (
        <>
          <hr className="border-[#EAE7DF]" />
          <section aria-labelledby="badges-heading">
            <h2
              id="badges-heading"
              className="mb-3 text-sm font-semibold text-[#111111]"
            >
              Badges
            </h2>
            <div className="flex flex-wrap gap-2">
              {profile.badges.map((badge) => (
                <span
                  key={badge.id}
                  title={badge.badge_name}
                  className="flex items-center gap-1.5 rounded-full border border-[#EAE7DF] bg-white px-3 py-1 text-xs text-[#111111]"
                >
                  <Award className="size-3.5 text-[#F59E0B]" aria-hidden />
                  {badge.badge_name}
                </span>
              ))}
            </div>
          </section>
        </>
      )}

      {/* My Posts */}
      <hr className="border-[#EAE7DF]" />
      <MyPostsSection />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page export
// ---------------------------------------------------------------------------

export default function ProfilePage() {
  const {
    data: profile,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: MY_PROFILE_KEY,
    queryFn: getMyProfile,
    staleTime: 60_000,
    retry: false,
  });

  if (isLoading) return <ProfileSkeleton />;

  if (isError || !profile) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Could not load your profile. Please refresh the page.";
    return <ProfileError message={message} />;
  }

  return <ProfileView profile={profile} />;
}
