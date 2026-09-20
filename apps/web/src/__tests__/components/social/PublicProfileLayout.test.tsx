/**
 * CP-PROFILE-1: Public Profile Layout Consistency Tests
 * (src/app/users/[username]/layout.tsx + page.tsx)
 *
 * Verifies that the public profile route tree renders inside AppLayout —
 * the same application shell used by /profile, /feed, /communities, etc.
 *
 * Tests:
 *   1.  PublicProfileLayout wraps children in AppLayout
 *   2.  Sidebar (app-sidebar) is present in the rendered tree
 *   3.  Main content area (app-main-content) is present
 *   4.  Children are rendered inside the main content area
 *   5.  Other user's profile shows the Follow button
 *   6.  Public profile does NOT show an Edit Profile button
 *   7.  Real profile data (display_name, username, bio) renders
 *   8.  Missing avatar renders initial-letter fallback (neutral)
 *   9.  Missing cover renders gradient fallback (neutral)
 *   10. Reputation section renders when data is present
 *
 * Mocks:
 *   - @/components/auth/ProtectedRoute → renders children directly
 *   - @/contexts/AuthContext → isAuthenticated + user stub
 *   - @/services/users → getMyProfile + getPublicProfile at service boundary
 *   - next/navigation → usePathname, useParams, useRouter
 *   - next/image → plain <img> shim
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import PublicProfileLayout from "@/app/users/[username]/layout";
import PublicProfilePage from "@/app/users/[username]/page";
import type { PublicProfileResponse } from "@/services/users";

// ---------------------------------------------------------------------------
// Mock next/navigation
// ---------------------------------------------------------------------------

const mockParamsUsername = vi.fn<() => string>(() => "travellerj");

vi.mock("next/navigation", () => ({
  useParams: () => ({ username: mockParamsUsername() }),
  usePathname: () => "/users/travellerj",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

// ---------------------------------------------------------------------------
// Mock next/image — use a plain img element
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
// Mock ProtectedRoute — render children unconditionally so AppLayout tests
// are not blocked by auth redirects in the test environment.
// ---------------------------------------------------------------------------

vi.mock("@/components/auth/ProtectedRoute", () => ({
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="protected-route">{children}</div>
  ),
}));

// ---------------------------------------------------------------------------
// Mock AuthContext — authenticated user stub
// ---------------------------------------------------------------------------

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    isLoading: false,
    user: { id: "auth-001", email: "viewer@example.com" },
  }),
}));

// ---------------------------------------------------------------------------
// Mock LogoutButton — avoid auth side effects inside AppLayout footer
// ---------------------------------------------------------------------------

vi.mock("@/components/auth/LogoutButton", () => ({
  LogoutButton: ({ className }: { className?: string }) => (
    <button type="button" className={className}>
      Log out
    </button>
  ),
}));

// ---------------------------------------------------------------------------
// Mock getMyProfile — used by AppLayout sidebar for the logged-in user's info
// ---------------------------------------------------------------------------

vi.mock("@/services/users", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/services/users")>();
  return {
    ...actual,
    getMyProfile: vi.fn().mockResolvedValue({
      id: "me-001",
      username: "viewer",
      display_name: "Viewer User",
      avatar_url: null,
      cover_url: null,
      bio: null,
      city: null,
      country: null,
      interests: [],
      preferences: null,
      reputation: null,
      badges: [],
      created_at: "2025-01-01T00:00:00Z",
    }),
    getPublicProfile: vi.fn(),
    followUser: vi.fn().mockResolvedValue({ message: "Followed." }),
    unfollowUser: vi.fn().mockResolvedValue({ message: "Unfollowed." }),
  };
});

// Re-import after mock so we can control return values per test
import { getPublicProfile } from "@/services/users";

const mockGetPublicProfile = getPublicProfile as ReturnType<typeof vi.fn>;

// ---------------------------------------------------------------------------
// Query client factory — fresh per test
// ---------------------------------------------------------------------------

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, retryDelay: 0, gcTime: 0, staleTime: 0 },
    },
  });
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const STUB_PROFILE: PublicProfileResponse = {
  id: "profile-abc",
  username: "travellerj",
  display_name: "Jamie Traveller",
  bio: "Slow travel enthusiast.",
  avatar_url: "https://cdn.example.com/avatars/jamie.jpg",
  cover_url: "https://cdn.example.com/covers/jamie.jpg",
  city: "Amsterdam",
  country: "Netherlands",
  follower_count: 42,
  following_count: 17,
  badges: [],
  reputation: {
    explorer_score: 88,
    community_score: 75,
    review_score: 60,
    expeditions_joined: 5,
    expeditions_organized: 1,
    guide_interactions: 10,
    reviews_received: 20,
  },
  created_at: "2025-04-10T00:00:00Z",
  is_own_profile: false,
  is_following: false,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderLayout(children: React.ReactNode) {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <PublicProfileLayout>{children}</PublicProfileLayout>
    </QueryClientProvider>
  );
}

function renderFullPage() {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <PublicProfileLayout>
        <PublicProfilePage />
      </PublicProfileLayout>
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  mockParamsUsername.mockReturnValue("travellerj");
  mockGetPublicProfile.mockResolvedValue(STUB_PROFILE);
});

// ---------------------------------------------------------------------------
// 1. PublicProfileLayout wraps children in AppLayout
// ---------------------------------------------------------------------------

describe("PublicProfileLayout — renders inside AppLayout", () => {
  it("renders children through the AppLayout shell", () => {
    renderLayout(<div data-testid="layout-child">Hello</div>);

    expect(screen.getByTestId("layout-child")).toBeInTheDocument();
  });

  it("wraps children in the ProtectedRoute guard (via AppLayout)", () => {
    renderLayout(<div>Content</div>);

    // AppLayout wraps its output in ProtectedRoute; our mock renders the
    // data-testid="protected-route" wrapper so we can assert it is present.
    expect(screen.getByTestId("protected-route")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 2. Sidebar is present
// ---------------------------------------------------------------------------

describe("PublicProfileLayout — sidebar present", () => {
  it("renders the app-sidebar element", () => {
    renderLayout(<div>Content</div>);

    expect(screen.getByTestId("app-sidebar")).toBeInTheDocument();
  });

  it("sidebar contains OntDekker brand text", () => {
    renderLayout(<div>Content</div>);

    // The sidebar renders the brand name
    expect(screen.getAllByText(/ontdekker/i).length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// 3. Main content area uses the same container/layout structure
// ---------------------------------------------------------------------------

describe("PublicProfileLayout — main content area", () => {
  it("renders the app-main-content element", () => {
    renderLayout(<div>Content</div>);

    expect(screen.getByTestId("app-main-content")).toBeInTheDocument();
  });

  it("children are rendered inside the main content area", () => {
    renderLayout(<div data-testid="inner">Inner content</div>);

    const main = screen.getByTestId("app-main-content");
    const inner = screen.getByTestId("inner");

    expect(main).toContainElement(inner);
  });
});

// ---------------------------------------------------------------------------
// 4. Other user's profile shows Follow button
// ---------------------------------------------------------------------------

describe("PublicProfilePage (inside layout) — Follow button for other user", () => {
  it("shows a Follow button when is_own_profile=false and is_following=false", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...STUB_PROFILE,
      is_own_profile: false,
      is_following: false,
    });

    renderFullPage();

    await screen.findByRole("button", { name: /follow jamie traveller/i });

    expect(
      screen.getByRole("button", { name: /follow jamie traveller/i })
    ).toBeInTheDocument();
  });

  it("shows an Unfollow button when is_own_profile=false and is_following=true", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...STUB_PROFILE,
      is_own_profile: false,
      is_following: true,
    });

    renderFullPage();

    await screen.findByRole("button", { name: /unfollow jamie traveller/i });

    expect(
      screen.getByRole("button", { name: /unfollow jamie traveller/i })
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 5. Public profile does NOT show Edit Profile
// ---------------------------------------------------------------------------

describe("PublicProfilePage (inside layout) — no Edit Profile", () => {
  it("does not render an Edit Profile / Edit button for other users", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...STUB_PROFILE,
      is_own_profile: false,
    });

    renderFullPage();

    await screen.findByRole("heading", { name: /jamie traveller/i });

    // Should not have an Edit Profile / Edit button
    expect(
      screen.queryByRole("button", { name: /edit profile/i })
    ).not.toBeInTheDocument();

    expect(
      screen.queryByRole("link", { name: /edit/i })
    ).not.toBeInTheDocument();
  });

  it("does not render any edit-profile link for own profile on public profile page", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...STUB_PROFILE,
      is_own_profile: true,
    });

    renderFullPage();

    await screen.findByRole("heading", { name: /jamie traveller/i });

    // /users/[username] page never has an "Edit" button regardless of own profile
    expect(
      screen.queryByRole("link", { name: /^edit$/i })
    ).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 6. Real profile data renders
// ---------------------------------------------------------------------------

describe("PublicProfilePage (inside layout) — real data rendering", () => {
  it("renders display_name from the API response", async () => {
    renderFullPage();

    await screen.findByRole("heading", { name: /jamie traveller/i });

    expect(
      screen.getByRole("heading", { name: /jamie traveller/i })
    ).toBeInTheDocument();
  });

  it("renders @username from the API response", async () => {
    renderFullPage();

    await screen.findByText(/@travellerj/i);

    expect(screen.getByText(/@travellerj/i)).toBeInTheDocument();
  });

  it("renders bio from the API response", async () => {
    renderFullPage();

    await screen.findByText(/slow travel enthusiast/i);

    expect(screen.getByText(/slow travel enthusiast/i)).toBeInTheDocument();
  });

  it("renders location from the API response", async () => {
    renderFullPage();

    await screen.findByText(/amsterdam/i);

    expect(screen.getByText(/amsterdam.*netherlands/i)).toBeInTheDocument();
  });

  it("renders follower count from the API response", async () => {
    renderFullPage();

    await screen.findByText("42");

    expect(screen.getByText("42")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 7. Missing avatar renders neutral initial-letter fallback
// ---------------------------------------------------------------------------

describe("PublicProfilePage (inside layout) — avatar fallback", () => {
  it("renders the first letter of display_name when avatar_url is null", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...STUB_PROFILE,
      avatar_url: null,
    });

    renderFullPage();

    await screen.findByRole("heading", { name: /jamie traveller/i });

    // Expects "J" as the initial fallback
    expect(screen.getByText("J")).toBeInTheDocument();
  });

  it("does not render an img element for the avatar when avatar_url is null", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...STUB_PROFILE,
      avatar_url: null,
    });

    renderFullPage();

    await screen.findByRole("heading", { name: /jamie traveller/i });

    // No avatar img should be present
    const avatarImg = screen.queryByRole("img", {
      name: /jamie traveller avatar/i,
    });
    expect(avatarImg).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 8. Missing cover renders neutral gradient fallback (no img element for cover)
// ---------------------------------------------------------------------------

describe("PublicProfilePage (inside layout) — cover fallback", () => {
  it("does not render a cover img element when cover_url is null", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...STUB_PROFILE,
      cover_url: null,
    });

    renderFullPage();

    await screen.findByRole("heading", { name: /jamie traveller/i });

    const coverImg = screen.queryByRole("img", { name: /jamie traveller cover/i });
    expect(coverImg).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 9. Reputation section renders when data is present
// ---------------------------------------------------------------------------

describe("PublicProfilePage (inside layout) — reputation section", () => {
  it("renders the Reputation heading when reputation data is present", async () => {
    renderFullPage();

    await screen.findByRole("heading", { name: /reputation/i });

    expect(
      screen.getByRole("heading", { name: /reputation/i })
    ).toBeInTheDocument();
  });

  it("renders explorer_score from the API response", async () => {
    renderFullPage();

    await screen.findByText("88");

    expect(screen.getByText("88")).toBeInTheDocument();
  });

  it("renders community_score from the API response", async () => {
    renderFullPage();

    await screen.findByText("75");

    expect(screen.getByText("75")).toBeInTheDocument();
  });

  it("renders review_score from the API response", async () => {
    renderFullPage();

    await screen.findByText("60");

    expect(screen.getByText("60")).toBeInTheDocument();
  });

  it("does NOT render Reputation heading when reputation is null", async () => {
    mockGetPublicProfile.mockResolvedValue({
      ...STUB_PROFILE,
      reputation: null,
    });

    renderFullPage();

    await screen.findByRole("heading", { name: /jamie traveller/i });

    expect(
      screen.queryByRole("heading", { name: /reputation/i })
    ).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 10. Layout renders page content inside main content area
// ---------------------------------------------------------------------------

describe("PublicProfilePage (inside layout) — content inside main", () => {
  it("renders the profile heading inside app-main-content", async () => {
    renderFullPage();

    await screen.findByRole("heading", { name: /jamie traveller/i });

    const main = screen.getByTestId("app-main-content");
    const heading = screen.getByRole("heading", { name: /jamie traveller/i });

    expect(main).toContainElement(heading);
  });
});
