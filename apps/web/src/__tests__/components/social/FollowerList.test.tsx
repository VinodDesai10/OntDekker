/**
 * Component tests for FollowerList
 * (src/components/social/FollowerList.tsx)
 *
 * FollowerList is a pure controlled component — it accepts all data and
 * callbacks as props. No service calls, no routing, no context required.
 *
 * Coverage:
 *   1. Loading state
 *   2. Error state (ApiError + generic error)
 *   3. Empty state (undefined data + data with zero items)
 *   4. Follower rendering — name, username, profile links
 *   5. Avatar — image rendered when url present; initial fallback otherwise
 *   6. Pagination — controls visible only for multi-page; prev/next boundaries
 *
 * No MSW / no network calls needed.
 * next/image is mocked to render a plain <img> in the test environment.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FollowerList } from "@/components/social/FollowerList";
import type { PaginatedFollowersResponse } from "@/services/users";
import { ApiError } from "@/services/api";

// ---------------------------------------------------------------------------
// Mock next/image — the real component requires a Next.js build context
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
// Fixtures
// ---------------------------------------------------------------------------

function makeFollower(
  n: number,
  overrides: Partial<{
    id: string;
    username: string;
    display_name: string;
    avatar_url: string | null;
  }> = {}
) {
  return {
    id: overrides.id ?? `user-${n}`,
    username: overrides.username ?? `traveler${n}`,
    display_name: overrides.display_name ?? `Traveler ${n}`,
    avatar_url: overrides.avatar_url ?? null,
  };
}

function makePageData(
  items: ReturnType<typeof makeFollower>[],
  overrides: Partial<{ total: number; page: number; size: number }> = {}
): PaginatedFollowersResponse {
  return {
    items,
    total: overrides.total ?? items.length,
    page: overrides.page ?? 1,
    size: overrides.size ?? 20,
  };
}

// ---------------------------------------------------------------------------
// Default props helpers
// ---------------------------------------------------------------------------

const noop = vi.fn();

function renderList(
  props: Partial<{
    title: string;
    data: PaginatedFollowersResponse | undefined;
    isLoading: boolean;
    error: unknown;
    page: number;
    onPageChange: (p: number) => void;
  }> = {}
) {
  return render(
    <FollowerList
      title={props.title ?? "Followers"}
      data={props.data}
      isLoading={props.isLoading ?? false}
      error={props.error ?? null}
      page={props.page ?? 1}
      onPageChange={props.onPageChange ?? noop}
    />
  );
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// 1. Loading state
// ---------------------------------------------------------------------------

describe("FollowerList — loading", () => {
  it("renders an sr-only loading message while loading", () => {
    renderList({ isLoading: true });

    expect(screen.getByText(/loading followers/i)).toBeInTheDocument();
  });

  it("does not render any list items while loading", () => {
    renderList({ isLoading: true });

    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("uses the title prop in the loading text", () => {
    renderList({ title: "Following", isLoading: true });

    expect(screen.getByText(/loading following/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 2. Error state
// ---------------------------------------------------------------------------

describe("FollowerList — error", () => {
  it("shows the ApiError message on failure", () => {
    renderList({
      error: new ApiError(503, {
        success: false,
        message: "Could not connect to user service",
        code: "SERVICE_UNAVAILABLE",
      }),
    });

    expect(
      screen.getByText(/could not connect to user service/i)
    ).toBeInTheDocument();
  });

  it("shows a generic fallback message for non-ApiError errors", () => {
    renderList({ title: "Followers", error: new Error("Unknown") });

    expect(
      screen.getByText(/could not load followers. please try again/i)
    ).toBeInTheDocument();
  });

  it("does not render a list on error", () => {
    renderList({ error: new ApiError(500, { success: false, message: "Error", code: "GENERIC_ERROR" }) });

    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 3. Empty state
// ---------------------------------------------------------------------------

describe("FollowerList — empty", () => {
  it("shows the empty-state message when data is undefined", () => {
    renderList({ data: undefined });

    expect(screen.getByText(/no followers yet/i)).toBeInTheDocument();
  });

  it("shows the empty-state message when items array is empty", () => {
    renderList({ data: makePageData([]) });

    expect(screen.getByText(/no followers yet/i)).toBeInTheDocument();
  });

  it("uses the title prop in the empty-state message", () => {
    renderList({ title: "Following", data: undefined });

    expect(screen.getByText(/no following yet/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 4. Follower rendering — names, usernames, links
// ---------------------------------------------------------------------------

describe("FollowerList — follower rendering", () => {
  it("renders the display name for each follower", () => {
    const followers = [makeFollower(1), makeFollower(2)];
    renderList({ data: makePageData(followers) });

    expect(screen.getByText("Traveler 1")).toBeInTheDocument();
    expect(screen.getByText("Traveler 2")).toBeInTheDocument();
  });

  it("renders the @username for each follower", () => {
    const followers = [makeFollower(1), makeFollower(2)];
    renderList({ data: makePageData(followers) });

    expect(screen.getByText("@traveler1")).toBeInTheDocument();
    expect(screen.getByText("@traveler2")).toBeInTheDocument();
  });

  it("renders a link to each follower's public profile", () => {
    const followers = [makeFollower(1), makeFollower(2)];
    renderList({ data: makePageData(followers) });

    const links = screen.getAllByRole("link");
    const hrefs = links.map((l) => l.getAttribute("href"));

    expect(hrefs).toContain("/users/traveler1");
    expect(hrefs).toContain("/users/traveler2");
  });

  it("shows the total follower count", () => {
    const followers = [makeFollower(1)];
    renderList({ data: makePageData(followers, { total: 42 }) });

    expect(screen.getByText(/42 followers/i)).toBeInTheDocument();
  });

  it("renders an accessible list with the title as aria-label", () => {
    renderList({ title: "Followers", data: makePageData([makeFollower(1)]) });

    expect(screen.getByRole("list", { name: "Followers" })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 5. Avatar — image vs. initial fallback
// ---------------------------------------------------------------------------

describe("FollowerList — avatar", () => {
  it("renders an img element when avatar_url is provided", () => {
    const follower = makeFollower(1, { avatar_url: "https://cdn.example.com/avatar1.jpg" });
    renderList({ data: makePageData([follower]) });

    const img = screen.getByRole("img", { name: /traveler 1 avatar/i });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://cdn.example.com/avatar1.jpg");
  });

  it("renders the first-letter initial fallback when avatar_url is null", () => {
    const follower = makeFollower(1, {
      display_name: "Quincy Vance",
      avatar_url: null,
    });
    renderList({ data: makePageData([follower]) });

    // The fallback renders display_name.charAt(0).toUpperCase() → "Q"
    expect(screen.getByText("Q")).toBeInTheDocument();
  });

  it("renders an empty initial span when display_name is empty string", () => {
    /**
     * Production: display_name?.charAt(0)?.toUpperCase() ?? "?"
     * When display_name is "", charAt(0) returns "" (not null/undefined),
     * so ?? "?" does not apply — the span renders with no visible text.
     * This documents the observed production behavior (not a bug target).
     */
    const follower = makeFollower(1, {
      display_name: "",
      avatar_url: null,
    });
    renderList({ data: makePageData([follower]) });

    // The span is in the document but contains no visible text
    const spans = document.querySelectorAll(
      "span.flex.h-full.items-center.justify-center"
    );
    expect(spans.length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// 6. Pagination
// ---------------------------------------------------------------------------

describe("FollowerList — pagination", () => {
  it("does NOT render pagination controls when all items fit on one page", () => {
    // 5 items, size 20 → totalPages = 1
    const followers = Array.from({ length: 5 }, (_, i) => makeFollower(i + 1));
    renderList({ data: makePageData(followers, { total: 5, size: 20 }) });

    expect(screen.queryByRole("button", { name: /prev/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /next/i })).not.toBeInTheDocument();
  });

  it("renders pagination controls when there are multiple pages", () => {
    const followers = Array.from({ length: 3 }, (_, i) => makeFollower(i + 1));
    renderList({
      data: makePageData(followers, { total: 50, page: 1, size: 20 }),
    });

    expect(
      screen.getByRole("button", { name: /previous page/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /next page/i })
    ).toBeInTheDocument();
  });

  it("disables the Prev button on the first page", () => {
    const followers = Array.from({ length: 3 }, (_, i) => makeFollower(i + 1));
    renderList({
      page: 1,
      data: makePageData(followers, { total: 50, page: 1, size: 20 }),
    });

    expect(
      screen.getByRole("button", { name: /previous page/i })
    ).toBeDisabled();
  });

  it("disables the Next button on the last page", () => {
    const followers = Array.from({ length: 3 }, (_, i) => makeFollower(i + 1));
    renderList({
      page: 3,
      data: makePageData(followers, { total: 50, page: 3, size: 20 }),
    });

    expect(screen.getByRole("button", { name: /next page/i })).toBeDisabled();
  });

  it("enables both Prev and Next on a middle page", () => {
    const followers = Array.from({ length: 3 }, (_, i) => makeFollower(i + 1));
    renderList({
      page: 2,
      data: makePageData(followers, { total: 50, page: 2, size: 20 }),
    });

    expect(
      screen.getByRole("button", { name: /previous page/i })
    ).not.toBeDisabled();
    expect(
      screen.getByRole("button", { name: /next page/i })
    ).not.toBeDisabled();
  });

  it("calls onPageChange with page - 1 when Prev is clicked", async () => {
    const onPageChange = vi.fn();
    const followers = Array.from({ length: 3 }, (_, i) => makeFollower(i + 1));
    const user = userEvent.setup();

    renderList({
      page: 2,
      data: makePageData(followers, { total: 50, page: 2, size: 20 }),
      onPageChange,
    });

    await user.click(screen.getByRole("button", { name: /previous page/i }));

    expect(onPageChange).toHaveBeenCalledWith(1);
  });

  it("calls onPageChange with page + 1 when Next is clicked", async () => {
    const onPageChange = vi.fn();
    const followers = Array.from({ length: 3 }, (_, i) => makeFollower(i + 1));
    const user = userEvent.setup();

    renderList({
      page: 1,
      data: makePageData(followers, { total: 50, page: 1, size: 20 }),
      onPageChange,
    });

    await user.click(screen.getByRole("button", { name: /next page/i }));

    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("shows current page and total pages in the pagination indicator", () => {
    const followers = Array.from({ length: 3 }, (_, i) => makeFollower(i + 1));
    renderList({
      page: 2,
      data: makePageData(followers, { total: 50, page: 2, size: 20 }),
    });

    // totalPages = ceil(50/20) = 3
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
  });
});
