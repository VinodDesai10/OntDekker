"use client";

/**
 * PostDetailView — Full single-post detail page
 *
 * Fetches the post by ID via getPostById(), resolves the author identity
 * via batchProfilesByAuth(), and renders the full post with:
 *   - Cover image / media gallery
 *   - Title, full content/body
 *   - Author display name, username, avatar (real identity)
 *   - Location, created date, visibility, tags
 *   - Like / bookmark actions (optimistic)
 *   - CommentsSection (with real comment author identity)
 *
 * Handles loading, not-found (404), API error, and normal states.
 * Author click navigates to /users/{username}.
 *
 * Does NOT introduce mock data or hardcoded images.
 */

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  MapPin,
  Heart,
  Bookmark,
  Calendar,
  Eye,
  MessageSquare,
  ArrowLeft,
  Globe,
  Lock,
  Users,
} from "lucide-react";
import { getPostById, likePost, unlikePost, bookmarkPost, unbookmarkPost } from "@/services/feedApi";
import { batchProfilesByAuth, type BatchProfileSummary } from "@/services/users";
import { ImageCarousel } from "@/components/content/ImageCarousel";
import { CommentsSection } from "./CommentsSection";
import type { Post } from "@/types";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface PostDetailViewProps {
  postId: string;
  /** The authenticated user's auth-service UUID (null if not logged in) */
  currentUserId: string | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function VisibilityBadge({ visibility }: { visibility: string }) {
  if (visibility === "PUBLIC") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-[#EAE7DF] bg-[#FBF9F4] px-3 py-1 text-[11px] font-semibold text-[#111111]">
        <Globe size={11} />
        Global
      </span>
    );
  }
  if (visibility === "COMMUNITY") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-[#EAE7DF] bg-[#FBF9F4] px-3 py-1 text-[11px] font-semibold text-[#111111]">
        <Users size={11} />
        Community
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-[#EAE7DF] bg-[#FBF9F4] px-3 py-1 text-[11px] font-semibold text-[#111111]">
      <Lock size={11} />
      Private
    </span>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PostDetailView({ postId, currentUserId }: PostDetailViewProps) {
  const router = useRouter();

  // Post state
  const [post, setPost] = useState<Post | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [apiError, setApiError] = useState(false);

  // Author identity
  const [authorProfile, setAuthorProfile] = useState<BatchProfileSummary | null>(null);

  // Interaction state
  const [liking, setLiking] = useState(false);
  const [bookmarking, setBookmarking] = useState(false);
  const [commentCount, setCommentCount] = useState(0);

  // ── Fetch post ─────────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setNotFound(false);
    setApiError(false);

    getPostById(postId)
      .then((p) => {
        if (cancelled) return;
        setPost(p);
        setCommentCount(p.commentCount);

        // Resolve author identity in a single batch call
        batchProfilesByAuth([p.authorId]).then((map) => {
          if (!cancelled) {
            setAuthorProfile(map[p.authorId] ?? null);
          }
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        // Treat 404 (or any HTTP 404-like response) as not-found
        const status =
          err &&
          typeof err === "object" &&
          "response" in err &&
          (err as { response?: { status?: number } }).response?.status;
        if (status === 404) {
          setNotFound(true);
        } else {
          setApiError(true);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [postId]);

  // ── Like/Unlike ─────────────────────────────────────────────────────────────
  async function handleToggleLike() {
    if (!post || liking) return;
    const wasLiked = post.isLiked;
    // Optimistic update
    setPost((p) =>
      p
        ? {
            ...p,
            isLiked: !wasLiked,
            likeCount: wasLiked ? p.likeCount - 1 : p.likeCount + 1,
          }
        : p
    );
    setLiking(true);
    try {
      if (wasLiked) {
        const res = await unlikePost(post.id);
        setPost((p) => (p ? { ...p, isLiked: res.isLiked, likeCount: res.likeCount } : p));
      } else {
        const res = await likePost(post.id);
        setPost((p) => (p ? { ...p, isLiked: res.isLiked, likeCount: res.likeCount } : p));
      }
    } catch {
      // Rollback
      setPost((p) =>
        p
          ? {
              ...p,
              isLiked: wasLiked,
              likeCount: wasLiked ? p.likeCount + 1 : p.likeCount - 1,
            }
          : p
      );
    } finally {
      setLiking(false);
    }
  }

  // ── Bookmark/Unbookmark ─────────────────────────────────────────────────────
  async function handleToggleBookmark() {
    if (!post || bookmarking) return;
    const wasBookmarked = post.isBookmarked;
    setPost((p) => (p ? { ...p, isBookmarked: !wasBookmarked } : p));
    setBookmarking(true);
    try {
      if (wasBookmarked) {
        const res = await unbookmarkPost(post.id);
        setPost((p) => (p ? { ...p, isBookmarked: res.isBookmarked } : p));
      } else {
        const res = await bookmarkPost(post.id);
        setPost((p) => (p ? { ...p, isBookmarked: res.isBookmarked } : p));
      }
    } catch {
      setPost((p) => (p ? { ...p, isBookmarked: wasBookmarked } : p));
    } finally {
      setBookmarking(false);
    }
  }

  // ── Loading ──────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div
        role="status"
        aria-label="Loading post"
        className="max-w-2xl mx-auto space-y-6 animate-pulse"
      >
        {/* Back button placeholder */}
        <div className="h-8 w-24 rounded-lg bg-gray-100" />
        {/* Card */}
        <div className="rounded-2xl border border-[#EAE7DF] bg-white p-6 space-y-5">
          {/* Author row */}
          <div className="flex items-center gap-3">
            <div className="size-10 rounded-full bg-gray-100" />
            <div className="space-y-1.5 flex-1">
              <div className="h-3 w-32 rounded-full bg-gray-100" />
              <div className="h-2.5 w-24 rounded-full bg-gray-100" />
            </div>
          </div>
          {/* Title */}
          <div className="h-6 w-3/4 rounded-full bg-gray-100" />
          {/* Media placeholder */}
          <div className="h-56 rounded-xl bg-gray-100" />
          {/* Body lines */}
          <div className="space-y-2">
            <div className="h-3 w-full rounded-full bg-gray-100" />
            <div className="h-3 w-5/6 rounded-full bg-gray-100" />
            <div className="h-3 w-4/6 rounded-full bg-gray-100" />
          </div>
        </div>
      </div>
    );
  }

  // ── Not found ────────────────────────────────────────────────────────────────
  if (notFound) {
    return (
      <div className="max-w-2xl mx-auto text-center space-y-4 py-24">
        <p className="text-4xl">🗺️</p>
        <h2 className="text-xl font-bold text-[#111111]">Post not found</h2>
        <p className="text-sm text-gray-500">
          This story might have been deleted or is no longer visible to you.
        </p>
        <button
          type="button"
          onClick={() => router.push("/feed")}
          className="mt-2 inline-flex items-center gap-2 rounded-xl bg-[#111111] px-4 py-2 text-sm font-semibold text-white hover:bg-[#333333] transition-colors"
        >
          <ArrowLeft size={16} />
          Back to feed
        </button>
      </div>
    );
  }

  // ── API error ────────────────────────────────────────────────────────────────
  if (apiError || !post) {
    return (
      <div className="max-w-2xl mx-auto text-center space-y-4 py-24">
        <p className="text-4xl">⚠️</p>
        <h2 className="text-xl font-bold text-[#111111]">Something went wrong</h2>
        <p className="text-sm text-gray-500">
          Failed to load this story. Please try again.
        </p>
        <button
          type="button"
          onClick={() => router.push("/feed")}
          className="mt-2 inline-flex items-center gap-2 rounded-xl bg-[#111111] px-4 py-2 text-sm font-semibold text-white hover:bg-[#333333] transition-colors"
        >
          <ArrowLeft size={16} />
          Back to feed
        </button>
      </div>
    );
  }

  // ── Media display ────────────────────────────────────────────────────────────
  const sortedMedia = [...(post.media ?? [])].sort(
    (a, b) => a.displayOrder - b.displayOrder
  );
  const carouselImages = sortedMedia.map((m) => ({
    id: m.id,
    url: m.mediaUrl,
    alt: post.title,
  }));

  // ── Normal render ─────────────────────────────────────────────────────────────
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Back navigation */}
      <button
        type="button"
        onClick={() => router.back()}
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-[#111111] transition-colors"
      >
        <ArrowLeft size={16} />
        Back
      </button>

      {/* Post article */}
      <article className="rounded-2xl border border-[#EAE7DF] bg-white p-6 space-y-5 shadow-2xs">
        {/* Author Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            {/* Avatar */}
            <button
              type="button"
              aria-label={
                authorProfile
                  ? `View ${authorProfile.displayName}'s profile`
                  : "View author profile"
              }
              onClick={() =>
                authorProfile && router.push(`/users/${authorProfile.username}`)
              }
              className="size-11 rounded-full shrink-0 overflow-hidden focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-[#111111]"
            >
              {authorProfile?.avatarUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={authorProfile.avatarUrl}
                  alt={authorProfile.displayName}
                  className="size-11 rounded-full object-cover"
                />
              ) : (
                <div className="size-11 rounded-full bg-[#111111] text-white flex items-center justify-center font-bold text-sm">
                  {authorProfile
                    ? authorProfile.displayName.charAt(0).toUpperCase()
                    : "?"}
                </div>
              )}
            </button>

            {/* Author info */}
            <div className="min-w-0">
              <button
                type="button"
                onClick={() =>
                  authorProfile && router.push(`/users/${authorProfile.username}`)
                }
                className={`block text-sm font-bold text-[#111111] leading-tight truncate max-w-[200px] ${
                  authorProfile ? "hover:underline cursor-pointer" : "cursor-default"
                }`}
              >
                {authorProfile ? authorProfile.displayName : "Unknown user"}
              </button>
              <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-500 flex-wrap">
                {authorProfile && (
                  <button
                    type="button"
                    onClick={() => router.push(`/users/${authorProfile.username}`)}
                    className="text-gray-400 hover:underline"
                  >
                    @{authorProfile.username}
                  </button>
                )}
                {post.location && (
                  <>
                    {authorProfile && <span>•</span>}
                    <span className="flex items-center gap-1 text-gray-400">
                      <MapPin size={11} />
                      {post.location}
                    </span>
                  </>
                )}
                <span>•</span>
                <span className="flex items-center gap-1 text-gray-400">
                  <Calendar size={11} />
                  {new Date(post.createdAt).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </span>
              </div>
            </div>
          </div>

          {/* Visibility badge */}
          <div className="shrink-0">
            <VisibilityBadge visibility={post.visibility} />
          </div>
        </div>

        {/* Title */}
        <h1 className="text-2xl font-bold text-[#111111] leading-snug">
          {post.title}
        </h1>

        {/* Media gallery */}
        {carouselImages.length > 0 && (
          <ImageCarousel
            images={carouselImages}
            aspectRatio="16/9"
            showCaptions={false}
          />
        )}

        {/* Full body content */}
        {post.content && (
          <div className="prose prose-sm max-w-none text-gray-700 leading-relaxed whitespace-pre-wrap">
            {post.content}
          </div>
        )}

        {/* Tags */}
        {post.tags && post.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {post.tags.map((tag) => (
              <span
                key={tag}
                className="text-xs font-medium text-gray-500 hover:text-[#111111] cursor-pointer"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Stats row */}
        <div className="flex items-center gap-4 text-xs text-gray-400 border-t border-[#EAE7DF] pt-4">
          <span className="flex items-center gap-1">
            <Eye size={13} />
            {post.viewCount.toLocaleString()} views
          </span>
          <span className="flex items-center gap-1">
            <Heart size={13} />
            {post.likeCount.toLocaleString()} likes
          </span>
          <span className="flex items-center gap-1">
            <MessageSquare size={13} />
            {commentCount.toLocaleString()} comments
          </span>
        </div>

        {/* Action bar */}
        <div className="flex items-center justify-between border-t border-[#EAE7DF] pt-4 text-xs font-medium text-gray-600">
          <div className="flex items-center gap-6">
            {/* Like */}
            <button
              type="button"
              onClick={handleToggleLike}
              disabled={liking || !currentUserId}
              aria-label={post.isLiked ? "Unlike" : "Like"}
              className={`flex items-center gap-1.5 transition-colors disabled:opacity-60 ${
                post.isLiked
                  ? "text-red-600 font-semibold"
                  : "hover:text-[#111111]"
              }`}
            >
              <Heart
                size={20}
                className={post.isLiked ? "fill-red-600 text-red-600" : ""}
              />
              <span>{post.likeCount}</span>
            </button>

            {/* Comment count */}
            <span className="flex items-center gap-1.5 text-gray-500">
              <MessageSquare size={20} />
              <span>{commentCount}</span>
            </span>
          </div>

          {/* Bookmark */}
          <button
            type="button"
            onClick={handleToggleBookmark}
            disabled={bookmarking || !currentUserId}
            aria-label={post.isBookmarked ? "Remove bookmark" : "Bookmark"}
            className={`flex items-center gap-1 transition-colors disabled:opacity-60 ${
              post.isBookmarked ? "text-[#111111]" : "hover:text-[#111111]"
            }`}
          >
            <Bookmark
              size={20}
              className={post.isBookmarked ? "fill-[#111111]" : ""}
            />
          </button>
        </div>

        {/* Comments Section — always visible on detail page */}
        <CommentsSection
          postId={post.id}
          currentUserId={currentUserId}
          onCountChange={(delta) =>
            setCommentCount((c) => Math.max(0, c + delta))
          }
        />
      </article>
    </div>
  );
}
