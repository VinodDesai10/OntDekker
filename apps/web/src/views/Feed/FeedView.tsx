"use client";

/**
 * OntDekker FeedView — Travel Social Media Feed
 *
 * Full-featured modern travel feed featuring:
 *   - Create Story via real POST /feed/stories API (Task 1)
 *   - Edit Story — owner only via PUT /feed/stories/{id} (Task 2)
 *   - Delete Story — owner only with confirmation (Task 3)
 *   - Like/Unlike with optimistic UI + rollback (Task 4)
 *   - Bookmark/Unbookmark with optimistic UI (Task 5)
 *   - Comments: load, create, edit own, delete own (Task 6)
 *   - Feed Toggle (All Stories vs Communities)
 *   - Live search across title, location, tags
 *   - Right Sidebar: Trending Communities, Upcoming Expeditions
 *   - Real author identity resolved via batch-profiles-by-auth (CP-FEED-IDENTITY-1)
 */

import React, { useState, useMemo, useEffect } from "react";
import useSWR from "swr";
import { AnimatePresence } from "motion/react";
import {
  Compass,
  Users,
  Sparkles,
  Calendar,
  MapPin,
  Clock,
} from "lucide-react";
import { useRouter } from "next/navigation";

import Search from "@/components/navigation/Search";
import {
  swrFetcherWithParams,
  feedKeys,
  communityKeys,
  expeditionKeys,
} from "@/services/cache";
import { createPost, updatePost, deletePost } from "@/services/feedApi";
import { joinCommunity, getMyMemberships } from "@/services/communityApi";
import { batchProfilesByAuth, type ProfileMap } from "@/services/users";
import { useToast } from "@/hooks/useToast";
import { useAuth } from "@/contexts/AuthContext";
import { queryClient } from "@/lib/query";
import type { CommunitySummary, ExpeditionSummary, CreatePostRequest, UpdatePostRequest } from "@/types";

import { StoryComposer } from "./StoryComposer";
import { PostCard } from "./PostCard";
import PostCardSkeleton from "./PostCardSkeleton";
import type { RawPost, RawPostListResponse } from "./types";

// ---------------------------------------------------------------------------
// FeedView Component
// ---------------------------------------------------------------------------

export default function FeedView() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  // Search & Tab state
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "community">("all");

  // Interactive sidebar state
  const [joinedCommunities, setJoinedCommunities] = useState<Set<string>>(new Set());

  // Author profile resolution — keyed by auth_user_id (= post.authorId)
  const [authorProfiles, setAuthorProfiles] = useState<ProfileMap>({});

  // ── SWR: Feed Posts ──────────────────────────────────────────────────────
  const { data, mutate, isLoading } = useSWR<RawPostListResponse>(
    feedKeys.list({ limit: 18 }),
    ([url, params]: [string, Record<string, unknown>]) =>
      swrFetcherWithParams(url, params),
    { revalidateOnFocus: false }
  );

  // ── SWR: Trending Communities ────────────────────────────────────────────
  const { data: communitiesData } = useSWR<{ items: CommunitySummary[] }>(
    communityKeys.list({ page_size: 3 }),
    ([url, params]: [string, Record<string, unknown>]) =>
      swrFetcherWithParams(url, params),
    { revalidateOnFocus: false }
  );

  // ── SWR: User's Memberships (for the post composer community selector) ───
  // Only fetch when the user is authenticated.  We pass the raw communities
  // list key with a high limit and filter client-side to isMember === true.
  const { data: membershipsData } = useSWR<{ communities: CommunitySummary[]; total: number; limit: number; offset: number; hasMore: boolean }>(
    user
      ? communityKeys.list({ limit: 200, offset: 0 })
      : null,
    ([url, params]: [string, Record<string, unknown>]) =>
      swrFetcherWithParams(url, params),
    { revalidateOnFocus: false }
  );

  // ── SWR: Upcoming Expeditions ────────────────────────────────────────────
  const { data: expeditionsData } = useSWR<{ items: ExpeditionSummary[] }>(
    expeditionKeys.mine({ page_size: 2, visibility: "PUBLIC" }),
    ([url, params]: [string, Record<string, unknown>]) =>
      swrFetcherWithParams(url, params),
    { revalidateOnFocus: false }
  );

  const trendingCommunities = communitiesData?.items ?? [];
  const upcomingExpeditions = expeditionsData?.items ?? [];

  // Communities where the current user is a member — used in post composer
  const myCommunities: CommunitySummary[] = useMemo(
    () => (membershipsData?.communities ?? []).filter((c) => c.isMember === true),
    [membershipsData]
  );

  // Backend returns { posts: [...] } — use raw shape directly
  const rawPosts: RawPost[] = data?.posts ?? [];

  // ── Batch-resolve author profiles ────────────────────────────────────────
  // Collect unique author IDs from the current post list and resolve them in
  // a single request.  Posts store author_id as the auth-service UUID (JWT sub).
  // We use the /users/batch-profiles-by-auth endpoint so the map key matches
  // post.authorId directly.
  useEffect(() => {
    if (rawPosts.length === 0) return;
    const uniqueIds = [...new Set(rawPosts.map((p) => p.authorId))];
    // Only fetch IDs not already in the map
    const missing = uniqueIds.filter((id) => !(id in authorProfiles));
    if (missing.length === 0) return;
    batchProfilesByAuth(missing).then((map) => {
      setAuthorProfiles((prev) => ({ ...prev, ...map }));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rawPosts]);

  // Apply filter + search
  const displayPosts = useMemo(() => {
    let filtered = rawPosts;

    if (activeFilter === "community") {
      filtered = filtered.filter((p) => p.communityId !== null);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          (p.location?.toLowerCase().includes(q) ?? false) ||
          p.tagList.some((t) => t.toLowerCase().includes(q))
      );
    }

    return filtered;
  }, [rawPosts, activeFilter, searchQuery]);

  // ── Create Story ─────────────────────────────────────────────────────────
  /**
   * Called by StoryComposer when the user hits Publish.
   * Returns the created post's id so StoryComposer can run the media upload
   * loop against the correct /posts/{postId}/media/* endpoints.
   */
  async function handleCreatePost(payload: CreatePostRequest): Promise<string> {
    try {
      const post = await createPost(payload);
      showToast("Story published to feed!", "success");
      // Revalidate SWR feed immediately.
      await mutate();
      // Invalidate the TanStack Query my-posts cache so Profile → My Posts
      // reflects the new post on next visit.
      await queryClient.invalidateQueries({ queryKey: ["feed", "me", "posts"] });
      return post.id;
    } catch {
      showToast("Failed to publish story. Please try again.", "error");
      throw new Error("Create failed"); // Let StoryComposer abort the upload loop
    }
  }

  /**
   * Called by StoryComposer after all image uploads are finished.
   * Triggers a full SWR revalidation so new media appears in the feed.
   */
  async function handleUploadComplete(): Promise<void> {
    await mutate();
  }

  // ── Edit Story ───────────────────────────────────────────────────────────
  async function handleEditPost(postId: string, payload: UpdatePostRequest) {
    try {
      await updatePost(postId, payload);
      await mutate(
        (current) => {
          if (!current) return current;
          return {
            ...current,
            posts: current.posts.map((p) =>
              p.id === postId
                ? {
                    ...p,
                    title: payload.title ?? p.title,
                    location: payload.location !== undefined
                      ? (payload.location ?? null)
                      : p.location,
                    visibility: payload.visibility ?? p.visibility,
                  }
                : p
            ),
          };
        },
        { revalidate: false }
      );
      showToast("Story updated.", "success");
    } catch {
      showToast("Failed to update story.", "error");
      throw new Error("Update failed");
    }
  }

  // ── Delete Story ─────────────────────────────────────────────────────────
  async function handleDeletePost(postId: string) {
    try {
      await deletePost(postId);
      // Remove from SWR cache immediately
      await mutate(
        (current) => {
          if (!current) return current;
          return {
            ...current,
            posts: current.posts.filter((p) => p.id !== postId),
            total: current.total - 1,
          };
        },
        { revalidate: false }
      );
      // Invalidate TanStack Query my-posts cache so Profile → My Posts is
      // also up-to-date after a deletion.
      await queryClient.invalidateQueries({ queryKey: ["feed", "me", "posts"] });
      showToast("Story deleted.", "info");
    } catch {
      showToast("Failed to delete story.", "error");
      throw new Error("Delete failed");
    }
  }

  // ── Share ────────────────────────────────────────────────────────────────
  function handleCopyLink() {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href);
      showToast("Story link copied to clipboard!", "success");
    }
  }

  // ── Join Community ───────────────────────────────────────────────────────
  async function handleToggleJoin(community: CommunitySummary) {
    const isJoined = joinedCommunities.has(community.id);
    setJoinedCommunities((prev) => {
      const next = new Set(prev);
      if (isJoined) {
        next.delete(community.id);
      } else {
        next.add(community.id);
      }
      return next;
    });

    if (isJoined) {
      showToast(`Left ${community.name}`, "info");
    } else {
      showToast(`Joined ${community.name}!`, "success");
      try {
        await joinCommunity(community.id, {});
      } catch {
        // Fallback state retained
      }
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveFilter("all")}
            className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all ${
              activeFilter === "all"
                ? "bg-[#111111] text-white shadow-xs"
                : "bg-white text-gray-600 border border-[#EAE7DF] hover:bg-gray-50"
            }`}
          >
            All Stories
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter("community")}
            className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all ${
              activeFilter === "community"
                ? "bg-[#111111] text-white shadow-xs"
                : "bg-white text-gray-600 border border-[#EAE7DF] hover:bg-gray-50"
            }`}
          >
            Communities
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="w-full max-w-xl">
        <Search
          placeholder="Search stories, locations, tags, or travelers…"
          value={searchQuery}
          onChange={setSearchQuery}
          ariaLabel="Search feed"
        />
      </div>

      {/* 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Feed Column */}
        <div className="lg:col-span-8 space-y-6">
          {/* Create Story Composer */}
          <StoryComposer
            user={user}
            onSubmit={handleCreatePost}
            onUploadComplete={handleUploadComplete}
            communities={myCommunities}
          />

          {/* Post Cards */}
          <div className="space-y-6">
            {isLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <PostCardSkeleton key={i} />
              ))
            ) : (
              <AnimatePresence mode="popLayout">
                {displayPosts.length === 0 ? (
                  <div className="rounded-2xl border border-[#EAE7DF] bg-white p-12 text-center space-y-3">
                    <Compass size={36} className="mx-auto text-gray-300" />
                    <p className="text-sm font-semibold text-[#111111]">
                      No stories match your filter.
                    </p>
                    <p className="text-xs text-gray-500">
                      Try adjusting your search or switching to &quot;All Stories&quot;.
                    </p>
                  </div>
                ) : (
                  displayPosts.map((post) => (
                    <PostCard
                      key={post.id}
                      post={post}
                      currentUserId={user?.id ?? null}
                      authorProfile={authorProfiles[post.authorId] ?? null}
                      onEdit={handleEditPost}
                      onDelete={handleDeletePost}
                      onCopyLink={handleCopyLink}
                    />
                  ))
                )}
              </AnimatePresence>
            )}
          </div>
        </div>

        {/* Right Sidebar */}
        <aside className="hidden lg:block lg:col-span-4 space-y-6">
          {/* Trending Communities */}
          <div className="rounded-2xl border border-[#EAE7DF] bg-white p-5 space-y-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-[#111111] flex items-center gap-2">
                <Sparkles size={16} className="text-[#111111]" />
                Trending Communities
              </h3>
            </div>

            <div className="space-y-3">
              {trendingCommunities.length === 0 ? (
                <p className="text-xs text-gray-400 text-center py-4">
                  No communities yet
                </p>
              ) : (
                trendingCommunities.map((c) => {
                  const isJoined = joinedCommunities.has(c.id);
                  return (
                    <div
                      key={c.id}
                      className="flex items-center justify-between p-2.5 rounded-xl hover:bg-[#FBF9F4] transition-colors cursor-pointer"
                      onClick={() => router.push(`/communities/${c.id}`)}
                    >
                      <div className="flex items-center gap-3">
                        <div className="size-8 rounded-full bg-gradient-to-br from-[#111111] to-gray-600 flex items-center justify-center text-white text-xs font-bold">
                          {c.name.charAt(0)}
                        </div>
                        <div>
                          <h4 className="text-xs font-bold text-[#111111]">
                            {c.name}
                          </h4>
                          <p className="text-[11px] text-gray-500">
                            {c.memberCount.toLocaleString()} members
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleJoin(c);
                        }}
                        className={`rounded-lg px-3 py-1 text-xs font-semibold transition-all ${
                          isJoined
                            ? "bg-gray-100 text-gray-600 border border-gray-200"
                            : "border border-[#EAE7DF] bg-white text-[#111111] hover:bg-gray-100"
                        }`}
                      >
                        {isJoined ? "Joined" : "Join"}
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Suggested Travelers — coming soon */}
          <div className="rounded-2xl border border-[#EAE7DF] bg-white p-5 space-y-4 shadow-2xs">
            <h3 className="font-bold text-sm text-[#111111] flex items-center gap-2">
              <Users size={16} />
              Suggested Travelers
            </h3>
            <div className="flex flex-col items-center justify-center py-5 space-y-2 text-center">
              <Clock size={24} className="text-gray-300" />
              <p className="text-xs font-semibold text-gray-500">
                Feature coming soon
              </p>
              <p className="text-[11px] text-gray-400">
                Traveler recommendations will appear here.
              </p>
            </div>
          </div>

          {/* Upcoming Expeditions */}
          <div className="rounded-2xl border border-[#EAE7DF] bg-white p-5 space-y-4 shadow-2xs">
            <h3 className="font-bold text-sm text-[#111111] flex items-center gap-2">
              <Compass size={16} />
              Upcoming Expeditions
            </h3>

            <div className="space-y-3">
              {upcomingExpeditions.length === 0 ? (
                <p className="text-xs text-gray-400 text-center py-4">
                  No upcoming expeditions yet
                </p>
              ) : (
                upcomingExpeditions.map((exp) => (
                  <div
                    key={exp.id}
                    onClick={() => router.push(`/expeditions/${exp.id}`)}
                    className="p-3 rounded-xl border border-[#EAE7DF] bg-[#FBF9F4] space-y-1.5 cursor-pointer hover:border-gray-400 hover:bg-white transition-all shadow-2xs"
                  >
                    <h4 className="text-xs font-bold text-[#111111] hover:underline">
                      {exp.title}
                    </h4>
                    <div className="flex items-center justify-between text-[11px] text-gray-500">
                      {exp.startDate ? (
                        <span className="flex items-center gap-1">
                          <Calendar size={12} />
                          {new Date(exp.startDate).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                          })}
                          {exp.endDate &&
                            ` - ${new Date(exp.endDate).toLocaleDateString("en-US", {
                              month: "short",
                              day: "numeric",
                            })}`}
                        </span>
                      ) : (
                        <span className="flex items-center gap-1">
                          <MapPin size={12} />
                          {exp.destination}
                        </span>
                      )}
                      <span className="font-medium text-[#111111]">
                        {exp.maxParticipants} spots
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
