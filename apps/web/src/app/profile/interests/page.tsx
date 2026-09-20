"use client";

/**
 * /profile/interests — Edit Interests Page
 *
 * Backend contract (PATCH /users/me/interests):
 *   UpdateInterestsRequest: { interests: string[] }
 *
 * The backend REPLACES the full list — it is not additive.
 * The frontend sends the complete current list every time.
 *
 * Constraints (from backend schema):
 *   - Max 30 interests
 *   - Duplicates not allowed (case-insensitive)
 *   - Each interest string is trimmed
 *
 * UI: free-text tag entry — type and press Enter or comma to add.
 * Existing interests are prefilled. Each tag can be removed individually.
 *
 * Pre-fill strategy: profile passed as props to InterestsForm whose state
 * is initialised directly from those props. key=profile.id on InterestsForm
 * ensures re-initialisation if the profile identity ever changes.
 */

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, ArrowLeft, X, CheckCircle } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  getMyProfile,
  updateInterests,
  type PrivateProfileResponse,
} from "@/services/users";
import { ApiError } from "@/services/api";
import { MY_PROFILE_KEY } from "../page";

const MAX_INTERESTS = 30;

// ---------------------------------------------------------------------------
// Inner form — state initialised from props once on mount
// ---------------------------------------------------------------------------

function InterestsForm({ profile }: { profile: PrivateProfileResponse }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);

  const [tags, setTags] = useState<string[]>(
    profile.interests.map((i) => i.interest)
  );
  const [inputValue, setInputValue] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  function addTag(raw: string) {
    const tag = raw.trim();
    if (!tag) return;
    if (tags.length >= MAX_INTERESTS) {
      setLocalError(`You can add up to ${MAX_INTERESTS} interests.`);
      return;
    }
    if (tags.some((t) => t.toLowerCase() === tag.toLowerCase())) {
      setLocalError("That interest is already in your list.");
      return;
    }
    setLocalError(null);
    setTags((prev) => [...prev, tag]);
    setInputValue("");
  }

  function removeTag(tag: string) {
    setTags((prev) => prev.filter((t) => t !== tag));
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(inputValue);
    } else if (e.key === "Backspace" && !inputValue && tags.length > 0) {
      setTags((prev) => prev.slice(0, -1));
    }
  }

  const mutation = useMutation({
    mutationFn: (interests: string[]) => updateInterests({ interests }),
    onSuccess: (updated: PrivateProfileResponse) => {
      queryClient.setQueryData<PrivateProfileResponse>(MY_PROFILE_KEY, updated);
      setSuccess(true);
      setTimeout(() => router.push("/profile"), 1200);
    },
  });

  const mutationError =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.error
        ? "Something went wrong. Please try again."
        : null;

  const displayError = localError ?? mutationError;

  return (
    <div className="space-y-6">
      {/* Success */}
      {success && (
        <div
          role="status"
          className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-[#0F5132]"
        >
          <CheckCircle className="size-4" aria-hidden />
          Interests updated.
        </div>
      )}

      {/* Error */}
      {displayError && !success && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {displayError}
        </div>
      )}

      {/* Tag input area */}
      <div
        role="group"
        aria-label="Interests input"
        onClick={() => inputRef.current?.focus()}
        className="min-h-[3rem] cursor-text rounded-lg border border-[#EAE7DF] bg-white px-3 py-2 focus-within:border-[#111111] focus-within:ring-2 focus-within:ring-[#111111]/10"
      >
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => (
            <span
              key={tag}
              className="flex items-center gap-1 rounded-full border border-[#EAE7DF] bg-[#FBF9F4] px-2.5 py-1 text-xs text-[#111111]"
            >
              {tag}
              <button
                type="button"
                aria-label={`Remove ${tag}`}
                onClick={(e) => {
                  e.stopPropagation();
                  removeTag(tag);
                }}
                className="rounded-full p-0.5 hover:bg-[#EAE7DF]"
              >
                <X className="size-3" aria-hidden />
              </button>
            </span>
          ))}
          <input
            ref={inputRef}
            type="text"
            aria-label="Add interest"
            placeholder={tags.length === 0 ? "e.g. hiking, slow travel…" : ""}
            value={inputValue}
            onChange={(e) => {
              setLocalError(null);
              setInputValue(e.target.value);
            }}
            onKeyDown={handleKeyDown}
            onBlur={() => {
              if (inputValue.trim()) addTag(inputValue);
            }}
            disabled={mutation.isPending || tags.length >= MAX_INTERESTS}
            className="min-w-[120px] flex-1 bg-transparent text-sm text-[#111111] placeholder:text-gray-400 outline-none disabled:opacity-50"
          />
        </div>
      </div>

      <p className="text-xs text-gray-400">
        {tags.length}/{MAX_INTERESTS} interests
      </p>

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          type="button"
          onClick={() => mutation.mutate(tags)}
          disabled={mutation.isPending || success}
          className="flex-1"
          size="lg"
        >
          {mutation.isPending ? (
            <>
              <Loader2 className="mr-2 size-4 animate-spin" aria-hidden />
              Saving…
            </>
          ) : (
            "Save interests"
          )}
        </Button>
        <Link href="/profile">
          <Button type="button" variant="outline" size="lg">
            Cancel
          </Button>
        </Link>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page export
// ---------------------------------------------------------------------------

export default function InterestsPage() {
  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: MY_PROFILE_KEY,
    queryFn: getMyProfile,
    staleTime: 60_000,
  });

  return (
    <div className="space-y-6">
      <Link
        href="/profile"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 underline-offset-4 hover:underline"
      >
        <ArrowLeft className="size-3.5" aria-hidden />
        Back to profile
      </Link>

      <div>
        <h1 className="text-xl font-bold text-[#111111]">Interests</h1>
        <p className="mt-1 text-sm text-gray-500">
          Add travel themes you care about. Type and press Enter or comma.
        </p>
      </div>

      {profileLoading || !profile ? (
        <div className="flex justify-center py-16">
          <Loader2 className="size-6 animate-spin text-gray-400" aria-hidden />
        </div>
      ) : (
        <InterestsForm key={profile.id} profile={profile} />
      )}
    </div>
  );
}
