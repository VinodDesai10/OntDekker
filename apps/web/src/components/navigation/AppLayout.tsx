"use client";

/**
 * OntDekker AppLayout — Authenticated Application Shell
 *
 * Provides a responsive persistent sidebar navigation across all authenticated
 * modules (/feed, /communities, /guides, /my-trips, /profile).
 *
 * Shared Container:
 *   Ensures consistent max-width, padding, spacing, and font hierarchy.
 *   Sidebar width (w-64) is strictly respected so main content never overlaps.
 *
 * Profile data is fetched via TanStack Query using the same MY_PROFILE_KEY as
 * the profile page, so that cache updates from profile edits and image uploads
 * are immediately reflected in the sidebar without a separate SWR revalidation.
 */

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Compass,
  Users,
  MapPin,
  Map,
  Backpack,
  User,
  Menu,
  X,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { LogoutButton } from "@/components/auth/LogoutButton";
import { useAuth } from "@/contexts/AuthContext";
import { getMyProfile } from "@/services/users";
import { MY_PROFILE_KEY } from "@/app/profile/page";
import { cn } from "@/lib/utils";

interface AppLayoutProps {
  children: React.ReactNode;
}

const NAV_ITEMS = [
  {
    label: "Feed",
    href: "/feed",
    icon: Compass,
  },
  {
    label: "Communities",
    href: "/communities",
    icon: Users,
  },
  {
    label: "Guides",
    href: "/guides",
    icon: MapPin,
  },
  {
    label: "Trips",
    href: "/trips",
    icon: Map,
  },
  {
    label: "My Trips",
    href: "/my-trips",
    icon: Backpack,
  },
  {
    label: "Profile",
    href: "/profile",
    icon: User,
  },
] as const;

export function AppLayout({ children }: AppLayoutProps) {
  const pathname = usePathname();
  const { user, isAuthenticated } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Fetch full user profile for sidebar display using the same TanStack Query
  // key as the profile page (MY_PROFILE_KEY). This means cache updates from
  // profile edits, username changes, and image uploads are immediately
  // reflected here without a separate SWR revalidation cycle.
  const { data: profile } = useQuery({
    queryKey: MY_PROFILE_KEY,
    queryFn: getMyProfile,
    enabled: isAuthenticated,
    staleTime: 60_000,
  });

  // Resolve display values: prefer profile data, fall back to auth user email
  const displayName = profile?.display_name ?? profile?.username ?? user?.email ?? "";
  const displaySubtitle = profile?.username ? `@${profile.username}` : user?.email ?? "";
  const avatarInitial = (profile?.display_name ?? profile?.username ?? user?.email ?? "U")
    .charAt(0)
    .toUpperCase();
  const avatarUrl = profile?.avatar_url ?? null;

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-[#FBF9F4] text-[#111111] flex flex-col md:flex-row antialiased font-sans">
        {/* ── Mobile Header ───────────────────────────────────────────────── */}
        <header className="md:hidden sticky top-0 z-30 flex items-center justify-between border-b border-[#EAE7DF] bg-white/90 px-4 py-3 backdrop-blur-sm">
          <Link href="/feed" className="flex items-center gap-2">
            <span className="text-lg font-bold tracking-tight text-[#111111]">
              OntDekker
            </span>
          </Link>
          <button
            type="button"
            onClick={() => setMobileMenuOpen((v) => !v)}
            className="rounded-lg p-2 text-gray-600 hover:bg-gray-100 transition-colors"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </header>

        {/* ── Mobile Overlay Menu ─────────────────────────────────────────── */}
        {mobileMenuOpen && (
          <div className="md:hidden fixed inset-0 z-20 top-[53px] bg-white flex flex-col justify-between p-6">
            <nav className="space-y-2">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const active = pathname?.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-colors",
                      active
                        ? "bg-[#111111] text-white"
                        : "text-gray-600 hover:bg-gray-100"
                    )}
                  >
                    <Icon size={18} />
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <div className="border-t border-[#EAE7DF] pt-4 flex items-center justify-between">
              <div className="truncate text-xs text-gray-500 font-medium">
                {displayName || user?.email}
              </div>
              <LogoutButton />
            </div>
          </div>
        )}

        {/* ── Desktop Sidebar Navigation ──────────────────────────────────── */}
        <aside data-testid="app-sidebar" className="hidden md:flex flex-col justify-between w-64 border-r border-[#EAE7DF] bg-white p-6 sticky top-0 h-screen shrink-0 z-20">
          <div className="space-y-8">
            {/* Brand */}
            <Link href="/feed" className="block space-y-0.5">
              <span className="text-xl font-bold tracking-tight text-[#111111]">
                OntDekker
              </span>
              <p className="text-[10px] text-gray-400 font-semibold tracking-wider uppercase">
                Slow Travel Platform
              </p>
            </Link>

            {/* Nav links */}
            <nav className="space-y-1.5" aria-label="Main navigation">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const active = pathname?.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all duration-150",
                      active
                        ? "bg-[#111111] text-white shadow-sm"
                        : "text-gray-600 hover:bg-gray-100/80 hover:text-[#111111]"
                    )}
                  >
                    <Icon size={18} className={active ? "text-white" : "text-gray-500"} />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* User profile & Logout footer */}
          <div className="border-t border-[#EAE7DF] pt-4 space-y-3">
            {user && (
              <div className="flex items-center gap-2.5 px-1">
                {avatarUrl ? (
                  <img
                    src={avatarUrl}
                    alt={displayName}
                    className="size-8 shrink-0 rounded-full object-cover border border-[#EAE7DF]"
                  />
                ) : (
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-[#111111] text-xs font-bold text-white">
                    {avatarInitial}
                  </div>
                )}
                <div className="truncate">
                  <p className="truncate text-xs font-semibold text-[#111111]">
                    {displayName}
                  </p>
                  <p className="truncate text-[10px] text-gray-400">
                    {displaySubtitle}
                  </p>
                </div>
              </div>
            )}
            <LogoutButton className="w-full justify-start text-xs text-gray-600 hover:bg-gray-100" />
          </div>
        </aside>

        {/* ── Main Content Area ───────────────────────────────────────────── */}
        <main data-testid="app-main-content" className="flex-1 min-w-0 overflow-y-auto p-4 sm:p-6 md:p-8">
          <div className="max-w-7xl mx-auto space-y-6">
            {children}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
