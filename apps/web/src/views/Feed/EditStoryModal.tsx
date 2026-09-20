"use client";

/**
 * EditStoryModal — Edit an existing story (owner only)
 *
 * NOTE: RawPost fields are camelCase (post axios camelCase transform).
 */

import React, { useState } from "react";
import { X } from "lucide-react";
import type { RawPost } from "./types";
import type { UpdatePostRequest } from "@/types";

interface EditStoryModalProps {
  post: RawPost;
  onSave: (payload: UpdatePostRequest) => Promise<void>;
  onClose: () => void;
}

export function EditStoryModal({ post, onSave, onClose }: EditStoryModalProps) {
  const [title, setTitle] = useState(post.title);
  const [location, setLocation] = useState(post.location ?? "");
  const [visibility, setVisibility] = useState<"PUBLIC" | "PRIVATE" | "COMMUNITY">(
    (post.visibility as "PUBLIC" | "PRIVATE" | "COMMUNITY") ?? "PUBLIC"
  );
  const [saving, setSaving] = useState(false);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      await onSave({
        title: title.trim(),
        location: location.trim() || null,
        visibility,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-md rounded-2xl bg-white border border-[#EAE7DF] p-6 shadow-xl space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-[#111111]">Edit Story</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-[#111111] transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-600">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-xl border border-[#EAE7DF] px-3.5 py-2 text-sm text-[#111111] placeholder:text-gray-400 outline-none focus:border-[#111111]"
              placeholder="Story title"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-600">Location</label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full rounded-xl border border-[#EAE7DF] px-3.5 py-2 text-sm text-[#111111] placeholder:text-gray-400 outline-none focus:border-[#111111]"
              placeholder="e.g. Chamonix, France"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-600">Visibility</label>
            <select
              value={visibility}
              onChange={(e) =>
                setVisibility(e.target.value as "PUBLIC" | "PRIVATE" | "COMMUNITY")
              }
              className="w-full rounded-xl border border-[#EAE7DF] bg-white px-3.5 py-2 text-sm text-gray-700 outline-none"
            >
              <option value="PUBLIC">Public</option>
              <option value="PRIVATE">Private</option>
              <option value="COMMUNITY">Community Only</option>
            </select>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-gray-500 hover:text-[#111111]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !title.trim()}
              className="rounded-xl bg-[#111111] px-4 py-2 text-xs font-semibold text-white hover:bg-[#333333] transition-colors disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
