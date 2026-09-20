"use client";

/**
 * OntDekker — OtpInput
 *
 * Six individual digit boxes for OTP entry.
 *
 * Behavior:
 *  - Auto-focuses the next box after typing a digit
 *  - Backspace on an empty box moves focus to the previous box
 *  - Pasting a 6-digit string fills all boxes and focuses the last
 *  - Accepts digits only — non-numeric input is silently ignored
 *  - Announces loading state via aria-busy on the fieldset
 *
 * Props:
 *  value      : current 6-char string (caller controls state)
 *  onChange   : called with the updated 6-char string
 *  disabled   : disables all inputs (e.g. while request is pending)
 *  hasError   : marks all inputs aria-invalid when true
 */

import { useRef, KeyboardEvent, ClipboardEvent, ChangeEvent } from "react";
import { cn } from "@/lib/utils";

const OTP_LENGTH = 6;

interface OtpInputProps {
  value: string;
  onChange: (otp: string) => void;
  disabled?: boolean;
  hasError?: boolean;
}

export function OtpInput({
  value,
  onChange,
  disabled = false,
  hasError = false,
}: OtpInputProps) {
  // Build a fixed-length array of characters from the controlled value.
  // We cannot use padEnd with "" as fill because padEnd("", 6, "") === "".
  const digits: string[] = Array.from({ length: OTP_LENGTH }, (_, i) =>
    i < value.length ? value[i] : ""
  );

  const inputRefs = useRef<Array<HTMLInputElement | null>>(
    new Array(OTP_LENGTH).fill(null)
  );

  function focusIndex(index: number) {
    const clamped = Math.max(0, Math.min(OTP_LENGTH - 1, index));
    inputRefs.current[clamped]?.focus();
  }

  function updateDigit(index: number, char: string) {
    const updated = [...digits];
    updated[index] = char;
    onChange(updated.join(""));
  }

  // -------------------------------------------------------------------------
  // Input handler — fires after the native change event
  // -------------------------------------------------------------------------

  function handleChange(e: ChangeEvent<HTMLInputElement>, index: number) {
    const raw = e.target.value;

    // Extract the last character typed (the input is maxLength=1)
    const last = raw.slice(-1);

    if (!/^\d$/.test(last)) {
      // Non-digit typed — restore the current value by resetting input
      e.target.value = digits[index];
      return;
    }

    updateDigit(index, last);

    // Advance focus to next box
    if (index < OTP_LENGTH - 1) {
      focusIndex(index + 1);
    }
  }

  // -------------------------------------------------------------------------
  // Keydown — handle backspace navigation
  // -------------------------------------------------------------------------

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>, index: number) {
    if (e.key === "Backspace") {
      if (digits[index] !== "") {
        // Clear current box
        updateDigit(index, "");
      } else if (index > 0) {
        // Box already empty — move back and clear previous
        updateDigit(index - 1, "");
        focusIndex(index - 1);
      }
      e.preventDefault();
    }

    if (e.key === "ArrowLeft" && index > 0) {
      focusIndex(index - 1);
      e.preventDefault();
    }

    if (e.key === "ArrowRight" && index < OTP_LENGTH - 1) {
      focusIndex(index + 1);
      e.preventDefault();
    }
  }

  // -------------------------------------------------------------------------
  // Paste — fill all boxes from the pasted content
  // -------------------------------------------------------------------------

  function handlePaste(e: ClipboardEvent<HTMLInputElement>, index: number) {
    e.preventDefault();

    const pasted = e.clipboardData
      .getData("text")
      .replace(/\D/g, "") // strip non-digits
      .slice(0, OTP_LENGTH);

    if (!pasted) return;

    const updated = [...digits];
    for (let i = 0; i < pasted.length; i++) {
      if (index + i < OTP_LENGTH) {
        updated[index + i] = pasted[i];
      }
    }
    onChange(updated.join(""));

    // Focus the box after the last pasted digit
    const nextFocus = Math.min(index + pasted.length, OTP_LENGTH - 1);
    focusIndex(nextFocus);
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div
      role="group"
      aria-label="One-time password"
      aria-busy={disabled}
    >
      <span className="sr-only">Enter your 6-digit verification code</span>
      <div className="flex gap-2 justify-center">
        {digits.map((digit, index) => (
          <input
            key={index}
            ref={(el) => {
              inputRefs.current[index] = el;
            }}
            id={`otp-digit-${index + 1}`}
            type="text"
            inputMode="numeric"
            pattern="\d*"
            maxLength={1}
            value={digit}
            autoComplete={index === 0 ? "one-time-code" : "off"}
            aria-label={`Digit ${index + 1} of ${OTP_LENGTH}`}
            aria-invalid={hasError || undefined}
            aria-required="true"
            disabled={disabled}
            className={cn(
              // Base styles
              "h-12 w-10 rounded-lg border text-center text-lg font-semibold",
              "text-[#111111] caret-transparent",
              "transition-colors duration-150 outline-none",
              // Border colours
              "border-[#EAE7DF] bg-white",
              // Focus ring
              "focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/20",
              // Error state
              hasError && "border-red-400 focus:border-red-500 focus:ring-red-200",
              // Disabled state
              disabled && "opacity-50 cursor-not-allowed bg-gray-50"
            )}
            onChange={(e) => handleChange(e, index)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            onPaste={(e) => handlePaste(e, index)}
            onFocus={(e) => {
              // Select the digit on focus so typing replaces it cleanly
              e.target.select();
            }}
          />
        ))}
      </div>
    </div>
  );
}
