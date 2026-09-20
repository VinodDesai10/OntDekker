"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Compass, Users, MapPin, Map, ArrowRight } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

/**
 * OntDekker Landing Page
 *
 * Public landing page for unauthenticated visitors highlighting OntDekker as a
 * travel social platform built around Stories, Communities, Expeditions, and Guides.
 * Automatically redirects authenticated users to /feed.
 */
export default function LandingPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/feed");
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <div className="min-h-screen bg-[#FBF9F4] text-[#111111] flex flex-col font-sans">
      {/* ── Navigation Header ────────────────────────────────────────────── */}
      <header className="w-full border-b border-[#EAE7DF] bg-white/80 backdrop-blur-sm sticky top-0 z-20">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-xl font-bold tracking-tight text-[#111111]">
              OntDekker
            </span>
          </Link>

          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="text-sm font-medium text-[#111111] hover:text-gray-600 transition-colors"
            >
              Log in
            </Link>
            <Link
              href="/register"
              className="rounded-xl bg-[#111111] px-4.5 py-2 text-sm font-medium text-white transition-all hover:bg-[#333333] shadow-sm"
            >
              Register
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero Section ─────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-6 py-16 sm:py-24 max-w-5xl mx-auto space-y-12">
        {/* Brand Positioning Header */}
        <div className="space-y-6 max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-[#EAE7DF] bg-white px-4 py-1.5 text-xs font-medium text-gray-600 shadow-2xs">
            <span className="inline-block size-1.5 rounded-full bg-[#111111]" />
            <span>The Travel Social Platform</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-[#111111] leading-[1.12]">
            Discover the world through real stories, shared expeditions, and genuine connections.
          </h1>

          <p className="text-base sm:text-lg text-gray-600 max-w-2xl mx-auto leading-relaxed font-normal">
            Join niche travel communities, explore authentic stories, plan group expeditions,
            and connect with verified local guides—all in one place.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 w-full max-w-xs sm:max-w-sm">
          <Link
            href="/register"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-[#111111] px-7 py-3.5 text-sm font-semibold text-white transition-all hover:bg-[#333333] shadow-sm"
          >
            Start Exploring
            <ArrowRight size={16} />
          </Link>

          <Link
            href="/login"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-[#EAE7DF] bg-white px-7 py-3.5 text-sm font-semibold text-[#111111] transition-all hover:bg-gray-100/80"
          >
            Sign In
          </Link>
        </div>

        {/* ── 4 Core Feature Cards ────────────────────────────────────────── */}
        <div className="pt-8 w-full">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 text-left w-full">
            {/* Card 1: Discover Stories */}
            <div className="group rounded-2xl border border-[#EAE7DF] bg-white p-6 space-y-3 transition-all duration-200 hover:border-gray-300 hover:shadow-md">
              <div className="size-11 rounded-xl bg-[#FBF9F4] flex items-center justify-center text-[#111111] group-hover:scale-105 transition-transform">
                <Compass size={22} strokeWidth={1.75} />
              </div>
              <h3 className="font-bold text-base text-[#111111]">
                Discover Stories
              </h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                Share experiences and explore authentic travel journals from explorers worldwide.
              </p>
            </div>

            {/* Card 2: Travel Communities */}
            <div className="group rounded-2xl border border-[#EAE7DF] bg-white p-6 space-y-3 transition-all duration-200 hover:border-gray-300 hover:shadow-md">
              <div className="size-11 rounded-xl bg-[#FBF9F4] flex items-center justify-center text-[#111111] group-hover:scale-105 transition-transform">
                <Users size={22} strokeWidth={1.75} />
              </div>
              <h3 className="font-bold text-base text-[#111111]">
                Travel Communities
              </h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                Join niche communities, swap local insights, and meet like-minded travelers.
              </p>
            </div>

            {/* Card 3: Expeditions */}
            <div className="group rounded-2xl border border-[#EAE7DF] bg-white p-6 space-y-3 transition-all duration-200 hover:border-gray-300 hover:shadow-md">
              <div className="size-11 rounded-xl bg-[#FBF9F4] flex items-center justify-center text-[#111111] group-hover:scale-105 transition-transform">
                <Map size={22} strokeWidth={1.75} />
              </div>
              <h3 className="font-bold text-base text-[#111111]">
                Expeditions
              </h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                Plan, co-create, and join real offline group adventures together.
              </p>
            </div>

            {/* Card 4: Local Guides */}
            <div className="group rounded-2xl border border-[#EAE7DF] bg-white p-6 space-y-3 transition-all duration-200 hover:border-gray-300 hover:shadow-md">
              <div className="size-11 rounded-xl bg-[#FBF9F4] flex items-center justify-center text-[#111111] group-hover:scale-105 transition-transform">
                <MapPin size={22} strokeWidth={1.75} />
              </div>
              <h3 className="font-bold text-base text-[#111111]">
                Local Guides
              </h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                Connect with verified local hosts and experts when you need them.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="w-full border-t border-[#EAE7DF] bg-white py-6 text-center text-xs text-gray-400">
        © {new Date().getFullYear()} OntDekker. All rights reserved.
      </footer>
    </div>
  );
}
