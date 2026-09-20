"use client";

/**
 * /users/[username]/following — Following Page
 *
 * Displays a paginated list of users that the given public profile is following.
 *
 * Resolution strategy:
 *   1. username (from URL) → getPublicProfile(username) → profile.id
 *   2. profile.id → getFollowing(profile.id, page, size)
 *
 * Both steps use the existing service layer only (no direct Axios calls).
 * profile.id is the user-service profile ID, which is exactly what
 * getFollowing() expects as its userId parameter.
 *
 * Rendering is delegated entirely to the existing FollowerList component.
 * No pagination logic is duplicated here.
 *
 * Does NOT expose private-profile data. Only PublicProfileResponse.id
 * and PublicProfileResponse.display_name/username are consumed by this page;
 * the following list itself contains only FollowerSummary items.
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, AlertTriangle, UserRound } from "lucide-react";
import { FollowerList } from "@/components/social/FollowerList";
import { getPublicProfile, getFollowing } from "@/services/users";
import { ApiError } from "@/services/api";

// ---------------------------------------------------------------------------
// Query key factories
// ---------------------------------------------------------------------------

const profileKey = (username: string) =>
  ["users", "public", username] as const;

const followingKey = (userId: string, page: number, size: number) =>
  ["users", userId, "following", { page, size }] as const;

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

const PAGE_SIZE = 20;

export default function FollowingPage() {
  const params = useParams();
  const username =
    typeof params.username === "string" ? params.username : "";

  const [page, setPage] = useState(1);

  // Step 1 — resolve profile.id from username
  const {
    data: profile,
    isLoading: profileLoading,
    isError: profileIsError,
    error: profileError,
  } = useQuery({
    queryKey: profileKey(username),
    queryFn: () => getPublicProfile(username),
    enabled: username.length > 0,
    staleTime: 60_000,
    retry: (failureCount, err) => {
      if (err instanceof ApiError && err.status === 404) return false;
      return failureCount < 2;
    },
  });

  // Step 2 — fetch following list once profile.id is known
  const {
    data: followingData,
    isLoading: followingLoading,
    isError: followingIsError,
    error: followingError,
  } = useQuery({
    queryKey: followingKey(profile?.id ?? "", page, PAGE_SIZE),
    queryFn: () => getFollowing(profile!.id, page, PAGE_SIZE),
    enabled: !!profile?.id,
    staleTime: 30_000,
  });

  // ---------------------------------------------------------------------------
  // Profile resolution error (404 or network)
  // ---------------------------------------------------------------------------

  if (profileIsError) {
    const is404 =
      profileError instanceof ApiError && profileError.status === 404;
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        {is404 ? (
          <>
            <UserRound className="size-10 text-[#EAE7DF]" aria-hidden />
            <p className="text-sm font-medium text-[#111111]">User not found</p>
            <p className="text-xs text-gray-400">
              No account exists for &ldquo;@{username}&rdquo;.
            </p>
          </>
        ) : (
          <>
            <AlertTriangle className="size-7 text-[#F59E0B]" aria-hidden />
            <p className="text-sm text-gray-500">
              {profileError instanceof ApiError
                ? profileError.message
                : "Could not load this profile. Please try again."}
            </p>
          </>
        )}
        <Link
          href={`/users/${username}`}
          className="mt-2 text-xs text-gray-400 underline-offset-4 hover:underline"
        >
          ← Back to profile
        </Link>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Main layout
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-5">
      {/* Back navigation */}
      <Link
        href={`/users/${username}`}
        className="inline-flex items-center gap-1 text-sm text-gray-500 underline-offset-4 hover:underline"
        aria-label={`Back to ${username}'s profile`}
      >
        <ChevronLeft className="size-4" aria-hidden />
        {profile?.display_name ?? username}
      </Link>

      {/* Heading */}
      <h1 className="text-lg font-bold text-[#111111]">Following</h1>

      {/* Delegate all list rendering, loading, error, and empty states */}
      <FollowerList
        title="Following"
        data={followingData}
        isLoading={profileLoading || followingLoading}
        error={followingIsError ? followingError : null}
        page={page}
        onPageChange={setPage}
      />
    </div>
  );
}
