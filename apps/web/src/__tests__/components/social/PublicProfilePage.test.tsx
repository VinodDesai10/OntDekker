/**
 * Component tests for the Public Profile page
 * (src/app/users/[username]/page.tsx)
 *
 * Tests observable behavior only — no implementation internals.
 *
 * PublicProfilePage uses:
 *   - useParams() to read the `username` route segment
 *   - useQuery() (@tanstack/react-query) to call getPublicProfile(username)
 *   - useMutation() to call followUser / unfollowUser
 *   - useQueryClient() to invalidate the profile query after follow/unfollow
 *
 * Coverage:
 *   1. Loading (skeleton) state
 *   2. Successful profile rendering — identity, bio, location, counts
 *   3. Followers / following navigation links
 *   4. Reputation scores rendered when present
 *   5. Badges rendered when present
 *   6. 404 / not-found state
 *   7. Generic error state
 *   8. Private data is NOT exposed in the rendered output
 *   9. Follow/Unfollow UI — Checkpoint 22.5 viewer-context behavior
 *
 * Mocks:
 *   - next/navigation useParams
 *   - @/services/users getPublicProfile, followUser, unfollowUser (service boundary)
 *   - next/image (plain <img> shim)
 *
 * No MSW / no network calls needed.
 * A QueryClient is provided via QueryClientProvider for each test.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import PublicProfilePage from "@/app/users/[username]/page";
import type { PublicProfileResponse } from "@/services/users";
import { ApiError } from "@/services/api";

// ---------------------------------------------------------------------------
// Mock next/navigation — useParams
// ---------------------------------------------------------------------------

const mockParamsUsername = vi.fn<() => string>(() => "explorer42");

vi.mock("next/navigation", () => ({
  useParams: () => ({ username: mockParamsUsername() }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

// ---------------------------------------------------------------------------
// Mock next/image
// ---------------------------------------------------------------------------

vi.mock("next/image", () => ({
  default: ({
    src,
    alt,
    ...rest
  }: {
    src: string;
    alt: string;
    [k: string]: unknown;
    // eslint-disable-next-line @next/next/no-img-element
  }) => <img src={src} alt={alt} {...(rest as Record<string, unknown>)} />,
}));

// ---------------------------------------------------------------------------
// Mock getPublicProfile, followUser, unfollowUser at the service boundary
// ---------------------------------------------------------------------------

const mockGetPublicProfile = vi.fn<(arg: string) => Promise<PublicProfileResponse>>();
const mockFollowUser = vi.fn<(arg: string) => Promise<{ message: string }>>();
const mockUnfollowUser = vi.fn<(arg: string) => Promise<{ message: string }>>();

vi.mock("@/services/users", () => ({
  getPublicProfile: (...args: unknown[]) =>
    mockGetPublicProfile(...(args as [string])),
  followUser: (...args: unknown[]) =>
    mockFollowUser(...(args as [string])),
  unfollowUser: (...args: unknown[]) =>
    mockUnfollowUser(...(args as [string])),
}));

// ---------------------------------------------------------------------------
// QueryClient factory — fresh client per test to prevent caching bleed
// ---------------------------------------------------------------------------

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // The page defines its own retry function that overrides this default.
        // We set retryDelay to 0 so any retries fire immediately, preventing
        // tests from timing out while waiting for retry backoff delays.
        retryDelay: 0,
        gcTime: 0,   // Don't cache between tests
        staleTime: 0,
      },
    },
  });
}

function renderPage() {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <PublicProfilePage />
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const BASE_PROFILE: PublicProfileResponse = {
  id: "profile-id-001",
  username: "explorer42",
  display_name: "Anya Kowalski",
  bio: "Mountains are my therapy.",
  avatar_url: "https://cdn.example.com/avatars/anya.jpg",
  cover_url: null,
  city: "Kraków",
  country: "Poland",
  follower_count: 128,
  following_count: 64,
  badges: [],
  reputation: null,
  created_at: "2025-03-15T09:00:00Z",
  is_own_profile: false,
  is_following: false,
};

const FULL_PROFILE: PublicProfileResponse = {
  ...BASE_PROFILE,
  reputation: {
    explorer_score: 95,
    community_score: 80,
    review_score: 70,
    expeditions_joined: 12,
    expeditions_organized: 3,
    guide_interactions: 25,
    reviews_received: 40,
  },
  badges: [
    {
      id: "badge-1",
      badge_name: "Summit Seeker",
      badge_icon: null,
      earned_at: "2025-06-01T00:00:00Z",
    },
    {
      id: "badge-2",
      badge_name: "Community Builder",
      badge_icon: null,
      earned_at: "2025-07-01T00:00:00Z",
    },
  ],
};

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  mockParamsUsername.mockReturnValue("explorer42");
  // Default follow/unfollow to resolve successfully
  mockFollowUser.mockResolvedValue({ message: "Followed successfully." });
  mockUnfollowUser.mockResolvedValue({ message: "Unfollowed successfully." });
});

// ---------------------------------------------------------------------------
// 1. Loading state
// ---------------------------------------------------------------------------

describe("PublicProfilePage — loading", () => {
  it("renders the loading skeleton while profile is being fetched", () => {
    // Keep promise pending
    mockGetPublicProfile.mockImplementation(() => new Promise(() => {}));

    renderPage();

    expect(
      screen.getByRole("generic", { name: /loading profile/i })
    ).toBeInTheDocument();
  });

  it("calls getPublicProfile with the username from route params", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    await waitFor(() => {
      expect(mockGetPublicProfile).toHaveBeenCalledWith("explorer42");
    });
  });
});

// ---------------------------------------------------------------------------
// 2. Successful profile rendering
// ---------------------------------------------------------------------------

describe("PublicProfilePage — successful rendering", () => {
  it("renders the user's display name", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    await screen.findByRole("heading", { name: /anya kowalski/i });

    expect(
      screen.getByRole("heading", { name: /anya kowalski/i })
    ).toBeInTheDocument();
  });

  it("renders the @username", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    await screen.findByText(/@explorer42/i);

    expect(screen.getByText(/@explorer42/i)).toBeInTheDocument();
  });

  it("renders the bio text", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    await screen.findByText(/mountains are my therapy/i);

    expect(screen.getByText(/mountains are my therapy/i)).toBeInTheDocument();
  });

  it("renders city and country location", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    await screen.findByText(/kraków/i);

    expect(screen.getByText(/kraków.*poland/i)).toBeInTheDocument();
  });

  it("renders the avatar image when avatar_url is provided", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    const img = await screen.findByRole("img", { name: /anya kowalski avatar/i });
    expect(img).toHaveAttribute("src", "https://cdn.example.com/avatars/anya.jpg");
  });

  it("renders initial fallback when avatar_url is null", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      avatar_url: null,
    });

    renderPage();

    await screen.findByText(/anya kowalski/i);

    // First letter "A" shown as initial
    expect(screen.getByText("A")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 3. Followers / following navigation links
// ---------------------------------------------------------------------------

describe("PublicProfilePage — social links", () => {
  it("renders a followers link with the correct href", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    const link = await screen.findByRole("link", {
      name: /128 followers/i,
    });
    expect(link).toHaveAttribute("href", "/users/explorer42/followers");
  });

  it("renders the follower count in the link", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    await screen.findByText("128");

    expect(screen.getByText("128")).toBeInTheDocument();
  });

  it("renders a following link with the correct href", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    const link = await screen.findByRole("link", {
      name: /64 following/i,
    });
    expect(link).toHaveAttribute("href", "/users/explorer42/following");
  });

  it("renders the following count", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    await screen.findByText("64");

    expect(screen.getByText("64")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 4. Reputation scores
// ---------------------------------------------------------------------------

describe("PublicProfilePage — reputation", () => {
  it("renders the Reputation section heading when reputation data is present", async () => {
    mockGetPublicProfile.mockResolvedValue(FULL_PROFILE);

    renderPage();

    await screen.findByRole("heading", { name: /reputation/i });

    expect(
      screen.getByRole("heading", { name: /reputation/i })
    ).toBeInTheDocument();
  });

  it("renders explorer_score", async () => {
    mockGetPublicProfile.mockResolvedValue(FULL_PROFILE);

    renderPage();

    await screen.findByText("95");

    expect(screen.getByText("95")).toBeInTheDocument();
    expect(screen.getByText("Explorer")).toBeInTheDocument();
  });

  it("renders community_score", async () => {
    mockGetPublicProfile.mockResolvedValue(FULL_PROFILE);

    renderPage();

    await screen.findByText("80");

    expect(screen.getByText("80")).toBeInTheDocument();
    expect(screen.getByText("Community")).toBeInTheDocument();
  });

  it("renders review_score", async () => {
    mockGetPublicProfile.mockResolvedValue(FULL_PROFILE);

    renderPage();

    await screen.findByText("70");

    expect(screen.getByText("70")).toBeInTheDocument();
    expect(screen.getByText("Review")).toBeInTheDocument();
  });

  it("does NOT render the Reputation section when reputation is null", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE); // reputation: null

    renderPage();

    await screen.findByRole("heading", { name: /anya kowalski/i });

    expect(
      screen.queryByRole("heading", { name: /reputation/i })
    ).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 5. Badges
// ---------------------------------------------------------------------------

describe("PublicProfilePage — badges", () => {
  it("renders the Badges section heading when badges are present", async () => {
    mockGetPublicProfile.mockResolvedValue(FULL_PROFILE);

    renderPage();

    await screen.findByRole("heading", { name: /badges/i });

    expect(
      screen.getByRole("heading", { name: /badges/i })
    ).toBeInTheDocument();
  });

  it("renders each badge name", async () => {
    mockGetPublicProfile.mockResolvedValue(FULL_PROFILE);

    renderPage();

    await screen.findByText("Summit Seeker");

    expect(screen.getByText("Summit Seeker")).toBeInTheDocument();
    expect(screen.getByText("Community Builder")).toBeInTheDocument();
  });

  it("does NOT render the Badges section when badges array is empty", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE); // badges: []

    renderPage();

    await screen.findByRole("heading", { name: /anya kowalski/i });

    expect(
      screen.queryByRole("heading", { name: /badges/i })
    ).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 6. 404 / not-found state
// ---------------------------------------------------------------------------

describe("PublicProfilePage — not found (404)", () => {
  it("renders the 'User not found' heading when the API returns 404", async () => {
    mockGetPublicProfile.mockRejectedValue(
      new ApiError(404, { success: false, message: "Profile not found", code: "PROFILE_NOT_FOUND" })
    );

    renderPage();

    await screen.findByText(/user not found/i);

    expect(screen.getByText(/user not found/i)).toBeInTheDocument();
  });

  it("includes the requested username in the not-found message", async () => {
    mockGetPublicProfile.mockRejectedValue(
      new ApiError(404, { success: false, message: "Profile not found", code: "PROFILE_NOT_FOUND" })
    );

    renderPage();

    await screen.findByText(/@explorer42/i);

    // Should mention the username in the not-found body
    expect(screen.getByText(/@explorer42/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 7. Generic error state
// ---------------------------------------------------------------------------

describe("PublicProfilePage — generic error", () => {
  it("shows the ApiError message for non-404 failures", async () => {
    mockGetPublicProfile.mockRejectedValue(
      new ApiError(503, {
        success: false,
        message: "Service temporarily unavailable",
        code: "SERVICE_UNAVAILABLE",
      })
    );

    renderPage();

    await screen.findByText(/service temporarily unavailable/i);

    expect(
      screen.getByText(/service temporarily unavailable/i)
    ).toBeInTheDocument();
  });

  it("shows a generic fallback message for non-ApiError failures", async () => {
    mockGetPublicProfile.mockRejectedValue(new Error("Network error"));

    renderPage();

    await screen.findByText(/could not load this profile/i);

    expect(
      screen.getByText(/could not load this profile/i)
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 8. Private data NOT exposed
// ---------------------------------------------------------------------------

describe("PublicProfilePage — private data not exposed", () => {
  it("does not render auth_user_id anywhere in the document", async () => {
    // auth_user_id is only on PrivateProfileResponse, not PublicProfileResponse.
    // Confirm it is never injected via the public profile response.
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    await screen.findByRole("heading", { name: /anya kowalski/i });

    expect(document.body.textContent).not.toContain("auth_user_id");
  });

  it("does not render a saved_items section", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    await screen.findByRole("heading", { name: /anya kowalski/i });

    expect(document.body.textContent).not.toContain("saved_items");
    expect(document.body.textContent).not.toContain("Saved Items");
  });

  it("does not render a preferences section", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    await screen.findByRole("heading", { name: /anya kowalski/i });

    // Preferences are private. Should not appear.
    expect(
      screen.queryByRole("heading", { name: /preferences/i })
    ).not.toBeInTheDocument();
  });

  it("does not render an interests section", async () => {
    mockGetPublicProfile.mockResolvedValue(BASE_PROFILE);

    renderPage();

    await screen.findByRole("heading", { name: /anya kowalski/i });

    expect(
      screen.queryByRole("heading", { name: /interests/i })
    ).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 9. Follow/Unfollow UI — Checkpoint 22.5 viewer-context behavior
// ---------------------------------------------------------------------------

describe("PublicProfilePage — Follow button (not following)", () => {
  it("shows a Follow button when is_own_profile=false and is_following=false", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      is_own_profile: false,
      is_following: false,
    });

    renderPage();

    await screen.findByRole("button", { name: /follow anya kowalski/i });

    expect(
      screen.getByRole("button", { name: /follow anya kowalski/i })
    ).toBeInTheDocument();
  });

  it("does not show an Unfollow button when is_following=false", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      is_own_profile: false,
      is_following: false,
    });

    renderPage();

    await screen.findByRole("button", { name: /follow anya kowalski/i });

    expect(
      screen.queryByRole("button", { name: /unfollow/i })
    ).not.toBeInTheDocument();
  });
});

describe("PublicProfilePage — Unfollow button (already following)", () => {
  it("shows an Unfollow button when is_own_profile=false and is_following=true", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      is_own_profile: false,
      is_following: true,
    });

    renderPage();

    await screen.findByRole("button", { name: /unfollow anya kowalski/i });

    expect(
      screen.getByRole("button", { name: /unfollow anya kowalski/i })
    ).toBeInTheDocument();
  });

  it("does not show a Follow button when is_following=true", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      is_own_profile: false,
      is_following: true,
    });

    renderPage();

    await screen.findByRole("button", { name: /unfollow anya kowalski/i });

    expect(
      screen.queryByRole("button", { name: /^follow anya kowalski$/i })
    ).not.toBeInTheDocument();
  });
});

describe("PublicProfilePage — own profile (no Follow/Unfollow)", () => {
  it("does not render a Follow button when is_own_profile=true", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      is_own_profile: true,
      is_following: false,
    });

    renderPage();

    await screen.findByRole("heading", { name: /anya kowalski/i });

    expect(
      screen.queryByRole("button", { name: /follow/i })
    ).not.toBeInTheDocument();
  });

  it("does not render an Unfollow button when is_own_profile=true", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      is_own_profile: true,
      is_following: false,
    });

    renderPage();

    await screen.findByRole("heading", { name: /anya kowalski/i });

    expect(
      screen.queryByRole("button", { name: /unfollow/i })
    ).not.toBeInTheDocument();
  });
});

describe("PublicProfilePage — unauthenticated viewer (default false fields)", () => {
  it("shows a Follow button when both is_own_profile and is_following are false (unauthenticated defaults)", async () => {
    // Server returns defaults for unauthenticated viewer
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      is_own_profile: false,
      is_following: false,
    });

    renderPage();

    await screen.findByRole("button", { name: /follow anya kowalski/i });

    expect(
      screen.getByRole("button", { name: /follow anya kowalski/i })
    ).toBeInTheDocument();
  });
});

describe("PublicProfilePage — successful Follow", () => {
  it("calls followUser with the profile id when Follow is clicked", async () => {
    const user = userEvent.setup();
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      is_own_profile: false,
      is_following: false,
    });

    renderPage();

    const followBtn = await screen.findByRole("button", {
      name: /follow anya kowalski/i,
    });
    await user.click(followBtn);

    await waitFor(() => {
      expect(mockFollowUser).toHaveBeenCalledWith("profile-id-001");
    });
  });

  it("invalidates the profile query after successful follow (triggering refetch)", async () => {
    const user = userEvent.setup();
    // First call: not following; second call (after invalidation): following
    mockGetPublicProfile
      .mockResolvedValueOnce({
        ...BASE_PROFILE,
        is_own_profile: false,
        is_following: false,
      })
      .mockResolvedValue({
        ...BASE_PROFILE,
        is_own_profile: false,
        is_following: true,
        follower_count: 129,
      });

    renderPage();

    const followBtn = await screen.findByRole("button", {
      name: /follow anya kowalski/i,
    });
    await user.click(followBtn);

    // After mutation success + query invalidation, the Unfollow button should appear
    await screen.findByRole("button", { name: /unfollow anya kowalski/i });

    expect(
      screen.getByRole("button", { name: /unfollow anya kowalski/i })
    ).toBeInTheDocument();
  });

  it("shows updated follower_count after successful follow refetch", async () => {
    const user = userEvent.setup();
    mockGetPublicProfile
      .mockResolvedValueOnce({
        ...BASE_PROFILE,
        is_own_profile: false,
        is_following: false,
        follower_count: 128,
      })
      .mockResolvedValue({
        ...BASE_PROFILE,
        is_own_profile: false,
        is_following: true,
        follower_count: 129,
      });

    renderPage();

    const followBtn = await screen.findByRole("button", {
      name: /follow anya kowalski/i,
    });
    await user.click(followBtn);

    await waitFor(() => {
      expect(screen.getByText("129")).toBeInTheDocument();
    });
  });
});

describe("PublicProfilePage — successful Unfollow", () => {
  it("calls unfollowUser with the profile id when Unfollow is clicked", async () => {
    const user = userEvent.setup();
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      is_own_profile: false,
      is_following: true,
    });

    renderPage();

    const unfollowBtn = await screen.findByRole("button", {
      name: /unfollow anya kowalski/i,
    });
    await user.click(unfollowBtn);

    await waitFor(() => {
      expect(mockUnfollowUser).toHaveBeenCalledWith("profile-id-001");
    });
  });

  it("invalidates the profile query after successful unfollow", async () => {
    const user = userEvent.setup();
    mockGetPublicProfile
      .mockResolvedValueOnce({
        ...BASE_PROFILE,
        is_own_profile: false,
        is_following: true,
        follower_count: 128,
      })
      .mockResolvedValue({
        ...BASE_PROFILE,
        is_own_profile: false,
        is_following: false,
        follower_count: 127,
      });

    renderPage();

    const unfollowBtn = await screen.findByRole("button", {
      name: /unfollow anya kowalski/i,
    });
    await user.click(unfollowBtn);

    await screen.findByRole("button", { name: /follow anya kowalski/i });

    expect(
      screen.getByRole("button", { name: /follow anya kowalski/i })
    ).toBeInTheDocument();
  });
});

describe("PublicProfilePage — pending/duplicate-click protection", () => {
  it("disables the Follow button while mutation is pending", async () => {
    const user = userEvent.setup();
    // Never resolves — keeps mutation in pending state
    mockFollowUser.mockImplementation(() => new Promise(() => {}));
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      is_own_profile: false,
      is_following: false,
    });

    renderPage();

    const followBtn = await screen.findByRole("button", {
      name: /follow anya kowalski/i,
    });
    await user.click(followBtn);

    // Button should be disabled immediately after click
    await waitFor(() => {
      expect(followBtn).toBeDisabled();
    });
  });

  it("disables the Unfollow button while mutation is pending", async () => {
    const user = userEvent.setup();
    mockUnfollowUser.mockImplementation(() => new Promise(() => {}));
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      is_own_profile: false,
      is_following: true,
    });

    renderPage();

    const unfollowBtn = await screen.findByRole("button", {
      name: /unfollow anya kowalski/i,
    });
    await user.click(unfollowBtn);

    await waitFor(() => {
      expect(unfollowBtn).toBeDisabled();
    });
  });
});

describe("PublicProfilePage — Follow/Unfollow API error handling", () => {
  it("shows an error message when followUser fails", async () => {
    const user = userEvent.setup();
    mockFollowUser.mockRejectedValue(
      new ApiError(500, {
        success: false,
        message: "Internal server error",
        code: "INTERNAL_ERROR",
      })
    );
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      is_own_profile: false,
      is_following: false,
    });

    renderPage();

    const followBtn = await screen.findByRole("button", {
      name: /follow anya kowalski/i,
    });
    await user.click(followBtn);

    await screen.findByRole("alert");

    expect(screen.getByRole("alert")).toHaveTextContent(/internal server error/i);
  });

  it("shows a generic error message when unfollowUser fails with a non-ApiError", async () => {
    const user = userEvent.setup();
    mockUnfollowUser.mockRejectedValue(new Error("Network timeout"));
    mockGetPublicProfile.mockResolvedValue({
      ...BASE_PROFILE,
      is_own_profile: false,
      is_following: true,
    });

    renderPage();

    const unfollowBtn = await screen.findByRole("button", {
      name: /unfollow anya kowalski/i,
    });
    await user.click(unfollowBtn);

    await screen.findByRole("alert");

    expect(screen.getByRole("alert")).toHaveTextContent(
      /could not unfollow/i
    );
  });
});
