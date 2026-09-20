/**
 * Tests for TripDiscussion component (CP-TRIP-3B)
 *
 * Tests:
 *  1.  Discussion tab renders (component mounts and shows discussion container)
 *  2.  Messages render with content
 *  3.  Real author names are resolved using batchProfilesByAuth()
 *  4.  Unknown-user fallback when profile resolution fails
 *  5.  Empty discussion state when no messages
 *  6.  Composer is visible for organizer
 *  7.  Composer is visible for active participant
 *  8.  Composer is hidden for non-member (replaced by notice)
 *  9.  Empty/whitespace message cannot be submitted
 * 10.  Successful message submission clears the composer and appends message
 * 11.  403 on posting shows a friendly membership error
 * 12.  Loading skeleton is shown while messages are fetching
 * 13.  Error state shown when discussion fails to load
 * 14.  404 trip not found shows appropriate error state
 *
 * All API calls are mocked at the service boundary.
 * MSW server is active (onUnhandledRequest: "error"); no MSW handlers needed.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// Mocks — must be declared before any module-under-test imports
// ---------------------------------------------------------------------------

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  useParams: () => ({}),
}));

// Trips API mocks
const mockGetTripDiscussion = vi.fn();
const mockPostDiscussionMessage = vi.fn();

vi.mock("@/services/tripsApi", () => ({
  getTripDiscussion: (...args: unknown[]) => mockGetTripDiscussion(...args),
  postDiscussionMessage: (...args: unknown[]) => mockPostDiscussionMessage(...args),
  joinTrip: vi.fn(),
  deleteTrip: vi.fn(),
  getMyParticipantStatus: vi.fn(),
}));

// User service mock
const mockBatchProfilesByAuth = vi.fn();

vi.mock("@/services/users", () => ({
  batchProfilesByAuth: (...args: unknown[]) => mockBatchProfilesByAuth(...args),
}));

// ---------------------------------------------------------------------------
// Import under test AFTER mocks
// ---------------------------------------------------------------------------

import TripDiscussion from "@/components/trips/TripDiscussion";
import { ApiError } from "@/services/api";
import type { DiscussionMessage, TripParticipant } from "@/types/trip";
import type { ProfileMap } from "@/services/users";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const TRIP_ID = "trip-abc-123";

function makeMessage(overrides: Partial<DiscussionMessage> = {}): DiscussionMessage {
  return {
    id: "msg-1",
    expeditionId: TRIP_ID,
    authorId: "auth-user-1",
    content: "Looking forward to the hike!",
    createdAt: "2026-05-10T08:30:00Z",
    updatedAt: "2026-05-10T08:30:00Z",
    ...overrides,
  };
}

function makeParticipant(
  role: TripParticipant["role"] = "PARTICIPANT",
  status: TripParticipant["status"] = "ACTIVE"
): TripParticipant {
  return {
    id: "participant-1",
    expedition_id: TRIP_ID,
    user_id: "auth-user-1",
    role,
    status,
    joined_at: "2026-05-01T00:00:00Z",
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
  };
}

function makeDiscussionResponse(messages: DiscussionMessage[]) {
  return {
    items: messages,
    pagination: {
      page: 1,
      pageSize: 50,
      totalItems: messages.length,
      totalPages: 1,
      hasNext: false,
      hasPrevious: false,
    },
  };
}

const PROFILE_ALICE: ProfileMap[string] = {
  id: "auth-user-1",
  username: "alice_treks",
  displayName: "Alice Trekker",
  avatarUrl: "https://example.com/alice.jpg",
};

const PROFILE_BOB: ProfileMap[string] = {
  id: "auth-user-2",
  username: "bob_climbs",
  displayName: "Bob Climber",
  avatarUrl: null,
};

// ---------------------------------------------------------------------------
// Render helper
// ---------------------------------------------------------------------------

function renderDiscussion(
  tripId = TRIP_ID,
  myParticipant: TripParticipant | null = null,
  isLoadingMyParticipant = false
) {
  return render(
    <TripDiscussion
      tripId={tripId}
      myParticipant={myParticipant}
      isLoadingMyParticipant={isLoadingMyParticipant}
    />
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("TripDiscussion", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: batchProfilesByAuth returns empty map unless overridden
    mockBatchProfilesByAuth.mockResolvedValue({});
  });

  // 1. Discussion tab renders
  it("renders the discussion container after messages load", async () => {
    mockGetTripDiscussion.mockResolvedValue(
      makeDiscussionResponse([makeMessage()])
    );

    renderDiscussion(TRIP_ID, makeParticipant());

    await waitFor(() => {
      expect(screen.getByTestId("trip-discussion")).toBeTruthy();
    });
  });

  // 2. Messages render with content
  it("renders message content in the list", async () => {
    const msg = makeMessage({ content: "Gear check tonight at 7pm!" });
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([msg]));

    renderDiscussion(TRIP_ID, makeParticipant());

    await waitFor(() => {
      expect(screen.getByText("Gear check tonight at 7pm!")).toBeTruthy();
    });
  });

  it("renders multiple messages in order", async () => {
    const msg1 = makeMessage({ id: "m1", content: "First message" });
    const msg2 = makeMessage({
      id: "m2",
      authorId: "auth-user-2",
      content: "Second message",
    });
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([msg1, msg2]));
    mockBatchProfilesByAuth.mockResolvedValue({
      "auth-user-1": PROFILE_ALICE,
      "auth-user-2": PROFILE_BOB,
    });

    renderDiscussion(TRIP_ID, makeParticipant());

    await waitFor(() => {
      expect(screen.getByText("First message")).toBeTruthy();
      expect(screen.getByText("Second message")).toBeTruthy();
    });

    // Verify DOM order: first message appears before second
    const messageEls = screen.getAllByTestId("discussion-message");
    expect(messageEls.length).toBe(2);
    expect(messageEls[0]).toHaveTextContent("First message");
    expect(messageEls[1]).toHaveTextContent("Second message");
  });

  // 3. Real author names resolved via batchProfilesByAuth
  it("displays the resolved displayName for a message author", async () => {
    const msg = makeMessage({ authorId: "auth-user-1" });
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([msg]));
    mockBatchProfilesByAuth.mockResolvedValue({ "auth-user-1": PROFILE_ALICE });

    renderDiscussion(TRIP_ID, makeParticipant());

    await waitFor(() => {
      expect(screen.getByText("Alice Trekker")).toBeTruthy();
    });
  });

  it("displays username when displayName is empty", async () => {
    const profileNoDisplay = { ...PROFILE_BOB, displayName: "" };
    const msg = makeMessage({ authorId: "auth-user-2" });
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([msg]));
    mockBatchProfilesByAuth.mockResolvedValue({ "auth-user-2": profileNoDisplay });

    renderDiscussion(TRIP_ID, makeParticipant());

    await waitFor(() => {
      expect(screen.getByText("bob_climbs")).toBeTruthy();
    });
  });

  it("calls batchProfilesByAuth once with deduplicated author IDs", async () => {
    // Two messages from the same author
    const m1 = makeMessage({ id: "m1", authorId: "auth-user-1" });
    const m2 = makeMessage({ id: "m2", authorId: "auth-user-1" });
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([m1, m2]));
    mockBatchProfilesByAuth.mockResolvedValue({ "auth-user-1": PROFILE_ALICE });

    renderDiscussion(TRIP_ID, makeParticipant());

    await waitFor(() => {
      const names = screen.getAllByText("Alice Trekker");
      expect(names.length).toBe(2);
    });

    // Must have been called exactly once; IDs must be deduplicated
    expect(mockBatchProfilesByAuth).toHaveBeenCalledTimes(1);
    const calledIds = mockBatchProfilesByAuth.mock.calls[0][0] as string[];
    expect(calledIds.filter((id) => id === "auth-user-1").length).toBe(1);
  });

  it("renders avatar img with the resolved avatarUrl", async () => {
    const msg = makeMessage({ authorId: "auth-user-1" });
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([msg]));
    mockBatchProfilesByAuth.mockResolvedValue({ "auth-user-1": PROFILE_ALICE });

    renderDiscussion(TRIP_ID, makeParticipant());

    await waitFor(() => {
      const img = screen.getByAltText("Alice Trekker") as HTMLImageElement;
      expect(img.src).toContain("example.com/alice.jpg");
    });
  });

  // 4. Unknown-user fallback
  it("shows 'Unknown user' when the author profile is not in the map", async () => {
    const msg = makeMessage({ authorId: "auth-unresolvable" });
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([msg]));
    mockBatchProfilesByAuth.mockResolvedValue({} as ProfileMap);

    renderDiscussion(TRIP_ID, makeParticipant());

    await waitFor(() => {
      expect(screen.getByText("Unknown user")).toBeTruthy();
    });
  });

  it("shows 'Unknown user' when batchProfilesByAuth rejects", async () => {
    const msg = makeMessage({ authorId: "auth-error-user" });
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([msg]));
    mockBatchProfilesByAuth.mockRejectedValue(new Error("user-service down"));

    renderDiscussion(TRIP_ID, makeParticipant());

    await waitFor(() => {
      expect(screen.getByText("Unknown user")).toBeTruthy();
    });
  });

  it("never shows raw UUID fragments as author names", async () => {
    const uuidAuthorId = "3f4a1c2e-beef-dead-cafe-000000000000";
    const msg = makeMessage({ authorId: uuidAuthorId });
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([msg]));
    mockBatchProfilesByAuth.mockResolvedValue({});

    renderDiscussion(TRIP_ID, makeParticipant());

    await waitFor(() => {
      expect(screen.getByText("Unknown user")).toBeTruthy();
    });
    // No UUID fragment should appear as author text
    expect(screen.queryByText(/3f4a1c2e/)).toBeNull();
  });

  // 5. Empty discussion state
  it("shows empty state when no messages exist", async () => {
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([]));

    renderDiscussion(TRIP_ID, makeParticipant());

    await waitFor(() => {
      expect(screen.getByTestId("discussion-empty")).toBeTruthy();
    });
    expect(screen.getByText("No messages yet.")).toBeTruthy();
  });

  // 6. Composer visible for organizer
  it("shows the composer for an organizer", async () => {
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([]));
    const organizer = makeParticipant("ORGANIZER", "ACTIVE");

    renderDiscussion(TRIP_ID, organizer);

    await waitFor(() => {
      expect(screen.getByTestId("discussion-composer")).toBeTruthy();
    });
  });

  // 7. Composer visible for active participant
  it("shows the composer for an active participant", async () => {
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([]));
    const participant = makeParticipant("PARTICIPANT", "ACTIVE");

    renderDiscussion(TRIP_ID, participant);

    await waitFor(() => {
      expect(screen.getByTestId("discussion-composer")).toBeTruthy();
    });
  });

  // 8. Composer hidden for non-member
  it("hides the composer and shows non-member notice for null participant", async () => {
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([]));

    renderDiscussion(TRIP_ID, null, false);

    await waitFor(() => {
      expect(screen.queryByTestId("discussion-composer")).toBeNull();
      expect(screen.getByTestId("non-member-notice")).toBeTruthy();
    });
    expect(
      screen.getByText("Join this trip to participate in the discussion.")
    ).toBeTruthy();
  });

  it("hides the composer for a participant with LEFT status", async () => {
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([]));
    const leftMember = makeParticipant("PARTICIPANT", "LEFT");

    renderDiscussion(TRIP_ID, leftMember, false);

    await waitFor(() => {
      expect(screen.queryByTestId("discussion-composer")).toBeNull();
      expect(screen.getByTestId("non-member-notice")).toBeTruthy();
    });
  });

  // 9. Empty/whitespace message cannot be submitted
  it("disables the submit button when the textarea is empty", async () => {
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([]));

    renderDiscussion(TRIP_ID, makeParticipant("ORGANIZER", "ACTIVE"));

    await waitFor(() => {
      expect(screen.getByTestId("discussion-composer")).toBeTruthy();
    });

    const submitBtn = screen.getByTestId("discussion-submit") as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
  });

  it("disables the submit button for whitespace-only content", async () => {
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([]));

    renderDiscussion(TRIP_ID, makeParticipant("ORGANIZER", "ACTIVE"));

    await waitFor(() => {
      expect(screen.getByTestId("discussion-input")).toBeTruthy();
    });

    const textarea = screen.getByTestId("discussion-input");
    fireEvent.change(textarea, { target: { value: "   \n  " } });

    const submitBtn = screen.getByTestId("discussion-submit") as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
  });

  it("does not call postDiscussionMessage when form is submitted with empty input", async () => {
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([]));

    renderDiscussion(TRIP_ID, makeParticipant("ORGANIZER", "ACTIVE"));

    await waitFor(() => {
      expect(screen.getByTestId("discussion-composer")).toBeTruthy();
    });

    // Try submitting the form directly
    const form = screen.getByTestId("discussion-input").closest("form")!;
    fireEvent.submit(form);

    expect(mockPostDiscussionMessage).not.toHaveBeenCalled();
  });

  // 10. Successful message submission
  it("calls postDiscussionMessage with trimmed content on submit", async () => {
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([]));
    const newMsg = makeMessage({
      id: "new-msg",
      content: "See you all at base camp!",
    });
    mockPostDiscussionMessage.mockResolvedValue(newMsg);

    renderDiscussion(TRIP_ID, makeParticipant("ORGANIZER", "ACTIVE"));

    await waitFor(() => {
      expect(screen.getByTestId("discussion-input")).toBeTruthy();
    });

    const textarea = screen.getByTestId("discussion-input");
    fireEvent.change(textarea, { target: { value: "  See you all at base camp!  " } });
    fireEvent.submit(textarea.closest("form")!);

    await waitFor(() => {
      expect(mockPostDiscussionMessage).toHaveBeenCalledWith(
        TRIP_ID,
        "See you all at base camp!"
      );
    });
  });

  it("appends the new message to the list after successful submission", async () => {
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([]));
    const newMsg = makeMessage({
      id: "new-msg",
      content: "This is going to be epic!",
    });
    mockPostDiscussionMessage.mockResolvedValue(newMsg);
    // batchProfilesByAuth also called for the new message author
    mockBatchProfilesByAuth.mockResolvedValue({ "auth-user-1": PROFILE_ALICE });

    renderDiscussion(TRIP_ID, makeParticipant("ORGANIZER", "ACTIVE"));

    await waitFor(() => {
      expect(screen.getByTestId("discussion-input")).toBeTruthy();
    });

    const textarea = screen.getByTestId("discussion-input");
    fireEvent.change(textarea, { target: { value: "This is going to be epic!" } });
    fireEvent.submit(textarea.closest("form")!);

    await waitFor(() => {
      expect(screen.getByText("This is going to be epic!")).toBeTruthy();
    });
  });

  it("clears the composer textarea after successful submission", async () => {
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([]));
    const newMsg = makeMessage({ id: "new-msg", content: "Hello team!" });
    mockPostDiscussionMessage.mockResolvedValue(newMsg);
    mockBatchProfilesByAuth.mockResolvedValue({});

    renderDiscussion(TRIP_ID, makeParticipant("ORGANIZER", "ACTIVE"));

    await waitFor(() => {
      expect(screen.getByTestId("discussion-input")).toBeTruthy();
    });

    const textarea = screen.getByTestId("discussion-input") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "Hello team!" } });
    fireEvent.submit(textarea.closest("form")!);

    await waitFor(() => {
      expect(textarea.value).toBe("");
    });
  });

  // 11. 403 handling
  it("shows a friendly error when postDiscussionMessage returns 403", async () => {
    mockGetTripDiscussion.mockResolvedValue(makeDiscussionResponse([]));
    mockPostDiscussionMessage.mockRejectedValue(
      new ApiError(403, {
        success: false,
        message: "Not a member",
        code: "FORBIDDEN",
      })
    );

    renderDiscussion(TRIP_ID, makeParticipant("ORGANIZER", "ACTIVE"));

    await waitFor(() => {
      expect(screen.getByTestId("discussion-input")).toBeTruthy();
    });

    const textarea = screen.getByTestId("discussion-input");
    fireEvent.change(textarea, { target: { value: "Hey everyone!" } });
    fireEvent.submit(textarea.closest("form")!);

    await waitFor(() => {
      expect(screen.getByTestId("composer-error")).toBeTruthy();
      expect(
        screen.getByText(
          "You must be an active member to post in this discussion."
        )
      ).toBeTruthy();
    });
  });

  // 12. Loading skeleton
  it("shows the loading skeleton while messages are being fetched", () => {
    // Never resolves — stays in loading state
    mockGetTripDiscussion.mockImplementation(() => new Promise(() => {}));

    renderDiscussion(TRIP_ID, makeParticipant());

    expect(screen.getByTestId("discussion-skeleton")).toBeTruthy();
  });

  // 13. Error state when discussion fails to load
  it("shows an error state when getTripDiscussion rejects", async () => {
    mockGetTripDiscussion.mockRejectedValue(
      new ApiError(500, {
        success: false,
        message: "Internal server error",
        code: "INTERNAL_ERROR",
      })
    );

    renderDiscussion(TRIP_ID, makeParticipant());

    await waitFor(() => {
      expect(screen.getByTestId("discussion-error")).toBeTruthy();
    });
    expect(
      screen.getByText("Unable to load the discussion. Please try again.")
    ).toBeTruthy();
  });

  // 14. 404 trip not found
  it("shows a 'trip not found' error state on 404", async () => {
    mockGetTripDiscussion.mockRejectedValue(
      new ApiError(404, {
        success: false,
        message: "Trip not found",
        code: "NOT_FOUND",
      })
    );

    renderDiscussion(TRIP_ID, makeParticipant());

    await waitFor(() => {
      expect(screen.getByTestId("discussion-error")).toBeTruthy();
    });
    expect(
      screen.getByText(
        "This trip was not found. It may have been deleted."
      )
    ).toBeTruthy();
  });
});
