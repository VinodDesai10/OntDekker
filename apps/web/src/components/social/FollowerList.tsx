"use client";

/**
 * OntDekker — FollowerList
 *
 * Shared list component used by both the Followers and Following pages.
 *
 * Renders a paginated list of FollowerSummary entries matching the
 * PaginatedFollowersResponse contract:
 *   { items: FollowerSummary[], total: number, page: number, size: number }
 *
 * Each entry links to that user's public profile (/users/{username}).
 * Avatar initials fallback is shown when avatar_url is null.
 *
 * Pagination: prev/next buttons based on total/size/page values from backend.
 * Default page size: 20 (matches backend default and max=100).
 */

import Image from "next/image";
import Link from "next/link";
import { Loader2, UserRound, AlertTriangle, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PaginatedFollowersResponse } from "@/services/users";
import { ApiError } from "@/services/api";

interface FollowerListProps {
  /** Display title, e.g. "Followers" or "Following" */
  title: string;
  data: PaginatedFollowersResponse | undefined;
  isLoading: boolean;
  error: unknown;
  page: number;
  onPageChange: (page: number) => void;
}

export function FollowerList({
  title,
  data,
  isLoading,
  error,
  page,
  onPageChange,
}: FollowerListProps) {
  const totalPages = data ? Math.ceil(data.total / data.size) : 0;
  const hasPrev = page > 1;
  const hasNext = page < totalPages;

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="size-6 animate-spin text-gray-400" aria-hidden />
        <span className="sr-only">Loading {title.toLowerCase()}…</span>
      </div>
    );
  }

  if (error) {
    const msg =
      error instanceof ApiError
        ? error.message
        : `Could not load ${title.toLowerCase()}. Please try again.`;
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <AlertTriangle className="size-7 text-[#F59E0B]" aria-hidden />
        <p className="text-sm text-gray-500">{msg}</p>
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <UserRound className="size-8 text-[#EAE7DF]" aria-hidden />
        <p className="text-sm text-gray-400">No {title.toLowerCase()} yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {/* Count */}
      <p className="mb-3 text-xs text-gray-400">
        {data.total} {title.toLowerCase()}
      </p>

      {/* List */}
      <ul className="divide-y divide-[#EAE7DF]" aria-label={title}>
        {data.items.map((person) => (
          <li key={person.id}>
            <Link
              href={`/users/${person.username}`}
              className="flex items-center gap-3 rounded-lg px-2 py-3 transition hover:bg-[#FBF9F4]"
            >
              {/* Avatar */}
              <div className="relative size-10 shrink-0 overflow-hidden rounded-full bg-[#EAE7DF]">
                {person.avatar_url ? (
                  <Image
                    src={person.avatar_url}
                    alt={`${person.display_name} avatar`}
                    fill
                    className="object-cover"
                    sizes="40px"
                  />
                ) : (
                  <span className="flex h-full items-center justify-center text-sm font-bold text-gray-400">
                    {person.display_name?.charAt(0)?.toUpperCase() ?? "?"}
                  </span>
                )}
              </div>

              {/* Identity */}
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-[#111111]">
                  {person.display_name}
                </p>
                <p className="truncate text-xs text-gray-400">
                  @{person.username}
                </p>
              </div>
            </Link>
          </li>
        ))}
      </ul>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={!hasPrev}
            aria-label="Previous page"
          >
            <ChevronLeft className="size-4" aria-hidden />
            Prev
          </Button>
          <span className="text-xs text-gray-400">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={!hasNext}
            aria-label="Next page"
          >
            Next
            <ChevronRight className="size-4" aria-hidden />
          </Button>
        </div>
      )}
    </div>
  );
}
