/**
 * Tests for the PackingTab component (CP-TRIP-3C)
 *
 * Tests:
 *  1.  Loading state renders a skeleton
 *  2.  Empty state when no items
 *  3.  Real packing items render with name and weight
 *  4.  Packed item renders with aria-pressed=true; unpacked with aria-pressed=false
 *  5.  Weight summary badge shows the real classification from the API
 *  6.  No hardcoded/mock packing data (items must come from API, not fixture)
 *  7.  Toggle item packed state (active participant who owns the item)
 *  8.  Delete item (active participant who owns the item)
 *  9.  Non-participant cannot see toggle/delete controls
 * 10.  Active participant sees "Add Gear Item" button
 * 11.  Non-participant does not see "Add Gear Item" button
 * 12.  Add item form — submit adds item and revalidates
 * 13.  API failure state renders error card
 * 14.  Organiser can delete any item (not just their own)
 *
 * Strategy:
 *  - All API calls mocked at the service-module boundary (vi.mock).
 *  - SWR is used by the component; we mock useSWR to return controlled data.
 *  - No network calls, no MSW needed.
 *  - Directly renders PackingTab component (no workspace wrapper needed).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// Mocks — declared BEFORE module-under-test imports
// ---------------------------------------------------------------------------

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  useParams: () => ({ id: "expedition-test-id" }),
}));

// motion/react mock — needed for motion.div components in PackingTab
vi.mock("motion/react", () => ({
  motion: {
    div: ({
      children,
      ...rest
    }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div {...rest}>{children}</div>
    ),
  },
  AnimatePresence: ({
    children,
  }: {
    children: React.ReactNode;
  }) => <>{children}</>,
}));

// SWR: mock both useSWR and useSWRConfig
const mockMutate = vi.fn().mockResolvedValue(undefined);

type UseSWRResult<T> = {
  data: T | undefined;
  isLoading: boolean;
  error: unknown;
};

let swrMockFn: (key: unknown, fetcher: unknown, opts: unknown) => UseSWRResult<unknown>;

vi.mock("swr", () => ({
  default: (key: unknown, fetcher: unknown, opts: unknown) => swrMockFn(key, fetcher, opts),
  useSWRConfig: () => ({ mutate: mockMutate }),
}));

// SWR cache key module
vi.mock("@/services/cache", () => ({
  swrFetcher: vi.fn(),
  swrFetcherWithParams: vi.fn(),
  expeditionKeys: {
    gear: (id: string) => `/expeditions/api/v1/expeditions/${id}/gear`,
    gallery: (id: string) => `/expeditions/api/v1/expeditions/${id}/gallery`,
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

// Gear mutation API
const mockAddGearItem = vi.fn();
const mockUpdateGearItem = vi.fn();
const mockDeleteGearItem = vi.fn();

vi.mock("@/services/gearApi", () => ({
  addGearItem: (...args: unknown[]) => mockAddGearItem(...args),
  updateGearItem: (...args: unknown[]) => mockUpdateGearItem(...args),
  deleteGearItem: (...args: unknown[]) => mockDeleteGearItem(...args),
}));

// useToast hook
const mockShowToast = vi.fn();
vi.mock("@/hooks/useToast", () => ({
  useToast: () => ({ showToast: mockShowToast }),
}));

// ---------------------------------------------------------------------------
// Import under test AFTER mocks
// ---------------------------------------------------------------------------

import PackingTab from "@/components/trips/PackingTab";
import type { GearItem, PackWeightSummary } from "@/types";
import type { TripParticipant } from "@/types/trip";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const EXPEDITION_ID = "expedition-test-id";

const MY_PARTICIPANT_ACTIVE: TripParticipant = {
  id: "participant-1",
  expedition_id: EXPEDITION_ID,
  user_id: "auth-user-1",
  role: "PARTICIPANT",
  status: "ACTIVE",
  joined_at: "2026-01-01T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const MY_PARTICIPANT_ORGANIZER: TripParticipant = {
  ...MY_PARTICIPANT_ACTIVE,
  id: "participant-organizer",
  role: "ORGANIZER",
};

function makeGearItem(overrides: Partial<GearItem> = {}): GearItem {
  return {
    id: "gear-item-1",
    expeditionId: EXPEDITION_ID,
    name: "Sleeping Bag",
    category: "BASE_PACK",
    weightGrams: 1200,
    quantity: 1,
    isPacked: false,
    addedBy: "auth-user-1",
    ...overrides,
  };
}

function makeSummary(overrides: Partial<PackWeightSummary> = {}): PackWeightSummary {
  return {
    totalWeightGrams: 1200,
    basePackGrams: 1200,
    consumablesGrams: 0,
    wornGearGrams: 0,
    packedItemsCount: 0,
    totalItemsCount: 1,
    classification: "ULTRALIGHT",
    ...overrides,
  };
}

function makeGearListResponse(
  items: GearItem[] = [],
  summaryOverrides: Partial<PackWeightSummary> = {},
) {
  return {
    expeditionId: EXPEDITION_ID,
    items,
    summary: makeSummary({
      totalItemsCount: items.length,
      packedItemsCount: items.filter((i) => i.isPacked).length,
      ...summaryOverrides,
    }),
  };
}

// ---------------------------------------------------------------------------
// Helper: configure swrMockFn for a given gear response
// ---------------------------------------------------------------------------

function setupSwr({
  gearData,
  gearError,
  isLoading = false,
}: {
  gearData?: ReturnType<typeof makeGearListResponse> | null;
  gearError?: Error;
  isLoading?: boolean;
}) {
  swrMockFn = () => {
    if (gearError) {
      return { data: undefined, isLoading: false, error: gearError };
    }
    if (isLoading) {
      return { data: undefined, isLoading: true, error: undefined };
    }
    return { data: gearData ?? makeGearListResponse(), isLoading: false, error: undefined };
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("PackingTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockShowToast.mockReset();
    mockMutate.mockReset().mockResolvedValue(undefined);
  });

  // 1. Loading state
  it("shows a loading skeleton while gear list is fetching", () => {
    setupSwr({ isLoading: true });
    render(<PackingTab expeditionId={EXPEDITION_ID} myParticipant={null} />);
    expect(screen.getByTestId("packing-loading")).toBeTruthy();
  });

  // 2. Empty state
  it("shows empty state when gear list is empty", () => {
    setupSwr({ gearData: makeGearListResponse([]) });
    render(
      <PackingTab expeditionId={EXPEDITION_ID} myParticipant={MY_PARTICIPANT_ACTIVE} />,
    );
    expect(screen.getByTestId("packing-empty")).toBeTruthy();
    expect(screen.getByText("No gear added yet.")).toBeTruthy();
  });

  // 3. Real packing items render
  it("renders real gear items from the API", () => {
    const items = [
      makeGearItem({ id: "item-1", name: "Sleeping Bag", weightGrams: 1200 }),
      makeGearItem({ id: "item-2", name: "Tent", weightGrams: 2500, addedBy: "auth-user-2" }),
    ];
    setupSwr({ gearData: makeGearListResponse(items) });
    render(
      <PackingTab expeditionId={EXPEDITION_ID} myParticipant={MY_PARTICIPANT_ACTIVE} />,
    );
    expect(screen.getByTestId("packing-list")).toBeTruthy();
    expect(screen.getByText("Sleeping Bag")).toBeTruthy();
    expect(screen.getByText("Tent")).toBeTruthy();
  });

  // 4. Packed / unpacked state display
  it("renders aria-pressed=true for packed items and aria-pressed=false for unpacked", () => {
    const items = [
      makeGearItem({ id: "item-packed", name: "Packed Item", isPacked: true }),
      makeGearItem({ id: "item-unpacked", name: "Unpacked Item", isPacked: false }),
    ];
    setupSwr({ gearData: makeGearListResponse(items, { packedItemsCount: 1 }) });
    render(
      <PackingTab expeditionId={EXPEDITION_ID} myParticipant={MY_PARTICIPANT_ACTIVE} />,
    );

    const packedBtn = screen.getByRole("button", { name: /unpack packed item/i });
    expect(packedBtn).toHaveAttribute("aria-pressed", "true");

    const unpackedBtn = screen.getByRole("button", { name: /^pack unpacked item/i });
    expect(unpackedBtn).toHaveAttribute("aria-pressed", "false");
  });

  // 5. Weight summary uses real classification from API (not hardcoded)
  it("shows the real weight classification from the API summary", () => {
    const items = [makeGearItem({ weightGrams: 20000 })];
    setupSwr({
      gearData: makeGearListResponse(items, {
        classification: "HEAVY",
        totalWeightGrams: 20000,
        basePackGrams: 20000,
      }),
    });
    render(
      <PackingTab expeditionId={EXPEDITION_ID} myParticipant={MY_PARTICIPANT_ACTIVE} />,
    );
    // WeightBadge should display "Heavy"
    expect(screen.getByText("Heavy")).toBeTruthy();
  });

  // 6. No hardcoded/mock packing data
  it("does not display any items when the API returns an empty list", () => {
    setupSwr({ gearData: makeGearListResponse([]) });
    render(
      <PackingTab expeditionId={EXPEDITION_ID} myParticipant={MY_PARTICIPANT_ACTIVE} />,
    );
    expect(screen.queryByTestId(/^gear-item-/)).toBeNull();
  });

  // 7. Toggle item — active participant who owns the item
  it("calls updateGearItem to toggle isPacked when toggle button clicked", async () => {
    const item = makeGearItem({
      id: "item-toggle",
      name: "Stove",
      isPacked: false,
      addedBy: "auth-user-1",
    });
    mockUpdateGearItem.mockResolvedValue({ ...item, isPacked: true });
    setupSwr({ gearData: makeGearListResponse([item]) });

    render(
      <PackingTab expeditionId={EXPEDITION_ID} myParticipant={MY_PARTICIPANT_ACTIVE} />,
    );

    const toggleBtn = screen.getByRole("button", { name: /^pack stove/i });
    await act(async () => {
      fireEvent.click(toggleBtn);
    });

    await waitFor(() => {
      expect(mockUpdateGearItem).toHaveBeenCalledWith(
        EXPEDITION_ID,
        "item-toggle",
        { isPacked: true },
      );
    });
  });

  // 8. Delete item — active participant who owns the item
  it("calls deleteGearItem when delete button clicked", async () => {
    const item = makeGearItem({
      id: "item-delete",
      name: "Extra Rope",
      addedBy: "auth-user-1",
    });
    mockDeleteGearItem.mockResolvedValue(undefined);
    setupSwr({ gearData: makeGearListResponse([item]) });

    render(
      <PackingTab expeditionId={EXPEDITION_ID} myParticipant={MY_PARTICIPANT_ACTIVE} />,
    );

    const deleteBtn = screen.getByRole("button", { name: /delete extra rope/i });
    await act(async () => {
      fireEvent.click(deleteBtn);
    });

    await waitFor(() => {
      expect(mockDeleteGearItem).toHaveBeenCalledWith(EXPEDITION_ID, "item-delete");
    });
  });

  // 9. Non-participant / non-owner sees no toggle/delete controls
  it("does not show toggle or delete buttons for a non-participant user", () => {
    const item = makeGearItem({
      id: "item-1",
      name: "Map",
      addedBy: "auth-other-user",
    });
    setupSwr({ gearData: makeGearListResponse([item]) });
    render(
      <PackingTab expeditionId={EXPEDITION_ID} myParticipant={null} />,
    );

    expect(screen.getByText("Map")).toBeTruthy();
    // No toggle/delete buttons for non-participant
    expect(screen.queryByRole("button", { name: /pack map/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /delete map/i })).toBeNull();
  });

  // 10. Active participant sees "Add Gear Item" button
  it("shows the add gear item button for an active participant", () => {
    setupSwr({ gearData: makeGearListResponse([]) });
    render(
      <PackingTab expeditionId={EXPEDITION_ID} myParticipant={MY_PARTICIPANT_ACTIVE} />,
    );
    expect(screen.getByTestId("add-gear-toggle")).toBeTruthy();
  });

  // 11. Non-participant does not see "Add Gear Item" button
  it("does not show the add gear item button for a non-participant", () => {
    setupSwr({ gearData: makeGearListResponse([]) });
    render(
      <PackingTab expeditionId={EXPEDITION_ID} myParticipant={null} />,
    );
    expect(screen.getByText("No gear added yet.")).toBeTruthy();
    expect(screen.queryByTestId("add-gear-toggle")).toBeNull();
  });

  // 12. Add item form — submit calls addGearItem and revalidates
  it("submits the add gear form and calls addGearItem", async () => {
    const newItem = makeGearItem({ id: "new-item", name: "Headlamp", weightGrams: 150 });
    mockAddGearItem.mockResolvedValue(newItem);
    setupSwr({ gearData: makeGearListResponse([]) });

    render(
      <PackingTab expeditionId={EXPEDITION_ID} myParticipant={MY_PARTICIPANT_ACTIVE} />,
    );

    // Open the form
    fireEvent.click(screen.getByTestId("add-gear-toggle"));
    expect(screen.getByTestId("add-gear-form")).toBeTruthy();

    // Fill in name and weight
    fireEvent.change(screen.getByTestId("add-gear-name"), {
      target: { value: "Headlamp" },
    });
    fireEvent.change(screen.getByTestId("add-gear-weight"), {
      target: { value: "150" },
    });

    // Submit
    await act(async () => {
      fireEvent.click(screen.getByTestId("add-gear-submit"));
    });

    await waitFor(() => {
      expect(mockAddGearItem).toHaveBeenCalledWith(
        EXPEDITION_ID,
        expect.objectContaining({ name: "Headlamp", weightGrams: 150 }),
      );
    });
  });

  // 13. API failure state
  it("shows an error state when the gear API fails", () => {
    setupSwr({ gearError: new Error("Network error") });
    render(
      <PackingTab expeditionId={EXPEDITION_ID} myParticipant={null} />,
    );
    expect(screen.getByTestId("packing-error")).toBeTruthy();
    expect(screen.getByText("Failed to load packing list.")).toBeTruthy();
  });

  // 14. Organiser can delete any item (including items added by other users)
  it("shows delete button for organiser on items they did not add", async () => {
    const item = makeGearItem({
      id: "item-other",
      name: "Compass",
      addedBy: "auth-other-user",
    });
    mockDeleteGearItem.mockResolvedValue(undefined);
    setupSwr({ gearData: makeGearListResponse([item]) });

    render(
      <PackingTab expeditionId={EXPEDITION_ID} myParticipant={MY_PARTICIPANT_ORGANIZER} />,
    );

    // Organiser should see the delete button even for other's items
    const deleteBtn = screen.getByRole("button", { name: /delete compass/i });
    expect(deleteBtn).toBeTruthy();

    await act(async () => {
      fireEvent.click(deleteBtn);
    });

    await waitFor(() => {
      expect(mockDeleteGearItem).toHaveBeenCalledWith(EXPEDITION_ID, "item-other");
    });
  });
});
