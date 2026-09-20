"use client";

/**
 * OntDekker Button
 *
 * Reusable action component covering all button use-cases.
 *
 * Variants:
 *   primary   — Black fill, white text. High-priority actions.
 *   secondary — Gray-50 fill, gray-800 text. Supporting actions.
 *   outline   — White fill, gray border. Neutral actions.
 *   ghost     — Transparent. Low-emphasis inline actions.
 *   danger    — Red fill. Destructive actions.
 *
 * Sizes: xs | sm | md | lg
 *
 * Motion:
 *   - whileTap scale 0.97 (100ms, instant easing) per motion spec
 *   - loading spinner rotation
 *
 * Accessibility:
 *   - aria-busy during loading
 *   - aria-disabled when disabled or loading
 *   - focus-visible ring-black per design system
 *   - Forwards ref so parent components can manage focus (e.g. Dialog)
 */

import React from "react";
import { motion } from "motion/react";
import { Loader2 } from "lucide-react";
import type { ButtonProps } from "./Button.types";

// ---------------------------------------------------------------------------
// Style maps
// ---------------------------------------------------------------------------

const variantClasses: Record<string, string> = {
  primary:
    "bg-ink text-white shadow-xs hover:bg-neutral-800 active:bg-neutral-900",
  secondary:
    "bg-gray-50 text-gray-800 border border-gray-200 hover:bg-gray-100 active:bg-gray-200",
  outline:
    "bg-white text-ink border border-gray-200 hover:bg-gray-50 active:bg-gray-100",
  ghost:
    "bg-transparent text-charcoal hover:bg-gray-50 active:bg-gray-100",
  danger:
    "bg-red-600 text-white shadow-xs hover:bg-red-700 active:bg-red-800",
};

const sizeClasses: Record<string, string> = {
  xs: "h-7 px-2.5 text-xs gap-1 rounded-lg",
  sm: "h-8 px-3 text-xs gap-1.5 rounded-xl",
  md: "h-9 px-4 text-sm gap-2 rounded-xl",
  lg: "h-11 px-5 text-sm gap-2 rounded-xl",
};

const iconOnlySizeClasses: Record<string, string> = {
  xs: "h-7 w-7 rounded-lg",
  sm: "h-8 w-8 rounded-xl",
  md: "h-9 w-9 rounded-xl",
  lg: "h-11 w-11 rounded-xl",
};

const iconSizeClasses: Record<string, string> = {
  xs: "w-3 h-3",
  sm: "w-3.5 h-3.5",
  md: "w-4 h-4",
  lg: "w-[18px] h-[18px]",
};

// ---------------------------------------------------------------------------
// Component (forwardRef so parent can programmatically focus)
// ---------------------------------------------------------------------------

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "primary",
      size = "md",
      loading = false,
      icon: Icon,
      iconPosition = "left",
      iconOnly = false,
      disabled,
      className = "",
      children,
      onClick,
      onMouseEnter,
      onMouseLeave,
      onFocus,
      onBlur,
      type = "button",
      ...rest
    },
    ref,
  ) {
    const isDisabled = disabled || loading;
    const iconClass = iconSizeClasses[size];

    const baseClasses = [
      "relative inline-flex items-center justify-center",
      "font-medium select-none",
      "transition-all duration-[var(--duration-responsive)] ease-[var(--ease-standard)]",
      "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
      isDisabled ? "opacity-50 cursor-not-allowed pointer-events-none" : "cursor-pointer",
      variantClasses[variant],
      iconOnly ? iconOnlySizeClasses[size] : sizeClasses[size],
      className,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <motion.button
        ref={ref}
        type={type}
        disabled={isDisabled}
        aria-busy={loading || undefined}
        aria-disabled={isDisabled || undefined}
        className={baseClasses}
        whileTap={isDisabled ? undefined : { scale: 0.97 }}
        transition={{ duration: 0.1, ease: [0.4, 0, 1, 1] }}
        onClick={onClick}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        onFocus={onFocus}
        onBlur={onBlur}
        id={rest.id}
        name={(rest as React.ButtonHTMLAttributes<HTMLButtonElement>).name}
        form={(rest as React.ButtonHTMLAttributes<HTMLButtonElement>).form}
        value={(rest as React.ButtonHTMLAttributes<HTMLButtonElement>).value}
        data-testid={(rest as { "data-testid"?: string })["data-testid"]}
      >
        {loading && (
          <Loader2
            className={`${iconClass} animate-spin flex-shrink-0`}
            aria-hidden="true"
          />
        )}
        {!loading && Icon && iconPosition === "left" && (
          <Icon className={`${iconClass} flex-shrink-0`} aria-hidden />
        )}
        {!iconOnly && children && (
          <span className="truncate">{children}</span>
        )}
        {!loading && Icon && iconPosition === "right" && (
          <Icon className={`${iconClass} flex-shrink-0`} aria-hidden />
        )}
      </motion.button>
    );
  },
);

export default Button;
