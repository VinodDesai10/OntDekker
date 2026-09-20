"use client";

/**
 * OntDekker — LogoutButton
 *
 * Reusable logout trigger component.
 * Uses AuthContext.logout() — does not make direct API calls.
 *
 * After logout navigates to /login.
 *
 * Designed to drop into any authenticated layout or navigation element.
 * The authenticated application shell (Checkpoint 6D) will wire this into
 * the persistent navigation bar.
 *
 * Props:
 *   className — optional extra Tailwind classes to merge (e.g. for placement)
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";

interface LogoutButtonProps {
  className?: string;
}

export function LogoutButton({ className }: LogoutButtonProps) {
  const { logout } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleLogout() {
    setLoading(true);
    try {
      await logout();
    } catch {
      // Remote revocation failure is non-fatal.
      // AuthContext.logout() already clears all local state regardless.
    } finally {
      // Navigate to login whether or not the remote revocation succeeded.
      setLoading(false);
      router.replace("/login");
    }
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleLogout}
      disabled={loading}
      className={className}
      aria-label="Sign out"
    >
      {loading ? (
        <Loader2 className="size-4 animate-spin" aria-hidden />
      ) : (
        <LogOut className="size-4" aria-hidden />
      )}
      <span className="ml-1.5">{loading ? "Signing out…" : "Sign out"}</span>
    </Button>
  );
}
