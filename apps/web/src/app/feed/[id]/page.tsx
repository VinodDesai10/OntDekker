"use client";

/**
 * Feed Post Detail Page — /feed/[id]
 *
 * Renders the full detail view for a single travel story post.
 * Delegates to PostDetailView which handles:
 *   - Loading / not-found / error states
 *   - Real author identity via batchProfilesByAuth()
 *   - Like, bookmark, and comment interactions
 */

import { use } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { PostDetailView } from "@/views/Feed/PostDetailView";

interface FeedPostPageProps {
  params: Promise<{ id: string }>;
}

export default function FeedPostPage({ params }: FeedPostPageProps) {
  const { id } = use(params);
  const { user } = useAuth();

  return (
    <main className="container mx-auto px-4 py-8">
      <PostDetailView postId={id} currentUserId={user?.id ?? null} />
    </main>
  );
}
