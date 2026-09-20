export type AvatarSize = "xs" | "sm" | "md" | "lg" | "xl";
export type AvatarStatus = "online" | "offline" | "none";

export interface AvatarProps {
  /** Image URL — if null or undefined shows initials fallback */
  src?: string | null;
  /** Alt text (also used to derive initials fallback) */
  alt: string;
  /** Avatar diameter — defaults to "md" */
  size?: AvatarSize;
  /** Presence indicator dot — defaults to "none" */
  status?: AvatarStatus;
  /** Additional Tailwind classes on the root element */
  className?: string;
}
