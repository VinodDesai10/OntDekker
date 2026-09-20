/**
 * Tests for PostDetailView (CP-FEED-4 Part 1)
 *
 * Tests:
 *  1. Loading state
 *  2. Successful post rendering (title, content, location, tags, visibility, media)
 *  3. Post not found (404)
 *  4. API error
 *  5. Real author identity (displayName, username, avatar)
 *  6. Author navigation to /users/{username}
 *  7. Comments section rendered
 *
 * All external API calls are mocked at the service boundary.
 * MSW server is active and set to onUnhandledRequest: "error" —
 * we use vi.mock to intercept at the module level, not via network.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// Mocks — all must be declared before any imports of the modules under test
// ---------------------------------------------------------------------------

const mockPush = vi.fn();
const mockBack = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: mockBack, replace: vi.fn() }),
  useParams: () => ({}),
}));

// Avoid ESM import issues with motion
vi.mock("motion/react", () => ({
  motion: {
    div: ({ children, ...rest }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div {...rest}>{children}</div>
    ),
    article: ({ children, ...rest }: React.HTMLAttributes<HTMLElement> & { children?: React.ReactNode }) => (
      <article {...rest}>{children}</article>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ImageCarousel — render first image's alt text so tests can verify media
vi.mock("@/components/content/ImageCarousel", () => ({
  ImageCarousel: ({ images }: { images: Array<{ id: string; url: string; alt: string }> }) => (
    <div data-testid="image-carousel">
      {images.map((img) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={img.id} src={img.url} alt={img.alt} />
      ))}
    </div>
  ),
}));

// CommentsSection — light stub so we can verify it's rendered
vi.mock("@/views/Feed/CommentsSection", () => ({
  CommentsSection: ({ postId }: { postId: string }) => (
    <div data-testid="comments-section" data-post-id={postId}>
      Comments section
    </div>
  ),
}));

// Auth context — provide a logged-in user
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "auth-user-abc", email: "test@example.com" },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

// ---------------------------------------------------------------------------
// Service mocks — controlled per-test
// ---------------------------------------------------------------------------

const mockGetPostById = vi.fn();
const mockLikePost = vi.fn();
const mockUnlikePost = vi.fn();
const mockBookmarkPost = vi.fn();
const mockUnbookmarkPost = vi.fn();

vi.mock("@/services/feedApi", () => ({
  getPostById: (...args: unknown[]) => mockGetPostById(...args),
  likePost: (...args: unknown[]) => mockLikePost(...args),
  unlikePost: (...args: unknown[]) => mockUnlikePost(...args),
  bookmarkPost: (...args: unknown[]) => mockBookmarkPost(...args),
  unbookmarkPost: (...args: unknown[]) => mockUnbookmarkPost(...args),
}));

const mockBatchProfilesByAuth = vi.fn();

vi.mock("@/services/users", () => ({
  batchProfilesByAuth: (...args: unknown[]) => mockBatchProfilesByAuth(...args),
}));

// ---------------------------------------------------------------------------
// Import component AFTER mocks are registered
// ---------------------------------------------------------------------------

import { PostDetailView } from "@/views/Feed/PostDetailView";
import type { Post, PostMedia } from "@/types";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeMedia(overrides: Partial<PostMedia> = {}): PostMedia {
  return {
    id: "media-1",
    postId: "post-1",
    mediaUrl: "https://example.com/photo.jpg",
    objectKey: "feed/photo.jpg",
    mediaType: "IMAGE",
    displayOrder: 0,
    altText: null,
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function makePost(overrides: Partial<Post> = {}): Post {
  return {
    id: "post-1",
    authorId: "auth-abc-123",
    communityId: null,
    expeditionId: null,
    title: "Summit at Dawn",
    content: "We reached the summit just as the sun rose. It was breathtaking.",
    location: "Alps, Switzerland",
    visibility: "PUBLIC",
    status: "PUBLISHED",
    tags: ["hiking", "alps", "sunrise"],
    media: [],
    likeCount: 12,
    commentCount: 4,
    shareCount: 2,
    viewCount: 200,
    isLiked: false,
    isBookmarked: false,
    createdAt: "2026-03-15T06:00:00Z",
    updatedAt: "2026-03-15T06:00:00Z",
    ...overrides,
  };
}

const AUTHOR_PROFILE = {
  id: "profile-1",
  username: "adriaan_trails",
  displayName: "Adriaan Bergsma",
  avatarUrl: "https://example.com/avatar.jpg",
};

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderPostDetail(postId = "post-1") {
  return render(<PostDetailView postId={postId} currentUserId="auth-user-abc" />);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("PostDetailView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1. Loading state
  it("shows a loading skeleton while the post is loading", () => {
    mockGetPostById.mockImplementation(() => new Promise(() => {}));
    mockBatchProfilesByAuth.mockResolvedValue({});

    renderPostDetail();

    // Loading skeleton has role="status" and aria-label="Loading post"
    expect(screen.getByRole("status", { name: "Loading post" })).toBeTruthy();
  });

  // 2. Successful post rendering
  it("renders post title, content, location, tags, and visibility", async () => {
    const post = makePost();
    mockGetPostById.mockResolvedValue(post);
    mockBatchProfilesByAuth.mockResolvedValue({});

    renderPostDetail();

    await waitFor(() => {
      expect(screen.getByText("Summit at Dawn")).toBeTruthy();
    });

    expect(
      screen.getByText("We reached the summit just as the sun rose. It was breathtaking.")
    ).toBeTruthy();
    expect(screen.getByText("Alps, Switzerland")).toBeTruthy();
    expect(screen.getByText("#hiking")).toBeTruthy();
    expect(screen.getByText("#alps")).toBeTruthy();
    expect(screen.getByText("#sunrise")).toBeTruthy();
    // Visibility badge
    expect(screen.getByText("Global")).toBeTruthy();
  });

  // 2b. Media rendered
  it("renders the image carousel when media is present", async () => {
    const post = makePost({ media: [makeMedia()] });
    mockGetPostById.mockResolvedValue(post);
    mockBatchProfilesByAuth.mockResolvedValue({});

    renderPostDetail();

    await waitFor(() => {
      expect(screen.getByTestId("image-carousel")).toBeTruthy();
    });
  });

  // 3. Post not found
  it("shows a not-found message when the API returns 404", async () => {
    mockGetPostById.mockRejectedValue({
      response: { status: 404 },
    });
    mockBatchProfilesByAuth.mockResolvedValue({});

    renderPostDetail();

    await waitFor(() => {
      expect(screen.getByText("Post not found")).toBeTruthy();
    });
  });

  // 4. API error
  it("shows an error message on non-404 API failure", async () => {
    mockGetPostById.mockRejectedValue(new Error("Network error"));
    mockBatchProfilesByAuth.mockResolvedValue({});

    renderPostDetail();

    await waitFor(() => {
      expect(screen.getByText("Something went wrong")).toBeTruthy();
    });
  });

  // 5. Real author identity
  it("displays the real author displayName when profile is resolved", async () => {
    const post = makePost({ authorId: "auth-abc-123" });
    mockGetPostById.mockResolvedValue(post);
    mockBatchProfilesByAuth.mockResolvedValue({
      "auth-abc-123": AUTHOR_PROFILE,
    });

    renderPostDetail();

    await waitFor(() => {
      expect(screen.getByText("Adriaan Bergsma")).toBeTruthy();
    });
    expect(screen.getByText("@adriaan_trails")).toBeTruthy();
  });

  it("displays the author avatar when avatarUrl is provided", async () => {
    const post = makePost({ authorId: "auth-abc-123" });
    mockGetPostById.mockResolvedValue(post);
    mockBatchProfilesByAuth.mockResolvedValue({
      "auth-abc-123": AUTHOR_PROFILE,
    });

    renderPostDetail();

    await waitFor(() => {
      const img = screen.getByAltText("Adriaan Bergsma") as HTMLImageElement;
      expect(img.src).toContain("example.com/avatar.jpg");
    });
  });

  it("shows 'Unknown user' when the author profile cannot be resolved", async () => {
    const post = makePost({ authorId: "unresolvable-id" });
    mockGetPostById.mockResolvedValue(post);
    // batchProfilesByAuth returns empty map → no profile for this ID
    mockBatchProfilesByAuth.mockResolvedValue({});

    renderPostDetail();

    await waitFor(() => {
      expect(screen.getByText("Unknown user")).toBeTruthy();
    });
  });

  it("does NOT show UUID fragments in the author display area", async () => {
    const post = makePost({ authorId: "auth-abc-123-def-456" });
    mockGetPostById.mockResolvedValue(post);
    mockBatchProfilesByAuth.mockResolvedValue({
      "auth-abc-123-def-456": AUTHOR_PROFILE,
    });

    renderPostDetail();

    await waitFor(() => {
      expect(screen.getByText("Adriaan Bergsma")).toBeTruthy();
    });
    // No UUID prefix should appear
    expect(screen.queryByText(/auth-abc-123/)).toBeNull();
  });

  // 6. Author navigation
  it("navigates to /users/{username} when author name is clicked", async () => {
    const post = makePost({ authorId: "auth-abc-123" });
    mockGetPostById.mockResolvedValue(post);
    mockBatchProfilesByAuth.mockResolvedValue({
      "auth-abc-123": AUTHOR_PROFILE,
    });

    renderPostDetail();

    await waitFor(() => {
      expect(screen.getByText("Adriaan Bergsma")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Adriaan Bergsma"));
    expect(mockPush).toHaveBeenCalledWith("/users/adriaan_trails");
  });

  // 7. Comments section rendered
  it("renders the CommentsSection for the post", async () => {
    const post = makePost({ id: "post-xyz" });
    mockGetPostById.mockResolvedValue(post);
    mockBatchProfilesByAuth.mockResolvedValue({});

    renderPostDetail("post-xyz");

    await waitFor(() => {
      const section = screen.getByTestId("comments-section");
      expect(section).toBeTruthy();
      expect(section.getAttribute("data-post-id")).toBe("post-xyz");
    });
  });

  // Back button navigates to feed on not-found
  it("navigates back to /feed when the not-found 'Back to feed' button is clicked", async () => {
    mockGetPostById.mockRejectedValue({ response: { status: 404 } });
    mockBatchProfilesByAuth.mockResolvedValue({});

    renderPostDetail();

    await waitFor(() => {
      expect(screen.getByText("Post not found")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("Back to feed"));
    expect(mockPush).toHaveBeenCalledWith("/feed");
  });

  // batchProfilesByAuth is called with the post's authorId
  it("calls batchProfilesByAuth with the post authorId", async () => {
    const post = makePost({ authorId: "auth-abc-123" });
    mockGetPostById.mockResolvedValue(post);
    mockBatchProfilesByAuth.mockResolvedValue({});

    renderPostDetail();

    await waitFor(() => {
      expect(mockBatchProfilesByAuth).toHaveBeenCalledWith(["auth-abc-123"]);
    });
  });
});
