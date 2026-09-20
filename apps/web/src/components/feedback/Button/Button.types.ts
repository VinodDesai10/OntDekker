import type React from "react";

export type ButtonVariant = "primary" | "secondary" | "outline" | "ghost" | "danger";
export type ButtonSize = "xs" | "sm" | "md" | "lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual treatment — defaults to "primary" */
  variant?: ButtonVariant;
  /** Size — defaults to "md" */
  size?: ButtonSize;
  /** Shows a rotating spinner and disables the button */
  loading?: boolean;
  /** Lucide (or any) icon component rendered alongside the label */
  icon?: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  /** Whether the icon appears before or after the label — defaults to "left" */
  iconPosition?: "left" | "right";
  /** When true the button is rendered as a square icon-only button */
  iconOnly?: boolean;
}
