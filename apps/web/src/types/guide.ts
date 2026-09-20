import type { UUID, ISODateString } from "./primitives";
import type { UserSummary } from "./user";

// ---------------------------------------------------------------------------
// Guide enumerations
// ---------------------------------------------------------------------------

export type VerificationStatus = "PENDING" | "VERIFIED" | "SUSPENDED" | "REVOKED";

export type AvailabilityStatus = "AVAILABLE" | "UNAVAILABLE" | "VACATION" | "BUSY";

export type ApplicationStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "REJECTED";

// ---------------------------------------------------------------------------
// Guide interfaces
// ---------------------------------------------------------------------------

export interface GuideProfile {
  id: UUID;
  userId: UUID;
  /**
   * Human-readable display name from the user record.
   * Populated when user-service integration is available; null until then.
   * Matches backend field display_name (camelCased by axios interceptor).
   */
  displayName?: string | null;
  /** Populated when user-service integration is available; null until then */
  user?: UserSummary | null;
  bio: string | null;
  profileImageUrl: string | null;
  coverImageUrl: string | null;
  yearsExperience: number | null;
  pricePerDay: number | null;
  rating: number | null;
  reviewCount: number;
  verificationStatus: VerificationStatus;
  locations: GuideLocation[];
  languages: GuideLanguage[];
  availability: GuideAvailability | null;
  specializations: GuideSpecialization[];
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

export interface GuideProfileSummary {
  id: UUID;
  userId: UUID;
  /** Populated when user-service integration is available; null until then */
  displayName: string | null;
  profileImageUrl: string | null;
  rating: number | null;
  reviewCount: number;
  verificationStatus: VerificationStatus;
  yearsExperience: number | null;
  pricePerDay: number | null;
  bio: string | null;
  locations: GuideLocation[];
  languages: GuideLanguage[];
  availability: GuideAvailability | null;
  specializations: GuideSpecialization[];
}

export interface GuideLocation {
  id: UUID;
  guideId: UUID;
  country: string;
  region: string | null;
  city: string | null;
}

export interface GuideLanguage {
  id: UUID;
  guideId: UUID;
  language: string;
}

export interface GuideSpecialization {
  id: UUID;
  guideId: UUID;
  category: string;
}

export interface GuideAvailability {
  guideId: UUID;
  status: AvailabilityStatus;
  note: string | null;
}

export interface GuideReview {
  id: UUID;
  guideId: UUID;
  reviewerId: UUID;
  /**
   * Populated only when user-service integration is available.
   * The guide-service currently returns reviewer_id only — no nested user object.
   * Code must treat this as optional and fall back to reviewer_id.
   */
  reviewer?: UserSummary | null;
  expeditionId: UUID | null;
  ratingOverall: number;
  ratingKnowledge: number;
  ratingFriendliness: number;
  ratingCommunication: number;
  ratingSafety: number;
  ratingProfessionalism: number;
  wouldRecommend: boolean;
  comment: string | null;
  createdAt: ISODateString;
  updatedAt?: ISODateString;
}

/**
 * Paginated list response for guide reviews.
 * Matches the backend GuideReviewListResponse schema:
 * { guide_id, items, pagination }
 *
 * Structurally compatible with PaginatedResponse<GuideReview> — same
 * .items and .pagination fields — so existing `data?.items ?? []`
 * patterns work without change.
 */
export interface GuideReviewListResponse {
  guideId: UUID;
  items: GuideReview[];
  pagination: import("./apiTypes").PaginationMeta;
}

export interface GuideRatingSummary {
  guideId: UUID;
  averageOverall: number | null;
  averageKnowledge: number | null;
  averageFriendliness: number | null;
  averageCommunication: number | null;
  averageSafety: number | null;
  averageProfessionalism: number | null;
  wouldRecommendPercentage: number | null;
  /** Backend field: review_count → camelCase: reviewCount */
  reviewCount: number;
}

export interface TravelConnection {
  id: UUID;
  guideId: UUID;
  guide: GuideProfileSummary;
  travelerId: UUID;
  firstMet: ISODateString;
  lastInteraction: ISODateString | null;
  expeditionsTogether: number;
  conversationCount: number;
  photosShared: number;
  bookmarked: boolean;
}

/** Backend response shape for a single connection (guide object NOT included) */
export interface TravelConnectionRecord {
  id: UUID;
  guideId: UUID;
  travelerId: UUID;
  firstMet: ISODateString | null;
  lastInteraction: ISODateString | null;
  expeditionsTogether: number;
  conversationCount: number;
  photosShared: number;
  bookmarked: boolean;
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

export interface TravelConnectionListResponse {
  travelerId: UUID;
  connections: TravelConnectionRecord[];
  pagination: import("./apiTypes").PaginationMeta;
}

// ---------------------------------------------------------------------------
// Guide application
// ---------------------------------------------------------------------------

export interface GuideApplicationCreate {
  biography: string;
  areas_covered?: string;
  languages?: string;
  experience_years?: number;
  certifications?: string;
  identity_document_url?: string;
}

export interface GuideApplicationResponse {
  id: UUID;
  userId: UUID;
  biography: string | null;
  areasCovered: string | null;
  languages: string | null;
  experienceYears: number | null;
  certifications: string | null;
  identityDocumentUrl: string | null;
  status: ApplicationStatus;
  submittedAt: ISODateString | null;
  reviewedAt: ISODateString | null;
  reviewedBy: UUID | null;
  reviewNotes: string | null;
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

// ---------------------------------------------------------------------------
// Filter parameter types (mirrored from backend query schemas)
// ---------------------------------------------------------------------------

/** Query filters for the guide directory endpoint */
export interface GuideFilter {
  country?: string;
  language?: string;
  specialization?: string;
  availability?: AvailabilityStatus;
  verification_status?: VerificationStatus;
  page?: number;
  page_size?: number;
}
