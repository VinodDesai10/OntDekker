/**
 * OntDekker — AuthCard
 *
 * Shared card shell used by all authentication screens.
 * Provides consistent centering, max-width, brand mark, and surface styling.
 *
 * Design:
 *   - Sand Cream canvas (#FBF9F4) full-height background
 *   - White card surface, Glacier Mist border (#EAE7DF)
 *   - Brand word-mark centered above the card
 *   - Responsive: full-width on mobile, fixed 440px on desktop
 */

import { cn } from "@/lib/utils";

interface AuthCardProps {
  /** Screen title shown inside the card (e.g. "Sign in") */
  title: string;
  /** Optional subtitle / instruction below the title */
  description?: string;
  children: React.ReactNode;
  className?: string;
}

export function AuthCard({
  title,
  description,
  children,
  className,
}: AuthCardProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#FBF9F4] px-4 py-12">
      {/* Brand mark */}
      <div className="mb-8 text-center">
        <span className="text-2xl font-bold tracking-tight text-[#111111]">
          OntDekker
        </span>
      </div>

      {/* Card */}
      <div
        className={cn(
          "w-full max-w-[440px] rounded-xl border border-[#EAE7DF] bg-white px-8 py-10 shadow-sm",
          className
        )}
      >
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight text-[#111111]">
            {title}
          </h1>
          {description && (
            <p className="mt-1.5 text-sm leading-relaxed text-gray-500">
              {description}
            </p>
          )}
        </div>

        {children}
      </div>
    </div>
  );
}
