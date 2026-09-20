"use client";

/**
 * DeleteConfirmModal — Confirm story deletion (owner only)
 */

import React, { useState } from "react";
import { Trash2, X } from "lucide-react";

interface DeleteConfirmModalProps {
  postTitle: string;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}

export function DeleteConfirmModal({
  postTitle,
  onConfirm,
  onClose,
}: DeleteConfirmModalProps) {
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    setDeleting(true);
    try {
      await onConfirm();
      onClose();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-sm rounded-2xl bg-white border border-[#EAE7DF] p-6 shadow-xl space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-[#111111]">Delete Story</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-[#111111] transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        <div className="space-y-2">
          <p className="text-sm text-gray-700">
            Are you sure you want to delete{" "}
            <span className="font-semibold text-[#111111]">
              &ldquo;{postTitle}&rdquo;
            </span>
            ?
          </p>
          <p className="text-xs text-gray-500">This action cannot be undone.</p>
        </div>

        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-gray-500 hover:text-[#111111]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="inline-flex items-center gap-1.5 rounded-xl bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-50"
          >
            <Trash2 size={13} />
            {deleting ? "Deleting..." : "Delete Story"}
          </button>
        </div>
      </div>
    </div>
  );
}
