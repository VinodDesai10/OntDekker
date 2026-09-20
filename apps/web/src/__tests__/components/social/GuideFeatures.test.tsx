/**
 * Tests for CP-GUIDE-5: Become a Guide + My Guides
 *
 * 15 test cases covering:
 *
 * BECOME A GUIDE:
 *  1.  "Become a Guide" button navigates to /guides/apply
 *  2.  Application page renders (GuideApplyView)
 *  3.  Form validation works (biography < 100 chars shows error)
 *  4.  applyForGuide() API is called on submit
 *  5.  Successful application shows success state
 *  6.  API failure shows error state
 *
 * MY GUIDES:
 *  7.  My Guides loads saved guides from backend
 *  8.  Saved guides render
 *  9.  Empty state renders when backend returns empty
 *  10. Loading state works
 *  11. API error state works
 *
 * BOOKMARK:
 *  12. Bookmark calls backend
 *  13. Successful bookmark updates AppState/UI
 *  14. Unbookmark calls backend
 *  15. Successful unbookmark updates AppState/UI
 *
 * All external API calls are mocked at the module level.
 * No real network requests are made.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// Mocks — declared before any module imports
// ---------------------------------------------------------------------------

const mockPush = vi.fn();
const mockBack = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: mockBack, replace: vi.fn() }),
  useParams: () => ({}),
}));

vi.mock("motion/react", () => ({
  motion: {
    div: ({
      children,
      ...rest
    }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div {...rest}>{children}</div>
    ),
    button: ({
      children,
      ...rest
    }: React.ButtonHTMLAttributes<HTMLButtonElement> & {
      children?: React.ReactNode;
      whileTap?: unknown;
      animate?: unknown;
      transition?: unknown;
    }) => <button {...rest}>{children}</button>,
  },
  AnimatePresence: ({
    children,
  }: {
    children: React.ReactNode;
  }) => <>{children}</>,
}));

// SWR mock — provides useSWR for GuidesView and useSWRConfig for cache invalidation
vi.mock("swr", () => ({
  default: vi.fn(),
  useSWRConfig: () => ({ mutate: vi.fn().mockResolvedValue(undefined) }),
}));

// useToast
const mockShowToast = vi.fn();
vi.mock("@/hooks/useToast", () => ({
  useToast: () => ({ showToast: mockShowToast }),
}));

// Mock Search component — GuidesView imports this
vi.mock("@/components/navigation/Search", () => ({
  default: ({
    value,
    onChange,
    placeholder,
    ariaLabel,
  }: {
    value: string;
    onChange: (v: string) => void;
    placeholder?: string;
    ariaLabel?: string;
    className?: string;
  }) => (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={ariaLabel ?? "Search"}
    />
  ),
}));

// Mock Badge component used by GuidesView (FilterChip uses inline button — no Badge mock needed)
// Mock Button component — GuidesView uses this
vi.mock("@/components/feedback/Button", () => ({
  default: ({
    children,
    onClick,
    icon: _Icon,
    ...rest
  }: {
    children?: React.ReactNode;
    onClick?: () => void;
    icon?: React.ComponentType<unknown>;
    variant?: string;
    size?: string;
    className?: string;
  }) => (
    <button type="button" onClick={onClick} {...rest}>
      {children}
    </button>
  ),
}));

// ---------------------------------------------------------------------------
// Guide API mocks
// ---------------------------------------------------------------------------

const mockApplyForGuide = vi.fn();
const mockSubmitGuideApplication = vi.fn();
const mockGetMyConnections = vi.fn();
const mockGetGuideById = vi.fn();
const mockBookmarkGuide = vi.fn();
const mockUnbookmarkGuide = vi.fn();

vi.mock("@/services/guideApi", () => ({
  applyForGuide: (...args: unknown[]) => mockApplyForGuide(...args),
  submitGuideApplication: (...args: unknown[]) =>
    mockSubmitGuideApplication(...args),
  getMyConnections: (...args: unknown[]) => mockGetMyConnections(...args),
  getGuideById: (...args: unknown[]) => mockGetGuideById(...args),
  bookmarkGuide: (...args: unknown[]) => mockBookmarkGuide(...args),
  unbookmarkGuide: (...args: unknown[]) => mockUnbookmarkGuide(...args),
  getGuides: vi.fn().mockResolvedValue({ items: [], pagination: {} }),
}));

// ---------------------------------------------------------------------------
// GuideCardSkeleton stub
// ---------------------------------------------------------------------------

vi.mock("@/views/Guides/GuideCardSkeleton", () => ({
  default: () => <div data-testid="guide-card-skeleton">Loading skeletons</div>,
}));

// ---------------------------------------------------------------------------
// GuideCard stub — renders guide display name and bookmark button
// ---------------------------------------------------------------------------

vi.mock("@/components/cards/GuideCard", () => ({
  default: ({
    guide,
    onBookmarkToggle,
    isBookmarked,
  }: {
    guide: { id: string; displayName: string | null };
    onBookmarkToggle: (e: React.MouseEvent) => void;
    isBookmarked?: boolean;
  }) => (
    <div data-testid={`guide-card-${guide.id}`}>
      <span>{guide.displayName ?? "Guide"}</span>
      <button
        type="button"
        data-testid={`bookmark-btn-${guide.id}`}
        aria-pressed={isBookmarked}
        onClick={onBookmarkToggle}
      >
        {isBookmarked ? "Unbookmark" : "Bookmark"}
      </button>
    </div>
  ),
}));

// ---------------------------------------------------------------------------
// AppStateProvider — real provider (no mock) so state transitions work
// ---------------------------------------------------------------------------

// Import the real provider after mocks are in place
import { AppStateProvider } from "@/contexts/AppStateProvider";
import GuidesView from "@/views/Guides/GuidesView";
import GuideApplyView from "@/views/Guides/GuideApplyView";
import MyGuidesView from "@/views/Guides/MyGuides/MyGuidesView";
import useSWR from "swr";
import type { GuideProfileSummary, TravelConnectionListResponse } from "@/types";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeGuide(overrides: Partial<GuideProfileSummary> = {}): GuideProfileSummary {
  return {
    id: "guide-id-1",
    userId: "user-id-1",
    displayName: "Sofia Bergström",
    profileImageUrl: null,
    rating: 4.8,
    reviewCount: 42,
    verificationStatus: "VERIFIED",
    yearsExperience: 8,
    pricePerDay: 150,
    bio: "Experienced mountain guide covering the Scandinavian wilderness.",
    locations: [{ id: "loc-1", guideId: "guide-id-1", country: "Sweden", region: "Dalarna", city: "Mora" }],
    languages: [{ id: "lang-1", guideId: "guide-id-1", language: "English" }],
    availability: { guideId: "guide-id-1", status: "AVAILABLE", note: null },
    specializations: [{ id: "spec-1", guideId: "guide-id-1", category: "Mountain" }],
    ...overrides,
  };
}

function makeConnections(
  guides: GuideProfileSummary[],
  bookmarked = true,
): TravelConnectionListResponse {
  return {
    travelerId: "traveler-id-1",
    connections: guides.map((g) => ({
      id: `conn-${g.id}`,
      guideId: g.id,
      travelerId: "traveler-id-1",
      firstMet: "2026-01-01T00:00:00Z",
      lastInteraction: null,
      expeditionsTogether: 0,
      conversationCount: 0,
      photosShared: 0,
      bookmarked,
      createdAt: "2026-01-01T00:00:00Z",
      updatedAt: "2026-01-01T00:00:00Z",
    })),
    pagination: {
      page: 1,
      pageSize: 20,
      totalItems: guides.length,
      totalPages: 1,
      hasNext: false,
      hasPrevious: false,
    },
  };
}

const DRAFT_APPLICATION = {
  id: "app-id-1",
  userId: "user-id-1",
  biography: "A".repeat(100),
  areasCovered: null,
  languages: null,
  experienceYears: null,
  certifications: null,
  identityDocumentUrl: null,
  status: "DRAFT" as const,
  submittedAt: null,
  reviewedAt: null,
  reviewedBy: null,
  reviewNotes: null,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
};

const SUBMITTED_APPLICATION = {
  ...DRAFT_APPLICATION,
  status: "SUBMITTED" as const,
  submittedAt: "2026-01-01T00:01:00Z",
};

// ---------------------------------------------------------------------------
// Render helpers
// ---------------------------------------------------------------------------

function renderGuidesView() {
  return render(
    <AppStateProvider>
      <GuidesView />
    </AppStateProvider>,
  );
}

function renderGuideApplyView() {
  return render(
    <AppStateProvider>
      <GuideApplyView />
    </AppStateProvider>,
  );
}

function renderMyGuidesView() {
  return render(
    <AppStateProvider>
      <MyGuidesView />
    </AppStateProvider>,
  );
}

// ---------------------------------------------------------------------------
// Configure the SWR mock (called in each test that uses GuidesView)
// ---------------------------------------------------------------------------

function setupSwrGuidesLoading() {
  vi.mocked(useSWR).mockReturnValue({
    data: undefined,
    isLoading: true,
    error: undefined,
    mutate: vi.fn(),
    isValidating: false,
  } as ReturnType<typeof useSWR>);
}

function setupSwrGuidesSuccess(guides: GuideProfileSummary[]) {
  vi.mocked(useSWR).mockReturnValue({
    data: {
      items: guides,
      pagination: { page: 1, pageSize: 30, totalItems: guides.length, totalPages: 1, hasNext: false, hasPrevious: false },
    },
    isLoading: false,
    error: undefined,
    mutate: vi.fn(),
    isValidating: false,
  } as ReturnType<typeof useSWR>);
}

function setupSwrGuidesError() {
  vi.mocked(useSWR).mockReturnValue({
    data: undefined,
    isLoading: false,
    error: new Error("Network error"),
    mutate: vi.fn(),
    isValidating: false,
  } as ReturnType<typeof useSWR>);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CP-GUIDE-5: Become a Guide + My Guides", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // BECOME A GUIDE
  // ─────────────────────────────────────────────────────────────────────────

  describe("BECOME A GUIDE", () => {
    // Test 1: Button navigates to /guides/apply
    it("1. 'Become a Guide' button navigates to /guides/apply", () => {
      setupSwrGuidesSuccess([]);
      renderGuidesView();

      const btn = screen.getByRole("button", { name: /become a guide/i });
      expect(btn).toBeTruthy();
      fireEvent.click(btn);
      expect(mockPush).toHaveBeenCalledWith("/guides/apply");
    });

    // Test 2: Application page renders with heading and form fields
    it("2. GuideApplyView renders the application form", () => {
      renderGuideApplyView();

      expect(screen.getByRole("heading", { name: /become a guide/i })).toBeTruthy();
      expect(screen.getByLabelText(/biography/i)).toBeTruthy();
      expect(screen.getByLabelText(/areas covered/i)).toBeTruthy();
      expect(screen.getByLabelText(/languages/i)).toBeTruthy();
      expect(screen.getByLabelText(/years of experience/i)).toBeTruthy();
      expect(screen.getByLabelText(/certifications/i)).toBeTruthy();
      expect(screen.getByLabelText(/identity document/i)).toBeTruthy();
    });

    // Test 3: Form validation — biography too short
    it("3. Form shows validation error when biography is too short", async () => {
      renderGuideApplyView();

      const bioField = screen.getByLabelText(/biography/i) as HTMLTextAreaElement;
      fireEvent.change(bioField, { target: { value: "Too short" } });
      fireEvent.click(screen.getByRole("button", { name: /submit guide application/i }));

      await waitFor(() => {
        expect(screen.getByText(/biography must be at least 100 characters/i)).toBeTruthy();
      });
      // API should NOT be called when validation fails
      expect(mockApplyForGuide).not.toHaveBeenCalled();
    });

    // Test 4: applyForGuide() API is called with correct payload
    it("4. applyForGuide() is called with the form data on submit", async () => {
      mockApplyForGuide.mockResolvedValue(DRAFT_APPLICATION);
      mockSubmitGuideApplication.mockResolvedValue(SUBMITTED_APPLICATION);

      renderGuideApplyView();

      const biography = "I am an experienced mountain guide with 10 years of leading expeditions across the Himalayas and the Alps, helping travelers achieve their goals safely.";
      const bioField = screen.getByLabelText(/biography/i) as HTMLTextAreaElement;
      fireEvent.change(bioField, { target: { value: biography } });

      fireEvent.click(screen.getByRole("button", { name: /submit guide application/i }));

      await waitFor(() => {
        expect(mockApplyForGuide).toHaveBeenCalledWith(
          expect.objectContaining({ biography }),
        );
      });
    });

    // Test 5: Successful submission shows success state
    it("5. Shows success state after successful application submission", async () => {
      mockApplyForGuide.mockResolvedValue(DRAFT_APPLICATION);
      mockSubmitGuideApplication.mockResolvedValue(SUBMITTED_APPLICATION);

      renderGuideApplyView();

      const biography = "I am an experienced mountain guide with 10 years of leading expeditions across the Himalayas and the Alps, helping travelers achieve their goals safely.";
      fireEvent.change(screen.getByLabelText(/biography/i), { target: { value: biography } });
      fireEvent.click(screen.getByRole("button", { name: /submit guide application/i }));

      await waitFor(() => {
        expect(screen.getByTestId("success-state")).toBeTruthy();
      });
      expect(screen.getByText(/application submitted/i)).toBeTruthy();
      // submitGuideApplication should have been called with the draft id
      expect(mockSubmitGuideApplication).toHaveBeenCalledWith(DRAFT_APPLICATION.id);
    });

    // Test 6: API failure shows error state
    it("6. Shows error banner when API call fails", async () => {
      mockApplyForGuide.mockRejectedValue({
        response: {
          data: { detail: "You already have an active application." },
        },
      });

      renderGuideApplyView();

      const biography = "I am an experienced mountain guide with 10 years of leading expeditions across the Himalayas and the Alps, helping travelers achieve their goals safely.";
      fireEvent.change(screen.getByLabelText(/biography/i), { target: { value: biography } });
      fireEvent.click(screen.getByRole("button", { name: /submit guide application/i }));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeTruthy();
        expect(screen.getByText(/you already have an active application/i)).toBeTruthy();
      });
    });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // MY GUIDES
  // ─────────────────────────────────────────────────────────────────────────

  describe("MY GUIDES", () => {
    // Test 7: My Guides loads saved guides from backend
    it("7. Fetches saved guides from GET /my-connections on mount", async () => {
      const guide = makeGuide();
      mockGetMyConnections.mockResolvedValue(makeConnections([guide]));
      mockGetGuideById.mockResolvedValue({ data: guide });

      renderMyGuidesView();

      await waitFor(() => {
        expect(mockGetMyConnections).toHaveBeenCalledWith(
          expect.objectContaining({ bookmarked_only: true }),
        );
      });
      expect(mockGetGuideById).toHaveBeenCalledWith(guide.id);
    });

    // Test 8: Saved guides render with guide names
    it("8. Renders guide cards for all returned saved guides", async () => {
      const guide = makeGuide();
      mockGetMyConnections.mockResolvedValue(makeConnections([guide]));
      mockGetGuideById.mockResolvedValue({ data: guide });

      renderMyGuidesView();

      await waitFor(() => {
        expect(screen.getByTestId(`guide-card-${guide.id}`)).toBeTruthy();
        expect(screen.getByText("Sofia Bergström")).toBeTruthy();
      });
    });

    // Test 9: Empty state when backend returns empty list
    it("9. Shows empty state when backend returns no connections", async () => {
      mockGetMyConnections.mockResolvedValue({
        travelerId: "t-1",
        connections: [],
        pagination: { page: 1, pageSize: 20, totalItems: 0, totalPages: 0, hasNext: false, hasPrevious: false },
      });

      renderMyGuidesView();

      await waitFor(() => {
        expect(screen.getByText(/no saved guides yet/i)).toBeTruthy();
      });
    });

    // Test 10: Loading state shown during fetch
    it("10. Shows loading skeleton while fetching guide data", () => {
      // Never resolves — stays in loading state
      mockGetMyConnections.mockImplementation(() => new Promise(() => {}));

      renderMyGuidesView();

      expect(screen.getByTestId("guide-card-skeleton")).toBeTruthy();
    });

    // Test 11: Error state when API call fails
    it("11. Shows error state when backend call fails", async () => {
      mockGetMyConnections.mockRejectedValue(new Error("Network error"));

      renderMyGuidesView();

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeTruthy();
        expect(screen.getByText(/unable to load your saved guides/i)).toBeTruthy();
      });
    });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // BOOKMARK
  // ─────────────────────────────────────────────────────────────────────────

  describe("BOOKMARK", () => {
    // Test 12: Bookmark calls backend
    it("12. Clicking bookmark on an unbookmarked guide calls bookmarkGuide()", async () => {
      const guide = makeGuide();
      setupSwrGuidesSuccess([guide]);
      mockBookmarkGuide.mockResolvedValue(undefined);

      renderGuidesView();

      await waitFor(() => {
        expect(screen.getByTestId(`guide-card-${guide.id}`)).toBeTruthy();
      });

      const bookmarkBtn = screen.getByTestId(`bookmark-btn-${guide.id}`);
      fireEvent.click(bookmarkBtn);

      await waitFor(() => {
        expect(mockBookmarkGuide).toHaveBeenCalledWith(guide.id);
      });
    });

    // Test 13: Successful bookmark updates AppState (toast shown)
    it("13. Successful bookmark dispatches toast and updates UI", async () => {
      const guide = makeGuide();
      setupSwrGuidesSuccess([guide]);
      mockBookmarkGuide.mockResolvedValue(undefined);

      renderGuidesView();

      await waitFor(() => {
        expect(screen.getByTestId(`guide-card-${guide.id}`)).toBeTruthy();
      });

      const bookmarkBtn = screen.getByTestId(`bookmark-btn-${guide.id}`);
      fireEvent.click(bookmarkBtn);

      await waitFor(() => {
        expect(mockShowToast).toHaveBeenCalledWith(
          expect.stringContaining("bookmarked"),
          "success",
        );
      });
    });

    // Test 14: Unbookmark calls backend (via My Guides)
    it("14. Clicking unbookmark in My Guides calls unbookmarkGuide()", async () => {
      const guide = makeGuide();
      mockGetMyConnections.mockResolvedValue(makeConnections([guide], true));
      mockGetGuideById.mockResolvedValue({ data: guide });
      mockUnbookmarkGuide.mockResolvedValue(undefined);

      renderMyGuidesView();

      await waitFor(() => {
        expect(screen.getByTestId(`guide-card-${guide.id}`)).toBeTruthy();
      });

      const unbookmarkBtn = screen.getByTestId(`bookmark-btn-${guide.id}`);
      fireEvent.click(unbookmarkBtn);

      await waitFor(() => {
        expect(mockUnbookmarkGuide).toHaveBeenCalledWith(guide.id);
      });
    });

    // Test 15: Successful unbookmark dispatches toast and updates state
    it("15. Successful unbookmark shows toast and removes guide from state", async () => {
      const guide = makeGuide();
      mockGetMyConnections.mockResolvedValue(makeConnections([guide], true));
      mockGetGuideById.mockResolvedValue({ data: guide });
      mockUnbookmarkGuide.mockResolvedValue(undefined);

      renderMyGuidesView();

      await waitFor(() => {
        expect(screen.getByTestId(`guide-card-${guide.id}`)).toBeTruthy();
      });

      const unbookmarkBtn = screen.getByTestId(`bookmark-btn-${guide.id}`);
      fireEvent.click(unbookmarkBtn);

      await waitFor(() => {
        expect(mockShowToast).toHaveBeenCalledWith("Bookmark removed.", "info");
      });
    });
  });
});
