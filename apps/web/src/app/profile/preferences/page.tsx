"use client";

/**
 * /profile/preferences — Travel Preferences Page
 *
 * Backend contract (PATCH /users/me/preferences):
 *   UpdatePreferencesRequest — all fields optional:
 *     travel_style: string | null       (max 50)
 *     budget: string | null             (max 50)
 *     adventure_level: string | null    (max 50)
 *     languages: string[] | null
 *     preferred_destinations: string[] | null
 *     notifications_enabled: boolean | null
 *     profile_public: boolean | null
 *
 * No enum values are enforced by the backend — free-text for string fields.
 * Suggested option buttons provided for UX only; custom values are accepted.
 *
 * Pre-fill strategy: profile passed as props to PreferencesForm whose state
 * is initialised directly from those props (no useEffect setState).
 * key=profile.id on PreferencesForm ensures re-initialisation if needed.
 */

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, ArrowLeft, X, CheckCircle } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  getMyProfile,
  updatePreferences,
  type PrivateProfileResponse,
} from "@/services/users";
import { ApiError } from "@/services/api";
import { cn } from "@/lib/utils";
import { MY_PROFILE_KEY } from "../page";

// Suggested values for UX — backend accepts any string
const TRAVEL_STYLE_OPTIONS = ["Solo", "Couple", "Group", "Family", "Digital nomad"];
const BUDGET_OPTIONS = ["Budget", "Mid-range", "Luxury", "Variable"];
const ADVENTURE_OPTIONS = ["Low", "Moderate", "High", "Extreme"];

// ---------------------------------------------------------------------------
// Pill option selector
// ---------------------------------------------------------------------------

function PillSelector({
  label,
  options,
  value,
  onChange,
  disabled,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-[#111111]">{label}</label>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            disabled={disabled}
            onClick={() => onChange(value === opt ? "" : opt)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition disabled:opacity-50",
              value === opt
                ? "border-[#111111] bg-[#111111] text-white"
                : "border-[#EAE7DF] bg-white text-[#111111] hover:border-[#111111]"
            )}
            aria-pressed={value === opt}
          >
            {opt}
          </button>
        ))}
        {/* Active custom value badge */}
        {value && !options.includes(value) && (
          <span className="flex items-center gap-1 rounded-full border border-[#111111] bg-[#111111] px-3 py-1 text-xs text-white">
            {value}
            <button
              type="button"
              aria-label={`Remove custom ${label.toLowerCase()}`}
              onClick={() => onChange("")}
              className="rounded-full p-0.5 hover:bg-white/20"
            >
              <X className="size-3" aria-hidden />
            </button>
          </span>
        )}
      </div>
      {/* Free-text custom entry */}
      <input
        type="text"
        placeholder={`Custom ${label.toLowerCase()}…`}
        value={options.includes(value) || !value ? "" : value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        maxLength={50}
        className="w-full rounded-lg border border-[#EAE7DF] bg-white px-3.5 py-2 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tag list input (languages, preferred destinations)
// ---------------------------------------------------------------------------

function TagListInput({
  label,
  placeholder,
  tags,
  onChange,
  disabled,
}: {
  label: string;
  placeholder: string;
  tags: string[];
  onChange: (tags: string[]) => void;
  disabled: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [inputValue, setInputValue] = useState("");

  function addTag(raw: string) {
    const tag = raw.trim();
    if (!tag) return;
    if (tags.some((t) => t.toLowerCase() === tag.toLowerCase())) return;
    onChange([...tags, tag]);
    setInputValue("");
  }

  function removeTag(tag: string) {
    onChange(tags.filter((t) => t !== tag));
  }

  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-[#111111]">{label}</label>
      <div
        onClick={() => inputRef.current?.focus()}
        className="min-h-[2.75rem] cursor-text rounded-lg border border-[#EAE7DF] bg-white px-3 py-2 focus-within:border-[#111111] focus-within:ring-2 focus-within:ring-[#111111]/10"
      >
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => (
            <span
              key={tag}
              className="flex items-center gap-1 rounded-full border border-[#EAE7DF] bg-[#FBF9F4] px-2.5 py-0.5 text-xs text-[#111111]"
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
            placeholder={tags.length === 0 ? placeholder : ""}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === ",") {
                e.preventDefault();
                addTag(inputValue);
              } else if (
                e.key === "Backspace" &&
                !inputValue &&
                tags.length > 0
              ) {
                onChange(tags.slice(0, -1));
              }
            }}
            onBlur={() => {
              if (inputValue.trim()) addTag(inputValue);
            }}
            disabled={disabled}
            className="min-w-[100px] flex-1 bg-transparent text-sm text-[#111111] placeholder:text-gray-400 outline-none disabled:opacity-50"
          />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inner form — state initialised directly from props on mount
// ---------------------------------------------------------------------------

function PreferencesForm({ profile }: { profile: PrivateProfileResponse }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const p = profile.preferences;

  const [travelStyle, setTravelStyle] = useState(p?.travel_style ?? "");
  const [budget, setBudget] = useState(p?.budget ?? "");
  const [adventureLevel, setAdventureLevel] = useState(
    p?.adventure_level ?? ""
  );
  const [languages, setLanguages] = useState<string[]>(p?.languages ?? []);
  const [destinations, setDestinations] = useState<string[]>(
    p?.preferred_destinations ?? []
  );
  const [notificationsEnabled, setNotificationsEnabled] = useState(
    p?.notifications_enabled ?? true
  );
  const [profilePublic, setProfilePublic] = useState(
    p?.profile_public ?? true
  );
  const [success, setSuccess] = useState(false);

  const mutation = useMutation({
    mutationFn: updatePreferences,
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

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSuccess(false);
    mutation.mutate({
      travel_style: travelStyle || null,
      budget: budget || null,
      adventure_level: adventureLevel || null,
      languages: languages.length > 0 ? languages : null,
      preferred_destinations: destinations.length > 0 ? destinations : null,
      notifications_enabled: notificationsEnabled,
      profile_public: profilePublic,
    });
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      {/* Success */}
      {success && (
        <div
          role="status"
          className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-[#0F5132]"
        >
          <CheckCircle className="size-4" aria-hidden />
          Preferences updated.
        </div>
      )}

      {/* Error */}
      {mutationError && !success && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {mutationError}
        </div>
      )}

      <PillSelector
        label="Travel style"
        options={TRAVEL_STYLE_OPTIONS}
        value={travelStyle}
        onChange={setTravelStyle}
        disabled={mutation.isPending}
      />

      <PillSelector
        label="Budget"
        options={BUDGET_OPTIONS}
        value={budget}
        onChange={setBudget}
        disabled={mutation.isPending}
      />

      <PillSelector
        label="Adventure level"
        options={ADVENTURE_OPTIONS}
        value={adventureLevel}
        onChange={setAdventureLevel}
        disabled={mutation.isPending}
      />

      <TagListInput
        label="Languages"
        placeholder="e.g. English, Dutch…"
        tags={languages}
        onChange={setLanguages}
        disabled={mutation.isPending}
      />

      <TagListInput
        label="Preferred destinations"
        placeholder="e.g. Patagonia, Iceland…"
        tags={destinations}
        onChange={setDestinations}
        disabled={mutation.isPending}
      />

      {/* Boolean toggles */}
      <div className="space-y-3 rounded-lg border border-[#EAE7DF] bg-white p-4">
        <label className="flex items-center justify-between gap-4">
          <span className="text-sm text-[#111111]">Receive notifications</span>
          <input
            type="checkbox"
            checked={notificationsEnabled}
            onChange={(e) => setNotificationsEnabled(e.target.checked)}
            disabled={mutation.isPending}
            className="size-4 accent-[#111111]"
          />
        </label>
        <hr className="border-[#EAE7DF]" />
        <label className="flex items-center justify-between gap-4">
          <span className="text-sm text-[#111111]">
            Public profile
            <span className="ml-1.5 text-xs text-gray-400">
              (visible to other users)
            </span>
          </span>
          <input
            type="checkbox"
            checked={profilePublic}
            onChange={(e) => setProfilePublic(e.target.checked)}
            disabled={mutation.isPending}
            className="size-4 accent-[#111111]"
          />
        </label>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <Button
          type="submit"
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
            "Save preferences"
          )}
        </Button>
        <Link href="/profile">
          <Button type="button" variant="outline" size="lg">
            Cancel
          </Button>
        </Link>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Page export
// ---------------------------------------------------------------------------

export default function PreferencesPage() {
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
        <h1 className="text-xl font-bold text-[#111111]">Travel preferences</h1>
        <p className="mt-1 text-sm text-gray-500">
          Help us and the community understand how you travel.
        </p>
      </div>

      {profileLoading || !profile ? (
        <div className="flex justify-center py-16">
          <Loader2 className="size-6 animate-spin text-gray-400" aria-hidden />
        </div>
      ) : (
        <PreferencesForm key={profile.id} profile={profile} />
      )}
    </div>
  );
}
