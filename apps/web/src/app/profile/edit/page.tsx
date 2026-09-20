"use client";

/**
 * /profile/edit — Edit Profile Page
 *
 * Prefills all UpdateProfileRequest fields from the cached profile.
 * Backend contract (PUT /users/me): all fields optional.
 *   - username: 3–30 chars, alphanumeric + underscore
 *   - display_name: 1–100 chars
 *   - bio: max 500 chars
 *   - city: max 100 chars
 *   - country: max 100 chars
 *
 * On success: updates the TanStack Query cache and navigates back to /profile.
 *
 * Form pre-fill strategy: profile data passed as props to an inner form
 * component whose default state is derived once from those props. A React
 * key reset triggers re-initialisation when the profile loads.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, ArrowLeft, CheckCircle } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  getMyProfile,
  updateMyProfile,
  type PrivateProfileResponse,
} from "@/services/users";
import { ApiError } from "@/services/api";
import { MY_PROFILE_KEY } from "../page";

const USERNAME_REGEX = /^[a-zA-Z0-9_]{3,30}$/;

// ---------------------------------------------------------------------------
// Inner form — receives prefilled defaults once, owns its own state
// ---------------------------------------------------------------------------

function EditForm({ profile }: { profile: PrivateProfileResponse }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [username, setUsername] = useState(profile.username ?? "");
  const [displayName, setDisplayName] = useState(profile.display_name ?? "");
  const [bio, setBio] = useState(profile.bio ?? "");
  const [city, setCity] = useState(profile.city ?? "");
  const [country, setCountry] = useState(profile.country ?? "");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const mutation = useMutation({
    mutationFn: updateMyProfile,
    onSuccess: (updated: PrivateProfileResponse) => {
      queryClient.setQueryData<PrivateProfileResponse>(MY_PROFILE_KEY, updated);
      setSuccess(true);
      setTimeout(() => router.push("/profile"), 1200);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setValidationError(null);
    setSuccess(false);

    if (!displayName.trim()) {
      setValidationError("Display name is required.");
      return;
    }
    if (displayName.trim().length > 100) {
      setValidationError("Display name must be 100 characters or fewer.");
      return;
    }
    if (username && !USERNAME_REGEX.test(username)) {
      setValidationError(
        "Username must be 3–30 characters: letters, digits, and underscores only."
      );
      return;
    }
    if (bio.length > 500) {
      setValidationError("Bio must be 500 characters or fewer.");
      return;
    }
    if (city.length > 100) {
      setValidationError("City must be 100 characters or fewer.");
      return;
    }
    if (country.length > 100) {
      setValidationError("Country must be 100 characters or fewer.");
      return;
    }

    mutation.mutate({
      username: username.trim() || null,
      display_name: displayName.trim(),
      bio: bio.trim() || null,
      city: city.trim() || null,
      country: country.trim() || null,
    });
  }

  const mutationError =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.error
        ? "Something went wrong. Please try again."
        : null;

  const displayError = validationError ?? mutationError;

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      {/* Success banner */}
      {success && (
        <div
          role="status"
          className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-[#0F5132]"
        >
          <CheckCircle className="size-4" aria-hidden />
          Profile updated.
        </div>
      )}

      {/* Error banner */}
      {displayError && !success && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {displayError}
        </div>
      )}

      {/* Display name */}
      <div className="space-y-1.5">
        <label
          htmlFor="display_name"
          className="block text-sm font-medium text-[#111111]"
        >
          Display name <span aria-hidden className="text-red-400">*</span>
        </label>
        <input
          id="display_name"
          type="text"
          required
          maxLength={100}
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          disabled={mutation.isPending}
          className="w-full rounded-lg border border-[#EAE7DF] bg-white px-3.5 py-2.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
        />
      </div>

      {/* Username */}
      <div className="space-y-1.5">
        <label
          htmlFor="username"
          className="block text-sm font-medium text-[#111111]"
        >
          Username
        </label>
        <input
          id="username"
          type="text"
          maxLength={30}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={mutation.isPending}
          placeholder="letters, digits, underscores"
          className="w-full rounded-lg border border-[#EAE7DF] bg-white px-3.5 py-2.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
        />
        <p className="text-xs text-gray-400">
          3–30 characters. Letters, digits, underscores.
        </p>
      </div>

      {/* Bio */}
      <div className="space-y-1.5">
        <div className="flex items-baseline justify-between">
          <label
            htmlFor="bio"
            className="block text-sm font-medium text-[#111111]"
          >
            Bio
          </label>
          <span className="text-xs text-gray-400">{bio.length}/500</span>
        </div>
        <textarea
          id="bio"
          maxLength={500}
          rows={3}
          value={bio}
          onChange={(e) => setBio(e.target.value)}
          disabled={mutation.isPending}
          placeholder="Tell the community about yourself…"
          className="w-full resize-none rounded-lg border border-[#EAE7DF] bg-white px-3.5 py-2.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
        />
      </div>

      {/* City */}
      <div className="space-y-1.5">
        <label
          htmlFor="city"
          className="block text-sm font-medium text-[#111111]"
        >
          City
        </label>
        <input
          id="city"
          type="text"
          maxLength={100}
          value={city}
          onChange={(e) => setCity(e.target.value)}
          disabled={mutation.isPending}
          placeholder="e.g. Amsterdam"
          className="w-full rounded-lg border border-[#EAE7DF] bg-white px-3.5 py-2.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
        />
      </div>

      {/* Country */}
      <div className="space-y-1.5">
        <label
          htmlFor="country"
          className="block text-sm font-medium text-[#111111]"
        >
          Country
        </label>
        <input
          id="country"
          type="text"
          maxLength={100}
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          disabled={mutation.isPending}
          placeholder="e.g. Netherlands"
          className="w-full rounded-lg border border-[#EAE7DF] bg-white px-3.5 py-2.5 text-sm text-[#111111] placeholder:text-gray-400 outline-none transition focus:border-[#111111] focus:ring-2 focus:ring-[#111111]/10 disabled:opacity-50"
        />
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
            "Save changes"
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

export default function EditProfilePage() {
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

      <h1 className="text-xl font-bold text-[#111111]">Edit profile</h1>

      {profileLoading || !profile ? (
        <div className="flex justify-center py-16">
          <Loader2 className="size-6 animate-spin text-gray-400" aria-hidden />
        </div>
      ) : (
        // key=profile.id ensures the form re-initialises if data changes
        <EditForm key={profile.id} profile={profile} />
      )}
    </div>
  );
}
