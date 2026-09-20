import type { UUID, ISODateString } from "./primitives";
import type { UserSummary } from "./user";

// ---------------------------------------------------------------------------
// Expedition enumerations
// ---------------------------------------------------------------------------

export type ExpeditionStatus =
  | "DRAFT"
  | "PUBLISHED"
  | "ACTIVE"
  | "COMPLETED"
  | "CANCELLED"
  | "ARCHIVED";

export type ExpeditionVisibility = "PUBLIC" | "PRIVATE";

export type ParticipantRole = "ORGANIZER" | "CO_ORGANIZER" | "PARTICIPANT";

export type ParticipantStatus = "ACTIVE" | "LEFT" | "REMOVED";

export type JoinRequestStatus = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";

export type GearCategory = "BASE_PACK" | "CONSUMABLES" | "WORN_GEAR";

export type PackWeightClassification =
  | "ULTRALIGHT"
  | "LIGHTWEIGHT"
  | "STANDARD"
  | "HEAVY";

// ---------------------------------------------------------------------------
// Expedition interfaces
// ---------------------------------------------------------------------------

export interface Expedition {
  id: UUID;
  communityId: UUID;
  organizerId: UUID;
  /** Populated when user-service integration is available; absent until then */
  organizer?: UserSummary | null;
  title: string;
  destination: string;
  description: string | null;
  meetingPoint: string | null;
  startDate: string | null; // ISO date "YYYY-MM-DD"
  endDate: string | null;
  maxParticipants: number;
  /** Populated when participant data is available; absent until then */
  currentParticipantsCount?: number;
  budget: number | null;
  visibility: ExpeditionVisibility;
  status: ExpeditionStatus;
  coverImageUrl: string | null;
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

export interface ExpeditionSummary {
  id: UUID;
  communityId: UUID;
  organizerId: UUID;
  title: string;
  destination: string;
  startDate: string | null;
  endDate: string | null;
  status: ExpeditionStatus;
  visibility: ExpeditionVisibility;
  coverImageUrl: string | null;
  budget: number | null;
  maxParticipants: number;
  /** Not present in current backend; populated when user-service integration is available */
  organizerName?: string | null;
  /** Not present in current backend; populated when participant data is available */
  currentParticipantsCount?: number;
}

export interface ExpeditionParticipant {
  expeditionId: UUID;
  userId: UUID;
  user: UserSummary;
  role: ParticipantRole;
  status: ParticipantStatus;
  joinedAt: ISODateString;
}

export interface ExpeditionItineraryDay {
  expeditionId: UUID;
  dayNumber: number;
  title: string;
  description: string;
  location: string;
  activityTime: string | null; // "HH:MM:SS"
}

export interface GearItem {
  id: UUID;
  expeditionId: UUID;
  name: string;
  category: GearCategory;
  weightGrams: number;
  quantity: number;
  isPacked: boolean;
  addedBy: UUID;
}

export interface PackWeightSummary {
  totalWeightGrams: number;
  basePackGrams: number;
  consumablesGrams: number;
  wornGearGrams: number;
  packedItemsCount: number;
  totalItemsCount: number;
  classification: PackWeightClassification;
}

export interface GalleryPhoto {
  id: UUID;
  expeditionId: UUID;
  imageUrl: string;
  caption: string | null;
  displayOrder: number;
  uploadedBy: UUID;
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

export interface ExpeditionReview {
  id: UUID;
  expeditionId: UUID;
  reviewerId: UUID;
  reviewer: UserSummary;
  revieweeId: UUID;
  reviewee: UserSummary;
  ratingOverall: number;
  ratingKnowledge: number;
  ratingFriendliness: number;
  ratingCommunication: number;
  ratingSafety: number;
  ratingProfessionalism: number;
  comment: string | null;
  wouldTravelAgain: boolean;
  createdAt: ISODateString;
}
