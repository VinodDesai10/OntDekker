/**
 * Checkpoint 5.3 — OTP Verification UI tests
 *
 * Covers the awaiting-otp flow introduced in this checkpoint:
 *   URL: /verify-email?email=user@example.com
 *
 * The existing token-flow tests (loading / success / error / no-token) are
 * preserved below as-is from VerifyEmailPage.test.tsx to keep full coverage
 * in one file.
 *
 * ==========================================================================
 * NEW coverage (OTP flow):
 *   7.  Renders OTP input boxes when email param is present
 *   8.  Successful OTP verification — success message shown
 *   9.  Successful OTP verification — redirect to /login?verified=1
 *  10.  Invalid OTP error
 *  11.  Expired OTP error
 *  12.  Too many attempts error
 *  13.  Generic (non-ApiError) failure
 *  14.  Verify button disabled while fewer than 6 digits entered
 *  15.  Verify button disabled while request is pending
 *  16.  Error cleared when user starts typing again
 *  17.  Paste behavior — fills all boxes and focuses last
 *  18.  Auto-focus — next box receives focus after typing a digit
 *  19.  Resend button is present but disabled
 *
 * NEW coverage (OtpInput component — isolated):
 *  20.  Renders 6 input boxes
 *  21.  Each box has an accessible aria-label
 *  22.  Auto-focus advances to the next input after a digit is typed
 *  23.  Backspace on an empty box moves to the previous box
 *  24.  Backspace on a filled box clears it without moving focus
 *  25.  Paste fills boxes starting at the focused index
 *  26.  Non-digit characters are ignored
 *  27.  All boxes are disabled when disabled=true
 *  28.  aria-invalid is set when hasError=true
 *
 * Mocks:
 *  - useAuth from @/contexts/AuthContext
 *  - useRouter / useSearchParams from next/navigation
 *  - verifyEmail from @/services/auth (for the legacy token flow)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  waitFor,
  act,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import VerifyEmailPage from "@/app/verify-email/page";
import { OtpInput } from "@/components/auth/OtpInput";
import { ApiError } from "@/services/api";

// ---------------------------------------------------------------------------
// Mock next/navigation
// ---------------------------------------------------------------------------

const mockReplace = vi.fn();
const mockSearchParamsGet = vi.fn<(arg: string) => string | null>();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  useSearchParams: () => ({ get: mockSearchParamsGet }),
}));

// ---------------------------------------------------------------------------
// Mock AuthContext
// ---------------------------------------------------------------------------

const mockVerifyEmailOtp = vi.fn();
const mockResendOtp = vi.fn();
const mockUseAuth = vi.fn();

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

// ---------------------------------------------------------------------------
// Mock verifyEmail (legacy token flow — service boundary)
// ---------------------------------------------------------------------------

const mockVerifyEmail = vi.fn<(arg: string) => Promise<{ message: string }>>();

vi.mock("@/services/auth", () => ({
  verifyEmail: (...args: unknown[]) => mockVerifyEmail(...(args as [string])),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Default auth state: exposes verifyEmailOtp and resendOtp, no user. */
function defaultAuthState() {
  return { verifyEmailOtp: mockVerifyEmailOtp, resendOtp: mockResendOtp };
}

/** Configure params: email param present, no token. */
function setEmailParam(email = "user@example.com") {
  mockSearchParamsGet.mockImplementation((key: string) => {
    if (key === "email") return email;
    return null;
  });
}

/** Configure params: token present, no email. */
function setTokenParam(token = "valid-token") {
  mockSearchParamsGet.mockImplementation((key: string) => {
    if (key === "token") return token;
    return null;
  });
}

/** Type a full 6-digit OTP into the rendered boxes. */
async function typeOtp(user: ReturnType<typeof userEvent.setup>, otp: string) {
  const inputs = screen.getAllByRole("textbox");
  for (let i = 0; i < otp.length; i++) {
    await user.click(inputs[i]);
    await user.keyboard(otp[i]);
  }
}

// ---------------------------------------------------------------------------
// Global setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers({ shouldAdvanceTime: true });
  mockUseAuth.mockReturnValue(defaultAuthState());
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
});

// ===========================================================================
// SECTION A — Legacy token flow (preserved from VerifyEmailPage.test.tsx)
// ===========================================================================

describe("VerifyEmailPage — no token", () => {
  beforeEach(() => {
    mockSearchParamsGet.mockReturnValue(null);
  });

  it("renders the no-token guidance message when token is absent", async () => {
    render(<VerifyEmailPage />);
    await screen.findByText(/please use the link from your verification email/i);
    expect(
      screen.getByText(/please use the link from your verification email/i)
    ).toBeInTheDocument();
  });

  it("shows a Back-to-register link when both token and email are absent", async () => {
    render(<VerifyEmailPage />);
    const link = await screen.findByRole("link", { name: /back to register/i });
    expect(link).toHaveAttribute("href", "/register");
  });

  it("does NOT call verifyEmail when token is absent", async () => {
    render(<VerifyEmailPage />);
    await screen.findByText(/please use the link from your verification email/i);
    expect(mockVerifyEmail).not.toHaveBeenCalled();
  });
});

describe("VerifyEmailPage — loading (token flow)", () => {
  it("shows the sr-only loading text while verification is pending", async () => {
    let resolveFn!: (v: { message: string }) => void;
    mockVerifyEmail.mockImplementation(
      () => new Promise<{ message: string }>((res) => { resolveFn = res; })
    );
    setTokenParam("valid-token-123");

    render(<VerifyEmailPage />);
    await screen.findByText(/verifying email/i);

    await act(async () => { resolveFn({ message: "ok" }); });
  });

  it("calls verifyEmail with the token from the URL", async () => {
    mockVerifyEmail.mockResolvedValue({ message: "ok" });
    setTokenParam("my-test-token");

    render(<VerifyEmailPage />);
    await waitFor(() => {
      expect(mockVerifyEmail).toHaveBeenCalledWith("my-test-token");
    });
  });
});

describe("VerifyEmailPage — success (token flow)", () => {
  it("shows confirmed message after verifyEmail resolves", async () => {
    mockVerifyEmail.mockResolvedValue({ message: "ok" });
    setTokenParam("success-token");

    render(<VerifyEmailPage />);
    await screen.findByText(/your email has been confirmed/i);
  });

  it("shows Sign-in link after verification succeeds", async () => {
    mockVerifyEmail.mockResolvedValue({ message: "ok" });
    setTokenParam("success-token");

    render(<VerifyEmailPage />);
    const link = await screen.findByRole("link", { name: /sign in to ontdekker/i });
    expect(link).toHaveAttribute("href", "/login");
  });
});

describe("VerifyEmailPage — error (token flow)", () => {
  it("shows ApiError message when verification fails", async () => {
    mockVerifyEmail.mockRejectedValue(
      new ApiError(401, {
        success: false,
        message: "Verification token is invalid or has expired",
        code: "TOKEN_INVALID",
      })
    );
    setTokenParam("expired-token");

    render(<VerifyEmailPage />);
    await screen.findByText(/verification token is invalid or has expired/i);
  });

  it("shows a generic message for non-ApiError rejections", async () => {
    mockVerifyEmail.mockRejectedValue(new Error("Network error"));
    setTokenParam("bad-token");

    render(<VerifyEmailPage />);
    await screen.findByText(/verification failed. please try again/i);
  });

  it("calls verifyEmail exactly once even under double-mount", async () => {
    mockVerifyEmail.mockResolvedValue({ message: "ok" });
    setTokenParam("once-token");

    render(<VerifyEmailPage />);
    await waitFor(() => {
      expect(mockVerifyEmail).toHaveBeenCalledTimes(1);
    });
  });
});

// ===========================================================================
// SECTION B — OTP flow (Checkpoint 5.3)
// ===========================================================================

describe("VerifyEmailPage — awaiting-otp: rendering", () => {
  beforeEach(() => setEmailParam());

  it("renders 6 OTP input boxes", async () => {
    render(<VerifyEmailPage />);
    await screen.findByRole("textbox", { name: /digit 1/i });
    const inputs = screen.getAllByRole("textbox");
    expect(inputs).toHaveLength(6);
  });

  it("shows the email address from the query param", async () => {
    render(<VerifyEmailPage />);
    await screen.findByText("user@example.com");
    expect(screen.getByText("user@example.com")).toBeInTheDocument();
  });

  it("shows the 'We sent a verification code to' text", async () => {
    render(<VerifyEmailPage />);
    await screen.findByText(/we sent a verification code to/i);
  });

  it("renders the Verify button", async () => {
    render(<VerifyEmailPage />);
    const btn = await screen.findByRole("button", { name: /^verify$/i });
    expect(btn).toBeInTheDocument();
  });

  it("renders the resend button in enabled state", async () => {
    render(<VerifyEmailPage />);
    await screen.findByText(/resend code/i);
    const resendBtn = screen.getByRole("button", { name: /^resend code$/i });
    expect(resendBtn).not.toBeDisabled();
  });

  it("does NOT call verifyEmail (token flow) when only email param is present", async () => {
    render(<VerifyEmailPage />);
    await screen.findByRole("textbox", { name: /digit 1/i });
    expect(mockVerifyEmail).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// 8–9: Successful OTP verification
// ---------------------------------------------------------------------------

describe("VerifyEmailPage — awaiting-otp: successful verification", () => {
  beforeEach(() => {
    setEmailParam();
    mockVerifyEmailOtp.mockResolvedValue({ message: "Email verified successfully." });
  });

  it("shows a success message after OTP is submitted and verified", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    await screen.findByRole("textbox", { name: /digit 1/i });
    await typeOtp(user, "123456");

    await user.click(screen.getByRole("button", { name: /^verify$/i }));

    await screen.findByText(/email verified/i);
    expect(screen.getByText(/email verified/i)).toBeInTheDocument();
  });

  it("calls verifyEmailOtp with the email and entered OTP", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    await screen.findByRole("textbox", { name: /digit 1/i });
    await typeOtp(user, "654321");

    await user.click(screen.getByRole("button", { name: /^verify$/i }));

    await waitFor(() => {
      expect(mockVerifyEmailOtp).toHaveBeenCalledWith({
        email: "user@example.com",
        otp: "654321",
      });
    });
  });

  it("redirects to /login?verified=1 after ~1 second", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    await screen.findByRole("textbox", { name: /digit 1/i });
    await typeOtp(user, "123456");
    await user.click(screen.getByRole("button", { name: /^verify$/i }));

    // Success message shown, no redirect yet
    await screen.findByText(/email verified/i);
    expect(mockReplace).not.toHaveBeenCalled();

    // Advance timer by 1 second
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });

    expect(mockReplace).toHaveBeenCalledWith("/login?verified=1");
  });
});

// ---------------------------------------------------------------------------
// 10–13: Error scenarios
// ---------------------------------------------------------------------------

describe("VerifyEmailPage — awaiting-otp: invalid OTP", () => {
  beforeEach(() => setEmailParam());

  it("displays 'Incorrect OTP' error message from backend", async () => {
    mockVerifyEmailOtp.mockRejectedValue(
      new ApiError(401, {
        success: false,
        message: "Incorrect OTP. Please try again.",
        code: "OTP_INVALID",
      })
    );
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    await screen.findByRole("textbox", { name: /digit 1/i });
    await typeOtp(user, "999999");
    await user.click(screen.getByRole("button", { name: /^verify$/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/incorrect otp/i);
  });

  it("does NOT redirect after an invalid OTP error", async () => {
    mockVerifyEmailOtp.mockRejectedValue(
      new ApiError(401, {
        success: false,
        message: "Incorrect OTP. Please try again.",
        code: "OTP_INVALID",
      })
    );
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    await screen.findByRole("textbox", { name: /digit 1/i });
    await typeOtp(user, "999999");
    await user.click(screen.getByRole("button", { name: /^verify$/i }));

    await screen.findByRole("alert");
    await act(async () => { vi.advanceTimersByTime(2000); });
    expect(mockReplace).not.toHaveBeenCalled();
  });
});

describe("VerifyEmailPage — awaiting-otp: expired OTP", () => {
  beforeEach(() => setEmailParam());

  it("displays 'OTP expired' error message from backend", async () => {
    mockVerifyEmailOtp.mockRejectedValue(
      new ApiError(401, {
        success: false,
        message: "OTP has expired. Please request a new code.",
        code: "OTP_EXPIRED",
      })
    );
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    await screen.findByRole("textbox", { name: /digit 1/i });
    await typeOtp(user, "000000");
    await user.click(screen.getByRole("button", { name: /^verify$/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/otp has expired/i);
  });
});

describe("VerifyEmailPage — awaiting-otp: too many attempts", () => {
  beforeEach(() => setEmailParam());

  it("displays 'too many attempts' error message from backend", async () => {
    mockVerifyEmailOtp.mockRejectedValue(
      new ApiError(429, {
        success: false,
        message: "Too many failed attempts. Please request a new code.",
        code: "OTP_MAX_ATTEMPTS",
      })
    );
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    await screen.findByRole("textbox", { name: /digit 1/i });
    await typeOtp(user, "111111");
    await user.click(screen.getByRole("button", { name: /^verify$/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/too many failed attempts/i);
  });
});

describe("VerifyEmailPage — awaiting-otp: generic failure", () => {
  beforeEach(() => setEmailParam());

  it("displays a generic fallback message for non-ApiError errors", async () => {
    mockVerifyEmailOtp.mockRejectedValue(new Error("Network failure"));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    await screen.findByRole("textbox", { name: /digit 1/i });
    await typeOtp(user, "123456");
    await user.click(screen.getByRole("button", { name: /^verify$/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/something went wrong/i);
  });

  it("allows the user to try again after an error", async () => {
    mockVerifyEmailOtp
      .mockRejectedValueOnce(new ApiError(401, {
        success: false,
        message: "Incorrect OTP. Please try again.",
        code: "OTP_INVALID",
      }))
      .mockResolvedValueOnce({ message: "ok" });

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    await screen.findByRole("textbox", { name: /digit 1/i });

    // First attempt — fail
    await typeOtp(user, "111111");
    await user.click(screen.getByRole("button", { name: /^verify$/i }));
    await screen.findByRole("alert");

    // Second attempt — succeed
    await typeOtp(user, "222222");
    await user.click(screen.getByRole("button", { name: /^verify$/i }));
    await screen.findByText(/email verified/i);
  });
});

// ---------------------------------------------------------------------------
// 14–15: Button state
// ---------------------------------------------------------------------------

describe("VerifyEmailPage — awaiting-otp: button state", () => {
  beforeEach(() => setEmailParam());

  it("Verify button is disabled when fewer than 6 digits are entered", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    await screen.findByRole("textbox", { name: /digit 1/i });

    // Type only 3 digits
    await typeOtp(user, "123");

    const btn = screen.getByRole("button", { name: /^verify$/i });
    expect(btn).toBeDisabled();
  });

  it("Verify button is enabled when all 6 digits are entered", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    await screen.findByRole("textbox", { name: /digit 1/i });
    await typeOtp(user, "654321");

    const btn = screen.getByRole("button", { name: /^verify$/i });
    expect(btn).not.toBeDisabled();
  });

  it("Verify button is disabled while request is pending", async () => {
    let resolveFn!: (v: { message: string }) => void;
    mockVerifyEmailOtp.mockImplementation(
      () => new Promise<{ message: string }>((res) => { resolveFn = res; })
    );

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    await screen.findByRole("textbox", { name: /digit 1/i });
    await typeOtp(user, "123456");
    await user.click(screen.getByRole("button", { name: /^verify$/i }));

    // Button should be disabled while pending
    expect(screen.getByRole("button", { name: /verifying/i })).toBeDisabled();

    await act(async () => { resolveFn({ message: "ok" }); });
  });
});

// ---------------------------------------------------------------------------
// 16: Error cleared when user types again
// ---------------------------------------------------------------------------

describe("VerifyEmailPage — awaiting-otp: error cleared on input change", () => {
  beforeEach(() => setEmailParam());

  it("clears the error message when the user edits the OTP after a failure", async () => {
    mockVerifyEmailOtp.mockRejectedValue(
      new ApiError(401, {
        success: false,
        message: "Incorrect OTP. Please try again.",
        code: "OTP_INVALID",
      })
    );

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    await screen.findByRole("textbox", { name: /digit 1/i });
    await typeOtp(user, "111111");
    await user.click(screen.getByRole("button", { name: /^verify$/i }));

    // Error visible
    await screen.findByRole("alert");
    expect(screen.getByRole("alert")).toBeInTheDocument();

    // Paste a new code — error should clear because onChange fires
    const firstInput = screen.getByRole("textbox", { name: /digit 1/i });
    await user.click(firstInput);
    await user.paste("222222");

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

// ===========================================================================
// SECTION C — OtpInput component (isolated unit tests)
// ===========================================================================

describe("OtpInput — rendering", () => {
  it("renders 6 input boxes", () => {
    render(<OtpInput value="" onChange={vi.fn()} />);
    expect(screen.getAllByRole("textbox")).toHaveLength(6);
  });

  it("each box has an accessible aria-label indicating its position", () => {
    render(<OtpInput value="" onChange={vi.fn()} />);
    for (let i = 1; i <= 6; i++) {
      expect(
        screen.getByRole("textbox", { name: `Digit ${i} of 6` })
      ).toBeInTheDocument();
    }
  });

  it("reflects the value prop in the input boxes", () => {
    render(<OtpInput value="123456" onChange={vi.fn()} />);
    const inputs = screen.getAllByRole("textbox");
    expect(inputs[0]).toHaveValue("1");
    expect(inputs[5]).toHaveValue("6");
  });

  it("all boxes are disabled when disabled=true", () => {
    render(<OtpInput value="" onChange={vi.fn()} disabled />);
    screen.getAllByRole("textbox").forEach((input) => {
      expect(input).toBeDisabled();
    });
  });

  it("sets aria-invalid on all boxes when hasError=true", () => {
    render(<OtpInput value="" onChange={vi.fn()} hasError />);
    screen.getAllByRole("textbox").forEach((input) => {
      expect(input).toHaveAttribute("aria-invalid", "true");
    });
  });
});

describe("OtpInput — digit input and auto-focus", () => {
  it("calls onChange with the typed digit at the correct position", async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    render(<OtpInput value="" onChange={handleChange} />);

    const firstInput = screen.getByRole("textbox", { name: /digit 1/i });
    await user.click(firstInput);
    await user.keyboard("5");

    expect(handleChange).toHaveBeenCalledWith(
      expect.stringMatching(/^5/)
    );
  });

  it("ignores non-numeric characters", async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    render(<OtpInput value="" onChange={handleChange} />);

    const firstInput = screen.getByRole("textbox", { name: /digit 1/i });
    await user.click(firstInput);
    await user.keyboard("a");

    // onChange must not have been called with a letter
    const calls = handleChange.mock.calls;
    const wasCalledWithLetter = calls.some(([val]) => /[a-z]/i.test(val));
    expect(wasCalledWithLetter).toBe(false);
  });

  it("auto-focuses the next box after typing a digit", async () => {
    let currentValue = "";
    const handleChange = vi.fn().mockImplementation((v: string) => {
      currentValue = v;
    });
    const user = userEvent.setup();

    const { rerender } = render(
      <OtpInput value={currentValue} onChange={handleChange} />
    );

    const firstInput = screen.getByRole("textbox", { name: /digit 1/i });
    await user.click(firstInput);
    await user.keyboard("3");

    // Re-render with the updated value to simulate controlled component
    rerender(<OtpInput value={currentValue} onChange={handleChange} />);

    await waitFor(() => {
      expect(
        document.activeElement?.getAttribute("aria-label")
      ).toMatch(/digit 2 of 6/i);
    });
  });
});

describe("OtpInput — backspace navigation", () => {
  it("clears the current box's digit when backspace is pressed on a filled box", async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    render(<OtpInput value="1" onChange={handleChange} />);

    const firstInput = screen.getByRole("textbox", { name: /digit 1/i });
    await user.click(firstInput);
    await user.keyboard("{Backspace}");

    // onChange should be called with the first digit cleared
    expect(handleChange).toHaveBeenCalled();
    const lastCall = handleChange.mock.calls.at(-1)?.[0] as string;
    // The value should either be empty or start with an empty string in position 0
    expect(lastCall).not.toContain("1");
  });

  it("moves focus to the previous box when backspace is pressed on an empty box", async () => {
    const user = userEvent.setup();
    // value "1" — first box has "1", second box is empty
    render(<OtpInput value="1" onChange={vi.fn()} />);

    // Focus the second (empty) box and press backspace
    const secondInput = screen.getByRole("textbox", { name: /digit 2/i });
    await user.click(secondInput);
    await user.keyboard("{Backspace}");

    await waitFor(() => {
      expect(document.activeElement?.getAttribute("aria-label")).toMatch(
        /digit 1 of 6/i
      );
    });
  });
});

describe("OtpInput — paste behavior", () => {
  it("fills all 6 boxes when a 6-digit string is pasted", async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    render(<OtpInput value="" onChange={handleChange} />);

    const firstInput = screen.getByRole("textbox", { name: /digit 1/i });
    await user.click(firstInput);
    await user.paste("123456");

    expect(handleChange).toHaveBeenCalledWith("123456");
  });

  it("strips non-digit characters from the pasted string", async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    render(<OtpInput value="" onChange={handleChange} />);

    const firstInput = screen.getByRole("textbox", { name: /digit 1/i });
    await user.click(firstInput);
    await user.paste("1a2b3c4d5e6f");

    // Should extract only the 6 digits
    expect(handleChange).toHaveBeenCalledWith("123456");
  });

  it("focuses the last box after a full paste", async () => {
    let currentValue = "";
    const handleChange = vi.fn().mockImplementation((v: string) => {
      currentValue = v;
    });
    const user = userEvent.setup();

    const { rerender } = render(
      <OtpInput value={currentValue} onChange={handleChange} />
    );

    const firstInput = screen.getByRole("textbox", { name: /digit 1/i });
    await user.click(firstInput);
    await user.paste("123456");

    rerender(<OtpInput value={currentValue} onChange={handleChange} />);

    await waitFor(() => {
      expect(document.activeElement?.getAttribute("aria-label")).toMatch(
        /digit 6 of 6/i
      );
    });
  });
});

// ===========================================================================
// SECTION D — Resend OTP (Checkpoint 5.4)
// ===========================================================================

/**
 * Tests 29–40: Resend OTP functionality
 *
 * 29.  Resend button is enabled on initial render (Checkpoint 5.4)
 * 30.  Successful resend — shows confirmation message
 * 31.  Successful resend — calls resendOtp with the correct email
 * 32.  Loading state — button shows "Sending…" while request is pending
 * 33.  Loading state — button is disabled while request is pending
 * 34.  Cooldown starts after successful resend — button shows countdown
 * 35.  Cooldown — button is disabled during countdown
 * 36.  Cooldown — repeated clicks do nothing (button is disabled)
 * 37.  Cooldown expires — button becomes enabled again
 * 38.  Cooldown expires — countdown label disappears
 * 39.  Backend failure — displays the error message from ApiError
 * 40.  Backend failure (generic) — displays a fallback message
 * 41.  Error cleared on next successful resend attempt
 */

describe("VerifyEmailPage — resend OTP: initial state", () => {
  beforeEach(() => setEmailParam());

  it("resend button is enabled on initial render", async () => {
    render(<VerifyEmailPage />);
    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    expect(btns[0]).not.toBeDisabled();
  });

  it("does not show any resend status message on initial render", async () => {
    render(<VerifyEmailPage />);
    await screen.findByRole("button", { name: /^resend code$/i });
    expect(
      screen.queryByText(/a new verification code has been sent/i)
    ).not.toBeInTheDocument();
  });
});

describe("VerifyEmailPage — resend OTP: successful resend", () => {
  beforeEach(() => {
    setEmailParam();
    mockResendOtp.mockResolvedValue({ message: "OTP sent." });
  });

  it("shows the success confirmation message after resend", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    // Use getAllByRole to handle potential Suspense double-render in test environment
    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    await screen.findAllByText(/a new verification code has been sent/i);
    expect(
      screen.getAllByText(/a new verification code has been sent/i)[0]
    ).toBeInTheDocument();
  });

  it("calls resendOtp with the email from the URL param", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    await waitFor(() => {
      expect(mockResendOtp).toHaveBeenCalledWith({ email: "user@example.com" });
    });
  });

  it("success message has role='status' for accessibility", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    const statusEls = await screen.findAllByRole("status");
    expect(statusEls[0]).toHaveTextContent(/a new verification code has been sent/i);
  });
});

describe("VerifyEmailPage — resend OTP: loading state", () => {
  beforeEach(() => setEmailParam());

  it("shows 'Sending…' text while the request is in-flight", async () => {
    let resolveFn!: (v: { message: string }) => void;
    mockResendOtp.mockImplementation(
      () => new Promise<{ message: string }>((res) => { resolveFn = res; })
    );

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    // While pending the button label should be "Sending…"
    const sendingBtns = await screen.findAllByRole("button", { name: /sending/i });
    expect(sendingBtns[0]).toBeInTheDocument();

    // Resolve to prevent dangling state
    await act(async () => { resolveFn({ message: "ok" }); });
  });

  it("button is disabled while the request is in-flight", async () => {
    let resolveFn!: (v: { message: string }) => void;
    mockResendOtp.mockImplementation(
      () => new Promise<{ message: string }>((res) => { resolveFn = res; })
    );

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    const pendingBtns = await screen.findAllByRole("button", { name: /sending/i });
    expect(pendingBtns[0]).toBeDisabled();

    await act(async () => { resolveFn({ message: "ok" }); });
  });
});

describe("VerifyEmailPage — resend OTP: cooldown timer", () => {
  beforeEach(() => {
    setEmailParam();
    mockResendOtp.mockResolvedValue({ message: "OTP sent." });
  });

  it("shows the countdown label immediately after a successful resend", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    // After success the button should show the initial countdown
    await screen.findAllByRole("button", { name: /resend code \(30s\)/i });
    expect(
      screen.getAllByRole("button", { name: /resend code \(30s\)/i })[0]
    ).toBeInTheDocument();
  });

  it("button is disabled during the cooldown period", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    await screen.findAllByRole("button", { name: /resend code \(30s\)/i });
    expect(
      screen.getAllByRole("button", { name: /resend code \(30s\)/i })[0]
    ).toBeDisabled();
  });

  it("countdown decrements each second", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    // Wait for cooldown to start
    await screen.findAllByRole("button", { name: /resend code \(30s\)/i });

    // Advance by 5 seconds
    await act(async () => {
      vi.advanceTimersByTime(5000);
    });

    expect(
      screen.getAllByRole("button", { name: /resend code \(25s\)/i })[0]
    ).toBeInTheDocument();
  });

  it("does not call resendOtp again when button is clicked during cooldown", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    // Wait for cooldown to start
    await screen.findAllByRole("button", { name: /resend code \(30s\)/i });

    // resendOtp should have been called exactly once so far
    expect(mockResendOtp).toHaveBeenCalledTimes(1);

    // Trying to click the disabled button should not trigger another call
    const cooldownBtns = screen.getAllByRole("button", { name: /resend code \(30s\)/i });
    // Disabled buttons don't fire click events via userEvent
    await user.click(cooldownBtns[0]);

    expect(mockResendOtp).toHaveBeenCalledTimes(1);
  });
});

describe("VerifyEmailPage — resend OTP: cooldown expiry", () => {
  beforeEach(() => {
    setEmailParam();
    mockResendOtp.mockResolvedValue({ message: "OTP sent." });
  });

  it("button becomes enabled again after the 30-second cooldown expires", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    // Wait for cooldown to start
    await screen.findAllByRole("button", { name: /resend code \(30s\)/i });

    // Fast-forward past the full cooldown
    await act(async () => {
      vi.advanceTimersByTime(30_000);
    });

    const readyBtns = await screen.findAllByRole("button", { name: /^resend code$/i });
    expect(readyBtns[0]).not.toBeDisabled();
  });

  it("countdown label disappears once the cooldown expires", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    await screen.findAllByRole("button", { name: /resend code \(30s\)/i });

    await act(async () => {
      vi.advanceTimersByTime(30_000);
    });

    // Should no longer show the countdown, just plain "Resend code"
    expect(
      screen.queryByRole("button", { name: /resend code \(\d+s\)/i })
    ).not.toBeInTheDocument();
    expect(
      screen.getAllByRole("button", { name: /^resend code$/i })[0]
    ).toBeInTheDocument();
  });

  it("allows another resend after cooldown expires", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    // First click
    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    await screen.findAllByRole("button", { name: /resend code \(30s\)/i });

    // Expire the cooldown
    await act(async () => {
      vi.advanceTimersByTime(30_000);
    });

    // Second click after cooldown
    const readyBtns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(readyBtns[0]);

    await waitFor(() => {
      expect(mockResendOtp).toHaveBeenCalledTimes(2);
    });
  });
});

describe("VerifyEmailPage — resend OTP: backend failures", () => {
  beforeEach(() => setEmailParam());

  it("displays the ApiError message when resend fails", async () => {
    mockResendOtp.mockRejectedValue(
      new ApiError(429, {
        success: false,
        message: "Too many requests. Please wait before requesting a new code.",
        code: "RATE_LIMITED",
      })
    );

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    const alerts = await screen.findAllByRole("alert");
    expect(alerts[0]).toHaveTextContent(/too many requests/i);
  });

  it("displays rate-limited error from backend", async () => {
    mockResendOtp.mockRejectedValue(
      new ApiError(429, {
        success: false,
        message: "Rate limited. Try again later.",
        code: "RATE_LIMITED",
      })
    );

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    const alerts = await screen.findAllByRole("alert");
    expect(alerts[0]).toHaveTextContent(/rate limited/i);
  });

  it("displays user-not-found error from backend", async () => {
    mockResendOtp.mockRejectedValue(
      new ApiError(404, {
        success: false,
        message: "User not found.",
        code: "USER_NOT_FOUND",
      })
    );

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    const alerts = await screen.findAllByRole("alert");
    expect(alerts[0]).toHaveTextContent(/user not found/i);
  });

  it("displays a generic fallback message for non-ApiError failures", async () => {
    mockResendOtp.mockRejectedValue(new Error("Network timeout"));

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    const alerts = await screen.findAllByRole("alert");
    expect(alerts[0]).toHaveTextContent(/something went wrong/i);
  });

  it("does NOT start the cooldown when the resend fails", async () => {
    mockResendOtp.mockRejectedValue(
      new ApiError(429, {
        success: false,
        message: "Too many requests.",
        code: "RATE_LIMITED",
      })
    );

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    // Error should appear
    await screen.findAllByRole("alert");

    // Button should NOT show a countdown — it should be the plain "Resend code"
    expect(
      screen.queryByRole("button", { name: /resend code \(\d+s\)/i })
    ).not.toBeInTheDocument();
  });

  it("button re-enables after a failed resend so the user can retry", async () => {
    mockResendOtp.mockRejectedValue(
      new ApiError(500, {
        success: false,
        message: "Internal server error.",
        code: "SERVER_ERROR",
      })
    );

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);

    // After the failed request, the button should be enabled again (no cooldown)
    const retryBtns = await screen.findAllByRole("button", { name: /^resend code$/i });
    expect(retryBtns[0]).not.toBeDisabled();
  });

  it("clears the previous error message on the next successful resend", async () => {
    mockResendOtp
      .mockRejectedValueOnce(
        new ApiError(500, {
          success: false,
          message: "Internal server error.",
          code: "SERVER_ERROR",
        })
      )
      .mockResolvedValueOnce({ message: "OTP sent." });

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<VerifyEmailPage />);

    // First click — fail
    const btns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(btns[0]);
    await screen.findAllByRole("alert");

    // Second click — succeed
    const retryBtns = await screen.findAllByRole("button", { name: /^resend code$/i });
    await user.click(retryBtns[0]);

    // Error should be gone; success message should be shown
    await screen.findAllByText(/a new verification code has been sent/i);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
