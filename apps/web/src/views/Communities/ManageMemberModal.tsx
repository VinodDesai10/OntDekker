"use client";

/**
 * OntDekker — ManageMemberModal
 *
 * Modal for role management actions on a community member.
 * CP-2.5: Shows real profile data (avatar, display name, username).
 * CP-2.5: Remove member requires a confirmation Dialog.
 *
 * OWNER (Head) actions:
 *   - Promote MEMBER → MODERATOR (Co-Head)
 *   - Demote MODERATOR → MEMBER
 *   - Remove member (with Dialog confirmation)
 *
 * MODERATOR (Co-Head) actions:
 *   - Remove MEMBER only (with Dialog confirmation)
 */

import { useState } from "react";
import { ShieldCheck, ShieldOff, Trash2 } from "lucide-react";
import Modal from "@/components/overlays/Modal";
import Dialog from "@/components/overlays/Dialog";
import Button from "@/components/feedback/Button";
import type { CommunityMember, MemberRole } from "@/types";
import type { ProfileMap } from "@/services/users";

interface ManageMemberModalProps {
  isOpen: boolean;
  onClose: () => void;
  member: CommunityMember | null;
  currentUserRole: MemberRole | null;
  profiles: ProfileMap;
  onPromote: (member: CommunityMember) => Promise<void>;
  onDemote: (member: CommunityMember) => Promise<void>;
  onRemove: (member: CommunityMember) => Promise<void>;
}

function shortId(id: string): string {
  if (id.length <= 12) return id;
  return `${id.slice(0, 6)}…${id.slice(-4)}`;
}

export default function ManageMemberModal({
  isOpen,
  onClose,
  member,
  currentUserRole,
  profiles,
  onPromote,
  onDemote,
  onRemove,
}: ManageMemberModalProps) {
  const [busy, setBusy] = useState<"promote" | "demote" | "remove" | null>(null);
  const [showRemoveDialog, setShowRemoveDialog] = useState(false);

  if (!member) return null;

  const isOwner = currentUserRole === "OWNER";
  const isMod = currentUserRole === "MODERATOR";

  const canPromote = isOwner && member.role === "MEMBER";
  const canDemote = isOwner && member.role === "MODERATOR";
  const canRemove =
    (isOwner && member.role !== "OWNER") ||
    (isMod && member.role === "MEMBER");

  // Profile data
  const profile = profiles[member.userId];
  const displayName = profile?.displayName ?? shortId(member.userId);
  const username = profile?.username ? `@${profile.username}` : null;
  const avatarSrc = profile?.avatarUrl ?? null;
  const initials = (profile?.displayName ?? member.userId)
    .slice(0, 2)
    .toUpperCase();

  async function handle(
    action: "promote" | "demote",
    fn: () => Promise<void>,
  ) {
    setBusy(action);
    try {
      await fn();
      onClose();
    } catch {
      // errors surfaced by parent
    } finally {
      setBusy(null);
    }
  }

  async function handleConfirmRemove() {
    setBusy("remove");
    try {
      await onRemove(member!);
      setShowRemoveDialog(false);
      onClose();
    } catch {
      // errors surfaced by parent
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title="Manage Member"
        size="sm"
      >
        <div className="space-y-4">
          {/* Member identity */}
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-2xl">
            <div className="flex-shrink-0">
              {avatarSrc ? (
                <img
                  src={avatarSrc}
                  alt={displayName}
                  className="w-10 h-10 rounded-full object-cover"
                />
              ) : (
                <div
                  className="
                    w-10 h-10 rounded-full flex-shrink-0
                    bg-gradient-to-br from-gray-200 to-gray-300
                    flex items-center justify-center
                    text-gray-600 text-xs font-semibold
                  "
                  aria-hidden="true"
                >
                  {initials}
                </div>
              )}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-[#111111] truncate">
                {displayName}
              </p>
              {username && (
                <p className="text-xs text-gray-500 font-mono">{username}</p>
              )}
              {!username && (
                <p className="text-xs text-gray-500">
                  {member.role === "OWNER"
                    ? "Head"
                    : member.role === "MODERATOR"
                      ? "Co-Head"
                      : "Member"}
                </p>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-2">
            {canPromote && (
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => handle("promote", () => onPromote(member!))}
                className="
                  w-full flex items-center gap-3 px-4 py-3 rounded-2xl
                  bg-white border border-gray-100 hover:bg-gray-50
                  text-sm font-medium text-[#111111]
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-colors
                "
              >
                <ShieldCheck size={16} className="text-blue-500 flex-shrink-0" aria-hidden="true" />
                <div className="text-left">
                  <div>Promote to Co-Head</div>
                  <div className="text-xs text-gray-500 font-normal">
                    Grants join-request and member management permissions
                  </div>
                </div>
              </button>
            )}

            {canDemote && (
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => handle("demote", () => onDemote(member!))}
                className="
                  w-full flex items-center gap-3 px-4 py-3 rounded-2xl
                  bg-white border border-gray-100 hover:bg-gray-50
                  text-sm font-medium text-[#111111]
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-colors
                "
              >
                <ShieldOff size={16} className="text-amber-500 flex-shrink-0" aria-hidden="true" />
                <div className="text-left">
                  <div>Demote to Member</div>
                  <div className="text-xs text-gray-500 font-normal">
                    Removes moderation permissions
                  </div>
                </div>
              </button>
            )}

            {canRemove && (
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => setShowRemoveDialog(true)}
                className="
                  w-full flex items-center gap-3 px-4 py-3 rounded-2xl
                  bg-white border border-red-100 hover:bg-red-50
                  text-sm font-medium text-red-600
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-colors
                "
              >
                <Trash2 size={16} className="flex-shrink-0" aria-hidden="true" />
                <div className="text-left">
                  <div>Remove from community</div>
                  <div className="text-xs text-red-400 font-normal">
                    Member will need to re-join
                  </div>
                </div>
              </button>
            )}
          </div>

          {!canPromote && !canDemote && !canRemove && (
            <p className="text-sm text-gray-500 text-center py-2">
              No actions available for this member.
            </p>
          )}

          <Button variant="outline" size="sm" onClick={onClose} className="w-full">
            Cancel
          </Button>
        </div>
      </Modal>

      {/* Remove confirmation dialog */}
      <Dialog
        isOpen={showRemoveDialog}
        title="Remove Member"
        message={`Remove ${displayName} from this community? They will need to re-join.`}
        confirmLabel="Remove"
        cancelLabel="Cancel"
        destructive
        loading={busy === "remove"}
        onConfirm={handleConfirmRemove}
        onCancel={() => setShowRemoveDialog(false)}
      />
    </>
  );
}
