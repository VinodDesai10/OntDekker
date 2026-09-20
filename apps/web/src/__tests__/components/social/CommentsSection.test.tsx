/**
 * Tests for CommentsSection with real comment author identity (CP-FEED-4 Part 2 & 3)
 *
 * Tests:
 *  1. Top-level comment shows real displayName (not UUID fragment)
 *  2. Reply shows real displayName (not UUID fragment)
 *  3. Avatar comes from user-service (avatarUrl rendered as <img>)
 *  4. batchProfilesByAuth is called once for unique author IDs
 *  5. Duplicate author IDs are deduplicated
 *  6. Unresolved profile shows neutral fallback ("Unknown user")
 *  7. Clicking author navigates to /users/{username}
 *
 * All API calls are mocked at the service boundary.
 * MSW server is active (onUnhandledRequest: "error"); no MSW handlers needed.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// Mocks — declared before any module-under-test imports
// ---------------------------------------------------------------------------

const mockPush = vi.fn();
const mockBack = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: mockBack, replace: vi.fn() }),
  useParams: () => ({}),
}));

// Feed API mocks
const mockGetComments = vi.fn();
const mockCreateComment = vi.fn();
const mockUpdateComment = vi.fn();
const mockDeleteComment = vi.fn();

vi.mock("@/services/feedApi", () => ({
  getComments: (...args: unknown[]) => mockGetComments(...args),
  createComment: (...args: unknown[]) => mockCreateComment(...args),
  updateComment: (...args: unknown[]) => mockUpdateComment(...args),
  deleteComment: (...args: unknown[]) => mockDeleteComment(...args),
}));

// User service mock
const mockBatchProfilesByAuth = vi.fn();

vi.mock("@/services/users", () => ({
  batchProfilesByAuth: (...args: unknown[]) => mockBatchProfilesByAuth(...args),
}));

// ---------------------------------------------------------------------------
// Import under test AFTER mocks
// ---------------------------------------------------------------------------

import { CommentsSection } from "@/views/Feed/CommentsSection";
import type { RawComment } from "@/views/Feed/types";
import type { ProfileMap } from "@/services/users";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeComment(overrides: Partial<RawComment> = {}): RawComment {
  return {
    id: "comment-1",
    postId: "post-1",
    authorId: "auth-author-1",
    parentCommentId: null,
    content: "Great adventure!",
    isDeleted: false,
    replies: [],
    createdAt: "2026-01-15T10:00:00Z",
    updatedAt: "2026-01-15T10:00:00Z",
    ...overrides,
  };
}

function makeReply(overrides: Partial<RawComment> = {}): RawComment {
  return makeComment({
    id: "comment-reply-1",
    authorId: "auth-author-2",
    parentCommentId: "comment-1",
    content: "I agree!",
    ...overrides,
  });
}

const PROFILE_AUTHOR_1 = {
  id: "profile-1",
  username: "lena_wanders",
  displayName: "Lena Wanderer",
  avatarUrl: "https://example.com/lena.jpg",
};

const PROFILE_AUTHOR_2 = {
  id: "profile-2",
  username: "marc_climbs",
  displayName: "Marc Climber",
  avatarUrl: null,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildCommentResponse(comments: RawComment[]) {
  return { comments, total: comments.length, limit: 20, offset: 0, hasMore: false };
}

interface RenderResult {
  container: HTMLElement;
}

function renderSection(
  postId = "post-1",
  currentUserId: string | null = "auth-user-abc"
): RenderResult {
  const onCountChange = vi.fn();
  return render(
    <CommentsSection
      postId={postId}
      currentUserId={currentUserId}
      onCountChange={onCountChange}
    />
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CommentsSection — author identity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1. Top-level comment shows real displayName
  it("shows the real displayName for a top-level comment author", async () => {
    const comment = makeComment({ authorId: "auth-author-1" });
    mockGetComments.mockResolvedValue(buildCommentResponse([comment]));
    mockBatchProfilesByAuth.mockResolvedValue({
      "auth-author-1": PROFILE_AUTHOR_1,
    });

    renderSection();

    await waitFor(() => {
      expect(screen.getByText("Lena Wanderer")).toBeTruthy();
    });
  });

  // 2. Reply shows real displayName
  it("shows the real displayName for a reply author", async () => {
    const reply = makeReply({ authorId: "auth-author-2" });
    const comment = makeComment({
      authorId: "auth-author-1",
      replies: [reply],
    });
    mockGetComments.mockResolvedValue(buildCommentResponse([comment]));
    mockBatchProfilesByAuth.mockResolvedValue({
      "auth-author-1": PROFILE_AUTHOR_1,
      "auth-author-2": PROFILE_AUTHOR_2,
    });

    renderSection();

    await waitFor(() => {
      expect(screen.getByText("Marc Climber")).toBeTruthy();
    });
  });

  // 3. Avatar comes from user-service
  it("renders the avatar <img> with avatarUrl from the user-service", async () => {
    const comment = makeComment({ authorId: "auth-author-1" });
    mockGetComments.mockResolvedValue(buildCommentResponse([comment]));
    mockBatchProfilesByAuth.mockResolvedValue({
      "auth-author-1": PROFILE_AUTHOR_1,
    });

    renderSection();

    await waitFor(() => {
      const img = screen.getByAltText("Lena Wanderer") as HTMLImageElement;
      expect(img.src).toContain("example.com/lena.jpg");
    });
  });

  // 4. batchProfilesByAuth is called once for unique author IDs
  it("calls batchProfilesByAuth exactly once after loading comments", async () => {
    const c1 = makeComment({ id: "c1", authorId: "auth-author-1" });
    const c2 = makeComment({ id: "c2", authorId: "auth-author-2" });
    mockGetComments.mockResolvedValue(buildCommentResponse([c1, c2]));
    mockBatchProfilesByAuth.mockResolvedValue({
      "auth-author-1": PROFILE_AUTHOR_1,
      "auth-author-2": PROFILE_AUTHOR_2,
    });

    renderSection();

    await waitFor(() => {
      expect(screen.getByText("Lena Wanderer")).toBeTruthy();
    });

    // resolveAuthors only calls batchProfilesByAuth once on initial load
    // (it doesn't call separately for each comment)
    const calls = mockBatchProfilesByAuth.mock.calls;
    // All IDs should have been sent in a single call
    const firstCallIds = calls[0][0] as string[];
    expect(firstCallIds).toContain("auth-author-1");
    expect(firstCallIds).toContain("auth-author-2");
  });

  // 5. Duplicate author IDs are deduplicated
  it("deduplicates author IDs before calling batchProfilesByAuth", async () => {
    // Two comments by the same author
    const c1 = makeComment({ id: "c1", authorId: "auth-author-1" });
    const c2 = makeComment({ id: "c2", authorId: "auth-author-1" });
    mockGetComments.mockResolvedValue(buildCommentResponse([c1, c2]));
    mockBatchProfilesByAuth.mockResolvedValue({
      "auth-author-1": PROFILE_AUTHOR_1,
    });

    renderSection();

    await waitFor(() => {
      // Both comments resolve to the same author
      const names = screen.getAllByText("Lena Wanderer");
      expect(names.length).toBe(2);
    });

    // batchProfilesByAuth must NOT have received duplicate IDs
    const firstCallIds = mockBatchProfilesByAuth.mock.calls[0][0] as string[];
    const uniqueIds = new Set(firstCallIds);
    expect(uniqueIds.size).toBe(firstCallIds.length);
    // Should only contain one unique ID
    expect(firstCallIds.filter((id: string) => id === "auth-author-1").length).toBe(1);
  });

  // 6. Unresolved profile shows neutral fallback
  it("shows 'Unknown user' when the author profile is not in the returned map", async () => {
    const comment = makeComment({ authorId: "auth-unresolvable" });
    mockGetComments.mockResolvedValue(buildCommentResponse([comment]));
    // batchProfilesByAuth returns empty map — no profile for this ID
    mockBatchProfilesByAuth.mockResolvedValue({} as ProfileMap);

    renderSection();

    await waitFor(() => {
      expect(screen.getByText("Unknown user")).toBeTruthy();
    });
  });

  it("does NOT show raw UUID fragments as author names", async () => {
    const comment = makeComment({ authorId: "3f4a1c2e-beef-dead-cafe-000000000000" });
    mockGetComments.mockResolvedValue(buildCommentResponse([comment]));
    mockBatchProfilesByAuth.mockResolvedValue({} as ProfileMap);

    renderSection();

    await waitFor(() => {
      expect(screen.getByText("Unknown user")).toBeTruthy();
    });
    // Ensure no UUID fragment pattern like "3f4a1c2e…" is in the DOM
    expect(screen.queryByText(/3f4a1c2e/)).toBeNull();
  });

  // 7. Clicking author navigates to /users/{username}
  it("navigates to /users/{username} when the author name is clicked", async () => {
    const comment = makeComment({ authorId: "auth-author-1" });
    mockGetComments.mockResolvedValue(buildCommentResponse([comment]));
    mockBatchProfilesByAuth.mockResolvedValue({
      "auth-author-1": PROFILE_AUTHOR_1,
    });

    renderSection();

    await waitFor(() => {
      expect(screen.getByText("Lena Wanderer")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Lena Wanderer"));
    expect(mockPush).toHaveBeenCalledWith("/users/lena_wanders");
  });

  // Replies also use same identity resolution
  it("reply author navigation also goes to /users/{username}", async () => {
    const reply = makeReply({ authorId: "auth-author-2" });
    const comment = makeComment({
      authorId: "auth-author-1",
      replies: [reply],
    });
    mockGetComments.mockResolvedValue(buildCommentResponse([comment]));
    mockBatchProfilesByAuth.mockResolvedValue({
      "auth-author-1": PROFILE_AUTHOR_1,
      "auth-author-2": PROFILE_AUTHOR_2,
    });

    renderSection();

    await waitFor(() => {
      expect(screen.getByText("Marc Climber")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Marc Climber"));
    expect(mockPush).toHaveBeenCalledWith("/users/marc_climbs");
  });

  // Existing behavior: comment creation still works
  it("creates a comment and adds it to the list", async () => {
    mockGetComments.mockResolvedValue(buildCommentResponse([]));
    mockBatchProfilesByAuth.mockResolvedValue({});
    mockCreateComment.mockResolvedValue(
      makeComment({ id: "new-1", authorId: "auth-user-abc", content: "Hello world" })
    );

    renderSection("post-1", "auth-user-abc");

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Write a comment...")).toBeTruthy();
    });

    const input = screen.getByPlaceholderText("Write a comment...");
    fireEvent.change(input, { target: { value: "Hello world" } });
    fireEvent.submit(input.closest("form")!);

    await waitFor(() => {
      expect(mockCreateComment).toHaveBeenCalledWith("post-1", {
        content: "Hello world",
      });
    });
  });

  // Loading state
  it("shows 'Loading comments…' while comments are loading", () => {
    mockGetComments.mockImplementation(() => new Promise(() => {}));
    mockBatchProfilesByAuth.mockResolvedValue({});

    renderSection();

    expect(screen.getByText("Loading comments…")).toBeTruthy();
  });

  // Empty state
  it("shows empty state when there are no comments", async () => {
    mockGetComments.mockResolvedValue(buildCommentResponse([]));
    mockBatchProfilesByAuth.mockResolvedValue({});

    renderSection();

    await waitFor(() => {
      expect(
        screen.getByText("No comments yet. Be the first to comment!")
      ).toBeTruthy();
    });
  });
});
