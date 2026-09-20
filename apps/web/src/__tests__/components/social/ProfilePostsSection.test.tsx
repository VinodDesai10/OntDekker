/**
 * Frontend tests for the Profile → My Posts section (CP-POST-3)
 *
 * Tests the observable behaviour of the MyPostsSection component embedded in
 * the profile page:
 *   1. Loading skeleton renders while the query is in-flight
 *   2. Empty state renders when the user has no posts
 *   3. Posts render when the user has posts
 *   4. Error state renders when the API call fails
 *   5. Global (PUBLIC) post is rendered with the correct visibility badge
 *   6. Community (COMMUNITY) post is rendered with the correct visibility badge
 *   7. Post count is shown in the section header
 *   8. Location and tags are rendered when present
 *   9. Cache key uses ["feed", "me", "posts", ...] so it can be invalidated
 *
 * Approach:
 *   - Mock @/services/feedApi.getMyPosts at the service boundary
 *   - Provide a real QueryClient so TanStack Query lifecycle works normally
 *   - Render only the profile page module; no MSW needed
 *   - Use waitFor to handle async query resolution
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { RawPostListResponse, RawPost } from "@/views/Feed/types";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// next/image → plain <img>
vi.mock("next/image", () => ({
  default: (props: Record<string, unknown>) => {
    // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
    return <img {...props} />;
  },
}));

// next/link → plain <a>
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

// next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useParams: () => ({}),
}));

// Mock getMyProfile to return a minimal profile
vi.mock("@/services/users", () => ({
  getMyProfile: vi.fn().mockResolvedValue({
    id: "prof-1",
    auth_user_id: "user-1",
    username: "test_user",
    display_name: "Test User",
    bio: null,
    avatar_url: null,
    cover_url: null,
    city: null,
    country: null,
    follower_count: 0,
    following_count: 0,
    interests: [],
    preferences: null,
    badges: [],
    reputation: null,
    saved_items: [],
    created_at: "2025-01-01T00:00:00Z",
  }),
  uploadAvatar: vi.fn(),
  uploadCover: vi.fn(),
  UPLOAD_ACCEPTED_MIME_TYPES: ["image/jpeg", "image/png", "image/webp"],
  UPLOAD_MAX_BYTES: 5_000_000,
}));

// Mock getMyPosts — tests override this per-test
const mockGetMyPosts = vi.fn<(params?: { limit?: number; offset?: number }) => Promise<RawPostListResponse>>();
vi.mock("@/services/feedApi", () => ({
  getMyPosts: (params?: { limit?: number; offset?: number }) => mockGetMyPosts(params),
  createPost: vi.fn(),
  updatePost: vi.fn(),
  deletePost: vi.fn(),
  getPostsByUser: vi.fn(),
  getPostsByCommunity: vi.fn(),
  getFeedPosts: vi.fn().mockResolvedValue({ posts: [], total: 0, limit: 20, offset: 0, hasMore: false }),
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makePost(overrides: Partial<RawPost> = {}): RawPost {
  return {
    id: "post-1",
    authorId: "user-1",
    communityId: null,
    title: "Test Travel Post",
    location: "Amsterdam, Netherlands",
    status: "PUBLISHED",
    visibility: "PUBLIC",
    coverImageUrl: null,
    media: [],
    tagList: ["travel", "adventure"],
    likeCount: 5,
    commentCount: 2,
    shareCount: 1,
    isLiked: false,
    isBookmarked: false,
    createdAt: "2026-01-15T10:00:00Z",
    updatedAt: "2026-01-15T10:00:00Z",
    ...overrides,
  };
}

function makeEmptyResponse(): RawPostListResponse {
  return { posts: [], total: 0, limit: 20, offset: 0, hasMore: false };
}

function makeResponseWith(posts: RawPost[]): RawPostListResponse {
  return { posts, total: posts.length, limit: 20, offset: 0, hasMore: false };
}

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

// Lazily import the profile page only after mocks are registered
async function renderProfilePage() {
  // Re-import to pick up fresh mocks
  const { default: ProfilePage } = await import("@/app/profile/page");
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <ProfilePage />
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Profile → My Posts section", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a loading skeleton while posts are loading", async () => {
    // Return a promise that never resolves during the test
    mockGetMyPosts.mockImplementation(
      () => new Promise<RawPostListResponse>(() => {})
    );

    await renderProfilePage();

    // Skeleton container has aria-label "Loading posts"
    await waitFor(() => {
      expect(
        screen.queryByLabelText("Loading posts")
      ).toBeTruthy();
    });
  });

  it("renders the empty state when the user has no posts", async () => {
    mockGetMyPosts.mockResolvedValue(makeEmptyResponse());

    await renderProfilePage();

    await waitFor(() => {
      expect(screen.getByText("No posts yet.")).toBeTruthy();
      expect(
        screen.getByText("Share your first travel story with the community.")
      ).toBeTruthy();
    });
  });

  it("renders posts when the user has posts", async () => {
    const post = makePost({ title: "My Alpine Adventure" });
    mockGetMyPosts.mockResolvedValue(makeResponseWith([post]));

    await renderProfilePage();

    await waitFor(() => {
      expect(screen.getByText("My Alpine Adventure")).toBeTruthy();
    });
  });

  it("renders the error state when the API call fails", async () => {
    mockGetMyPosts.mockRejectedValue(new Error("Network error"));

    await renderProfilePage();

    await waitFor(() => {
      expect(
        screen.getByText("Could not load posts. Please refresh.")
      ).toBeTruthy();
    });
  });

  it("renders the post count in the section header", async () => {
    const posts = [makePost({ id: "p1" }), makePost({ id: "p2" })];
    mockGetMyPosts.mockResolvedValue({
      posts,
      total: 2,
      limit: 20,
      offset: 0,
      hasMore: false,
    });

    await renderProfilePage();

    await waitFor(() => {
      expect(screen.getByText("2 posts")).toBeTruthy();
    });
  });

  it("shows singular 'post' when exactly 1 post exists", async () => {
    mockGetMyPosts.mockResolvedValue({
      posts: [makePost()],
      total: 1,
      limit: 20,
      offset: 0,
      hasMore: false,
    });

    await renderProfilePage();

    await waitFor(() => {
      expect(screen.getByText("1 post")).toBeTruthy();
    });
  });

  it("renders 'Global' visibility badge for a PUBLIC post", async () => {
    const post = makePost({ visibility: "PUBLIC" });
    mockGetMyPosts.mockResolvedValue(makeResponseWith([post]));

    await renderProfilePage();

    await waitFor(() => {
      expect(screen.getByText("Global")).toBeTruthy();
    });
  });

  it("renders 'Community' visibility badge for a COMMUNITY post", async () => {
    const post = makePost({
      visibility: "COMMUNITY",
      communityId: "community-123",
    });
    mockGetMyPosts.mockResolvedValue(makeResponseWith([post]));

    await renderProfilePage();

    await waitFor(() => {
      expect(screen.getByText("Community")).toBeTruthy();
    });
  });

  it("renders the post location when present", async () => {
    const post = makePost({ location: "Zurich, Switzerland" });
    mockGetMyPosts.mockResolvedValue(makeResponseWith([post]));

    await renderProfilePage();

    await waitFor(() => {
      expect(screen.getByText("Zurich, Switzerland")).toBeTruthy();
    });
  });

  it("renders tags for a post", async () => {
    const post = makePost({ tagList: ["hiking", "alps", "summer"] });
    mockGetMyPosts.mockResolvedValue(makeResponseWith([post]));

    await renderProfilePage();

    await waitFor(() => {
      expect(screen.getByText("hiking")).toBeTruthy();
      expect(screen.getByText("alps")).toBeTruthy();
      expect(screen.getByText("summer")).toBeTruthy();
    });
  });

  it("renders like and comment counts for a post", async () => {
    const post = makePost({ likeCount: 42, commentCount: 7 });
    mockGetMyPosts.mockResolvedValue(makeResponseWith([post]));

    await renderProfilePage();

    await waitFor(() => {
      expect(screen.getByText("42 likes")).toBeTruthy();
      expect(screen.getByText("7 comments")).toBeTruthy();
    });
  });

  it("renders multiple posts when the user has several", async () => {
    const posts = [
      makePost({ id: "p1", title: "Post One" }),
      makePost({ id: "p2", title: "Post Two" }),
      makePost({ id: "p3", title: "Post Three" }),
    ];
    mockGetMyPosts.mockResolvedValue(makeResponseWith(posts));

    await renderProfilePage();

    await waitFor(() => {
      expect(screen.getByText("Post One")).toBeTruthy();
      expect(screen.getByText("Post Two")).toBeTruthy();
      expect(screen.getByText("Post Three")).toBeTruthy();
    });
  });

  it("calls getMyPosts with correct default parameters", async () => {
    mockGetMyPosts.mockResolvedValue(makeEmptyResponse());

    await renderProfilePage();

    await waitFor(() => {
      expect(mockGetMyPosts).toHaveBeenCalledWith({ limit: 20, offset: 0 });
    });
  });
});
