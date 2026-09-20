import type { UUID, ISODateString } from "./primitives";

// ---------------------------------------------------------------------------
// User & identity
// ---------------------------------------------------------------------------

export interface UserProfile {
  id: UUID;
  username: string;
  displayName: string;
  bio: string | null;
  avatarUrl: string | null;
  coverImageUrl: string | null;
  /** Countries or regions visited */
  countriesVisited: number;
  /** Total expeditions participated in */
  expeditionsCount: number;
  /** Number of followers */
  followersCount: number;
  /** Number of accounts the user follows */
  followingCount: number;
  /** Whether the current authenticated user follows this profile */
  isFollowing: boolean;
  createdAt: ISODateString;
}

/** Minimal user reference used inside nested objects (e.g., post author) */
export interface UserSummary {
  id: UUID;
  username: string;
  displayName: string;
  avatarUrl: string | null;
}

/** Authenticated session data stored in AppState */
export interface AuthUser extends UserSummary {
  email: string;
  /** JWT access token — never expose in UI */
  accessToken: string;
}
