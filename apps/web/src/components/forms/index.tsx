"use client";

/**
 * OntDekker Form Components
 *
 * Reusable controlled form primitives using the design system tokens.
 * All components are accessible, keyboard-navigable, and typed strictly.
 *
 * Exports:
 *   TextInput     — single-line text field with label, hint, error, icon
 *   TextareaInput — multi-line field with optional character counter
 *   ToggleInput   — accessible switch (role=switch) with label + description
 *   FormField     — layout wrapper: label, hint, error, children slot
 */

import React, { useId } from "react";
import type {
  TextInputProps,
  TextareaInputProps,
  ToggleInputProps,
  FormFieldProps,
} from "./forms.types";

// ---------------------------------------------------------------------------
// Shared style tokens
// ---------------------------------------------------------------------------

const inputBase = [
  "w-full bg-gray-50 border border-gray-200 rounded-xl",
  "text-sm text-ink placeholder:text-muted-slate",
  "transition-all duration-[var(--duration-responsive)]",
  "focus:outline-none focus:bg-white focus:border-ink focus:ring-1 focus:ring-ink",
].join(" ");

const inputError = "border-red-300 focus:border-red-400 focus:ring-red-300";

const inputSizeClasses = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2.5",
  lg: "px-4 py-3 text-base",
};

// ---------------------------------------------------------------------------
// FormField — layout wrapper
// ---------------------------------------------------------------------------

export function FormField({
  label,
  htmlFor,
  hint,
  error,
  required = false,
  children,
  className = "",
}: FormFieldProps) {
  return (
    <div className={["flex flex-col gap-1", className].filter(Boolean).join(" ")}>
      <label
        htmlFor={htmlFor}
        className="text-xs font-mono uppercase tracking-wider text-muted-slate"
      >
        {label}
        {required && (
          <span className="ml-1 text-red-500" aria-hidden="true">
            *
          </span>
        )}
      </label>

      {children}

      {/* Error takes priority over hint */}
      {error ? (
        <p role="alert" className="text-xs text-red-500 mt-0.5">
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-muted-slate mt-0.5">{hint}</p>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// TextInput
// ---------------------------------------------------------------------------

export function TextInput({
  label,
  hint,
  error,
  inputSize = "md",
  leadingIcon: LeadingIcon,
  className = "",
  id: externalId,
  ...rest
}: TextInputProps) {
  const generatedId = useId();
  const inputId = externalId ?? generatedId;

  return (
    <FormField
      label={label ?? ""}
      htmlFor={inputId}
      hint={hint}
      error={error}
      className={label ? "" : className}
    >
      <div className="relative">
        {LeadingIcon && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
            <LeadingIcon
              size={15}
              strokeWidth={1.75}
              className="text-muted-slate"
              aria-hidden="true"
            />
          </span>
        )}
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
          className={[
            inputBase,
            inputSizeClasses[inputSize],
            error ? inputError : "",
            LeadingIcon ? "pl-9" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          {...rest}
        />
      </div>
    </FormField>
  );
}

// ---------------------------------------------------------------------------
// TextareaInput
// ---------------------------------------------------------------------------

export function TextareaInput({
  label,
  hint,
  error,
  showCount = false,
  maxLength,
  value,
  className = "",
  id: externalId,
  rows = 3,
  ...rest
}: TextareaInputProps) {
  const generatedId = useId();
  const inputId = externalId ?? generatedId;
  const charCount = typeof value === "string" ? value.length : 0;

  return (
    <FormField
      label={label ?? ""}
      htmlFor={inputId}
      hint={hint}
      error={error}
    >
      <div className="relative">
        <textarea
          id={inputId}
          rows={rows}
          maxLength={maxLength}
          value={value}
          aria-invalid={error ? true : undefined}
          className={[
            inputBase,
            "px-4 py-2.5 resize-none",
            error ? inputError : "",
            className,
          ]
            .filter(Boolean)
            .join(" ")}
          {...rest}
        />
        {showCount && maxLength && (
          <p className="text-[10px] font-mono text-muted-slate text-right mt-1">
            {charCount}/{maxLength}
          </p>
        )}
      </div>
    </FormField>
  );
}

// ---------------------------------------------------------------------------
// ToggleInput — accessible switch
// ---------------------------------------------------------------------------

export function ToggleInput({
  id,
  label,
  description,
  checked,
  onChange,
  disabled = false,
}: ToggleInputProps) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1">
        <label
          htmlFor={id}
          className={[
            "text-sm font-medium",
            disabled ? "text-muted-slate cursor-not-allowed" : "text-ink cursor-pointer",
          ].join(" ")}
        >
          {label}
        </label>
        {description && (
          <p className="text-xs text-muted-slate mt-0.5">{description}</p>
        )}
      </div>

      <button
        type="button"
        id={id}
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={[
          "relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent",
          "transition-colors duration-[var(--duration-responsive)]",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
          disabled
            ? "opacity-40 cursor-not-allowed"
            : "cursor-pointer",
          checked ? "bg-ink" : "bg-gray-200",
        ].join(" ")}
      >
        <span
          aria-hidden="true"
          className={[
            "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow",
            "transform transition-transform duration-[var(--duration-responsive)]",
            checked ? "translate-x-4" : "translate-x-0",
          ].join(" ")}
        />
        <span className="sr-only">{checked ? "Enabled" : "Disabled"}</span>
      </button>
    </div>
  );
}
