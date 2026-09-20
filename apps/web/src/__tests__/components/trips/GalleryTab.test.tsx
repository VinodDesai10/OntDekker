/**
 * Tests for the GalleryTab component (CP-TRIP-3D)
 *
 * Tests directly against GalleryTab — no workspace wrapper.
 *
 * Coverage:
 *  1.  Loading state renders skeleton placeholders
 *  2.  Empty gallery state shows "No photos yet." message
 *  3.  Real gallery images render from API data
 *  4.  Multiple gallery images render (all items shown)
 *  5.  No hardcoded/mock images — rendered src comes from API data
 *  6.  API error state shows error card
 *  7.  Broken/missing image URL shows placeholder fallback (via onError)
 *  8.  Gallery is read-only — no upload button visible
 *  9.  Photo caption renders on photo tile
 * 10.  Photo with null caption does not crash
 *
 * Strategy:
 *  - SWR mocked at module boundary (vi.mock).
 *  - No network calls; all data driven by test fixtures.
 *  - Renders GalleryTab directly (no ExpeditionWorkspaceView wrapper).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// Mocks — declared BEFORE module-under-test imports
// ---------------------------------------------------------------------------

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  useParams: () => ({ id: "expedition-test-id" }),
}));

// motion/react mock — suppress animation in tests
vi.mock("motion/react", () => ({
  motion: {
    div: ({
      children,
      ...rest
    }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div {...rest}>{children}</div>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// SWR mock — controlled via swrMockFn
type UseSWRResult<T> = {
  data: T | undefined;
  isLoading: boolean;
  error: unknown;
};

let swrMockFn: (key: unknown, fetcher: unknown, opts: unknown) => UseSWRResult<unknown>;

vi.mock("swr", () => ({
  default: (key: unknown, fetcher: unknown, opts: unknown) => swrMockFn(key, fetcher, opts),
  useSWRConfig: () => ({ mutate: vi.fn() }),
}));

// Cache module mock
vi.mock("@/services/cache", () => ({
  swrFetcher: vi.fn(),
  swrFetcherWithParams: vi.fn(),
  expeditionKeys: {
    gallery: (id: string) => `/expeditions/api/v1/expeditions/${id}/gallery`,
    gear: (id: string) => `/expeditions/api/v1/expeditions/${id}/gear`,
    participants: (id: string) => `/expeditions/api/v1/expeditions/${id}/participants`,
    mine: () => ["/expeditions/api/v1/expeditions", {}],
    byId: (id: string) => `/expeditions/api/v1/expeditions/${id}`,
    itinerary: (id: string) => `/expeditions/api/v1/expeditions/${id}/itinerary`,
  },
  tripKeys: {
    all: () => ["/api/v1/trips", {}],
    byId: (id: string) => `/api/v1/trips/${id}`,
    mine: () => ["/api/v1/users/me/trips", {}],
  },
}));

// ---------------------------------------------------------------------------
// Import under test AFTER mocks
// ---------------------------------------------------------------------------

import GalleryTab from "@/components/trips/GalleryTab";
import type { GalleryPhoto } from "@/types";
import type { GalleryResponse } from "@/components/trips/GalleryTab";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const EXPEDITION_ID = "expedition-gallery-test";

function makePhoto(overrides: Partial<GalleryPhoto> = {}): GalleryPhoto {
  return {
    id: "photo-1",
    expeditionId: EXPEDITION_ID,
    imageUrl: "https://cdn.example.com/photo-1.jpg",
    caption: "Summit view",
    displayOrder: 0,
    uploadedBy: "user-abc",
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function makeGalleryResponse(photos: GalleryPhoto[] = []): GalleryResponse {
  return {
    expeditionId: EXPEDITION_ID,
    photos,
    totalPhotos: photos.length,
  };
}

// ---------------------------------------------------------------------------
// SWR setup helpers
// ---------------------------------------------------------------------------

function setupSwr({
  galleryData,
  galleryError,
  isLoading = false,
}: {
  galleryData?: GalleryResponse | null;
  galleryError?: Error;
  isLoading?: boolean;
}) {
  swrMockFn = () => {
    if (isLoading) {
      return { data: undefined, isLoading: true, error: undefined };
    }
    if (galleryError) {
      return { data: undefined, isLoading: false, error: galleryError };
    }
    return {
      data: galleryData ?? makeGalleryResponse(),
      isLoading: false,
      error: undefined,
    };
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("GalleryTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1. Loading state
  it("shows a loading skeleton while gallery is fetching", () => {
    setupSwr({ isLoading: true });
    render(<GalleryTab expeditionId={EXPEDITION_ID} />);
    expect(screen.getByTestId("gallery-loading")).toBeTruthy();
    // No images should be visible during loading
    expect(screen.queryByRole("img")).toBeNull();
  });

  // 2. Empty gallery state
  it("shows empty state when the expedition has no photos", () => {
    setupSwr({ galleryData: makeGalleryResponse([]) });
    render(<GalleryTab expeditionId={EXPEDITION_ID} />);
    expect(screen.getByTestId("gallery-empty")).toBeTruthy();
    expect(screen.getByText("No photos yet.")).toBeTruthy();
    expect(
      screen.getByText("Photos shared by expedition members will appear here."),
    ).toBeTruthy();
    // No images rendered
    expect(screen.queryByRole("img")).toBeNull();
  });

  // 3. Real gallery images render from API data
  it("renders a gallery image using the real URL from the API", () => {
    const photo = makePhoto({
      id: "photo-real",
      imageUrl: "https://cdn.example.com/real-photo.jpg",
      caption: "Camp site",
    });
    setupSwr({ galleryData: makeGalleryResponse([photo]) });
    render(<GalleryTab expeditionId={EXPEDITION_ID} />);

    expect(screen.getByTestId("gallery-grid")).toBeTruthy();
    const img = screen.getByRole("img", { name: "Camp site" });
    expect(img).toBeTruthy();
    expect(img).toHaveAttribute("src", "https://cdn.example.com/real-photo.jpg");
  });

  // 4. Multiple gallery images render
  it("renders all photos returned by the API", () => {
    const photos = [
      makePhoto({ id: "photo-a", imageUrl: "https://cdn.example.com/a.jpg", caption: "Photo A" }),
      makePhoto({ id: "photo-b", imageUrl: "https://cdn.example.com/b.jpg", caption: "Photo B" }),
      makePhoto({ id: "photo-c", imageUrl: "https://cdn.example.com/c.jpg", caption: "Photo C" }),
    ];
    setupSwr({ galleryData: makeGalleryResponse(photos) });
    render(<GalleryTab expeditionId={EXPEDITION_ID} />);

    expect(screen.getByTestId("gallery-grid")).toBeTruthy();
    expect(screen.getByTestId("gallery-photo-photo-a")).toBeTruthy();
    expect(screen.getByTestId("gallery-photo-photo-b")).toBeTruthy();
    expect(screen.getByTestId("gallery-photo-photo-c")).toBeTruthy();
    expect(screen.getAllByRole("img")).toHaveLength(3);
  });

  // 5. No hardcoded/mock images — rendered src must match API data
  it("does not render any images when the API returns an empty list", () => {
    setupSwr({ galleryData: makeGalleryResponse([]) });
    render(<GalleryTab expeditionId={EXPEDITION_ID} />);
    // Gallery grid should not render
    expect(screen.queryByTestId("gallery-grid")).toBeNull();
    // No img tags
    expect(screen.queryByRole("img")).toBeNull();
    // Empty state shown instead
    expect(screen.getByTestId("gallery-empty")).toBeTruthy();
  });

  // 6. API error state
  it("shows error card when the gallery API fails", () => {
    setupSwr({ galleryError: new Error("Network error") });
    render(<GalleryTab expeditionId={EXPEDITION_ID} />);
    expect(screen.getByTestId("gallery-error")).toBeTruthy();
    expect(screen.getByText("Failed to load gallery.")).toBeTruthy();
    expect(screen.getByText("Unable to fetch photos. Please try again later.")).toBeTruthy();
    // No images rendered
    expect(screen.queryByRole("img")).toBeNull();
  });

  // 7. Broken/missing image URL shows placeholder fallback
  it("shows a broken-image placeholder when the image URL fails to load", () => {
    const photo = makePhoto({
      id: "photo-broken",
      imageUrl: "https://cdn.example.com/missing.jpg",
      caption: "Broken photo",
    });
    setupSwr({ galleryData: makeGalleryResponse([photo]) });
    render(<GalleryTab expeditionId={EXPEDITION_ID} />);

    // Initially the img is rendered
    const img = screen.getByRole("img", { name: "Broken photo" });
    expect(img).toBeTruthy();

    // Simulate the browser failing to load the image
    fireEvent.error(img);

    // After onError fires, the img is replaced by the broken placeholder
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.getByTestId("gallery-photo-broken-photo-broken")).toBeTruthy();
  });

  // 8. Gallery is read-only — no upload button
  it("does not render an upload button (read-only — MinIO not implemented)", () => {
    const photo = makePhoto();
    setupSwr({ galleryData: makeGalleryResponse([photo]) });
    render(<GalleryTab expeditionId={EXPEDITION_ID} />);

    // No upload controls should exist
    expect(screen.queryByRole("button", { name: /upload/i })).toBeNull();
    expect(screen.queryByTestId("gallery-upload")).toBeNull();
  });

  // 9. Photo caption renders on the photo tile
  it("renders the caption text for a photo with a caption", () => {
    const photo = makePhoto({
      id: "photo-caption",
      caption: "Early morning mist",
    });
    setupSwr({ galleryData: makeGalleryResponse([photo]) });
    render(<GalleryTab expeditionId={EXPEDITION_ID} />);

    // Caption is in the img alt attribute
    const img = screen.getByRole("img", { name: "Early morning mist" });
    expect(img).toBeTruthy();
    expect(img).toHaveAttribute("alt", "Early morning mist");
  });

  // 10. Photo with null caption does not crash
  it("renders without error when a photo has a null caption", () => {
    const photo = makePhoto({
      id: "photo-no-caption",
      caption: null,
    });
    setupSwr({ galleryData: makeGalleryResponse([photo]) });
    // Should not throw
    expect(() => render(<GalleryTab expeditionId={EXPEDITION_ID} />)).not.toThrow();

    // The image should still render with a generic alt text
    const img = screen.getByRole("img", { name: "Gallery photo" });
    expect(img).toBeTruthy();
  });
});
