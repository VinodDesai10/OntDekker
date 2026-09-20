import type React from "react";

// ---------------------------------------------------------------------------
// TextInput
// ---------------------------------------------------------------------------

export interface TextInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string;
  hint?: string;
  error?: string;
  /** Matches design system sizing; does NOT conflict with HTML input size */
  inputSize?: "sm" | "md" | "lg";
  /** Leading icon component */
  leadingIcon?: React.ComponentType<{
    size?: number;
    strokeWidth?: number;
    className?: string;
    "aria-hidden"?: boolean | "true" | "false";
  }>;
}

// ---------------------------------------------------------------------------
// TextareaInput
// ---------------------------------------------------------------------------

export interface TextareaInputProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
  showCount?: boolean;
  maxLength?: number;
}

// ---------------------------------------------------------------------------
// ToggleInput
// ---------------------------------------------------------------------------

export interface ToggleInputProps {
  id: string;
  label: string;
  description?: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
}

// ---------------------------------------------------------------------------
// FormField (layout wrapper)
// ---------------------------------------------------------------------------

export interface FormFieldProps {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
  className?: string;
}
