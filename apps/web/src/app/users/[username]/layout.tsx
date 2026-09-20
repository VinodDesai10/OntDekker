"use client";

/**
 * /users/[username] — Shared Layout
 *
 * Wraps the public profile route tree in the application shell (AppLayout)
 * so that /users/[username], /users/[username]/followers, and
 * /users/[username]/following all render with the same sidebar, container,
 * spacing, and typography as every other authenticated page (e.g. /profile,
 * /feed, /communities).
 *
 * This mirrors the approach used by apps/web/src/app/profile/layout.tsx.
 * No content logic lives here — only the layout shell injection.
 */

import { AppLayout } from "@/components/navigation/AppLayout";

export default function PublicProfileLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppLayout>{children}</AppLayout>;
}
