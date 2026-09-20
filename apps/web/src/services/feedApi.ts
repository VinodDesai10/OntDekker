/**
 * OntDekker Feed API Functions
 *
 * All API calls for the Feed Service (Developer 2 scope).
 * Follows the same pattern as guideApi.ts and expeditionApi.ts.
 *
 * Endpoint mapping:
 *   Feed : /feed/api/v1/feed/*
 *
 * All paths are relative to the Traefik gateway base URL configured
 * in axios.ts (NEXT_PUBLIC_API_BASE_URL).
 */

import apiClient from "./axios";
import type {
  PaginatedResponse,
  Post,
  PostSummary,
  PostMedia,
  Comment,
  Share,
  CreatePostRequest,
  UpdatePostRequest,
  CreateCommentRequest,
  UpdateCommentRequest,
  FeedFilter,
  MediaUploadRequest,
  MediaUploadResponse,
  RegisterMediaRequest,
} from "@/types";
import type { RawPostListResponse } from "@/views/Feed/types";

// ---------------------------------------------------------------------------
// Posts (Travel Stories)
// ---------------------------------------------------------------------------

/** Fetch paginated feed posts (latest / community / user stories) */
export async function getFeedPosts(
  filters: Partial<FeedFilter> = {},
): Promise<PaginatedResponse<PostSummary>> {
  const { data } = await apiClient.get("/feed/api/v1/feed/stories", {
    params: filters,
  });
  return data;
}

/** Fetch a single post's full detail */
export async function getPostById(postId: string): Promise<Post> {
  const { data } = await apiClient.get(`/feed/api/v1/feed/stories/${postId}`);
  return data;
}

/** Fetch posts authored by a specific user */
export async function getPostsByUser(
  userId: string,
  params: { page?: number; page_size?: number } = {},
): Promise<PaginatedResponse<PostSummary>> {
  const { data } = await apiClient.get(
    `/feed/api/v1/feed/users/${userId}`,
    { params },
  );
  return data;
}

/**
 * Fetch the currently authenticated user's own posts.
 *
 * Author identity is derived from the JWT on the server — the caller never
 * supplies an author_id.  Returns all PUBLISHED posts (Global + Community)
 * created by the current user for display on their Profile.
 */
export async function getMyPosts(
  params: { limit?: number; offset?: number } = {},
): Promise<RawPostListResponse> {
  const { data } = await apiClient.get("/feed/api/v1/feed/me/posts", { params });
  return data;
}

/** Fetch posts belonging to a specific community */
export async function getPostsByCommunity(
  communityId: string,
  params: { page?: number; page_size?: number } = {},
): Promise<PaginatedResponse<PostSummary>> {
  const { data } = await apiClient.get(
    `/feed/api/v1/feed/communities/${communityId}`,
    { params },
  );
  return data;
}

/** Create a new travel story post */
export async function createPost(payload: CreatePostRequest): Promise<Post> {
  // Backend expects snake_case keys; translate from TS camelCase
  const backendPayload = {
    title: payload.title,
    content: payload.content,
    location: payload.location,
    community_id: payload.communityId,
    expedition_id: payload.expeditionId,
    tags: payload.tags,
    visibility: payload.visibility,
    media_keys: payload.mediaKeys,
  };
  const { data } = await apiClient.post("/feed/api/v1/feed/stories", backendPayload);
  return data;
}

/** Update an existing post */
export async function updatePost(
  postId: string,
  payload: UpdatePostRequest,
): Promise<Post> {
  // Backend expects snake_case keys; translate from TS camelCase
  const backendPayload = {
    title: payload.title,
    content: payload.content,
    location: payload.location,
    visibility: payload.visibility,
    tags: payload.tags,
  };
  const { data } = await apiClient.put(
    `/feed/api/v1/feed/stories/${postId}`,
    backendPayload,
  );
  return data;
}

/** Delete (soft-delete) a post */
export async function deletePost(postId: string): Promise<void> {
  await apiClient.delete(`/feed/api/v1/feed/stories/${postId}`);
}

// ---------------------------------------------------------------------------
// Post media
// ---------------------------------------------------------------------------

/**
 * Step 1 — Request a presigned PUT URL for uploading a single image.
 *
 * POST /feed/api/v1/feed/posts/{postId}/media/upload-url
 * Body: { filename, content_type }
 * Returns: { upload_url, object_key, expires_in }  (camelCased by interceptor)
 */
export async function generateMediaUploadUrl(
  postId: string,
  payload: MediaUploadRequest,
): Promise<MediaUploadResponse> {
  const { data } = await apiClient.post(
    `/feed/api/v1/feed/posts/${postId}/media/upload-url`,
    payload,
  );
  return data;
}

/**
 * Step 2 — Upload the binary file directly to MinIO via the presigned URL.
 *
 * This is a plain HTTP PUT — NOT through the API client — because:
 *  - The URL is a direct MinIO presigned URL, not the Traefik gateway.
 *  - We must not send the Authorization header (MinIO presigned URLs are
 *    self-authenticating via query-string parameters).
 *  - We must set Content-Type to match what was declared in step 1.
 */
export async function uploadFileToMinIO(
  presignedUrl: string,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", presignedUrl, true);
    // MinIO presigned PUT requires the Content-Type to match what was
    // declared when generating the URL.
    xhr.setRequestHeader("Content-Type", file.type);

    if (onProgress) {
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      });
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new Error(`MinIO upload failed with status ${xhr.status}`));
      }
    };
    xhr.onerror = () => reject(new Error("MinIO upload network error"));
    xhr.send(file);
  });
}

/**
 * Step 3 — Register the uploaded object with the post in the database.
 *
 * POST /feed/api/v1/feed/posts/{postId}/media
 * Body: { object_key, display_order, alt_text }
 * Returns: PostMediaSchema
 */
export async function registerPostMedia(
  postId: string,
  payload: RegisterMediaRequest,
): Promise<PostMedia> {
  const { data } = await apiClient.post(
    `/feed/api/v1/feed/posts/${postId}/media`,
    payload,
  );
  return data;
}

/** Fetch media items for a specific post */
export async function getPostMedia(postId: string): Promise<PostMedia[]> {
  const { data } = await apiClient.get(
    `/feed/api/v1/feed/posts/${postId}/media`,
  );
  return data;
}

// ---------------------------------------------------------------------------
// Likes
// ---------------------------------------------------------------------------

// Camelcase shape after axios interceptor transforms snake_case response
export interface LikeActionResponse {
  postId: string;
  isLiked: boolean;
  likeCount: number;
}

export interface BookmarkActionResponse {
  postId: string;
  isBookmarked: boolean;
}

/** Like a post — returns updated like state */
export async function likePost(postId: string): Promise<LikeActionResponse> {
  const { data } = await apiClient.post(
    `/feed/api/v1/feed/posts/${postId}/like`,
  );
  return data;
}

/** Unlike a post — returns updated like state */
export async function unlikePost(postId: string): Promise<LikeActionResponse> {
  const { data } = await apiClient.delete(
    `/feed/api/v1/feed/posts/${postId}/like`,
  );
  return data;
}

// ---------------------------------------------------------------------------
// Bookmarks
// ---------------------------------------------------------------------------

/** Bookmark a post */
export async function bookmarkPost(
  postId: string,
): Promise<BookmarkActionResponse> {
  const { data } = await apiClient.post(
    `/feed/api/v1/feed/posts/${postId}/bookmark`,
  );
  return data;
}

/** Remove a post bookmark */
export async function unbookmarkPost(
  postId: string,
): Promise<BookmarkActionResponse> {
  const { data } = await apiClient.delete(
    `/feed/api/v1/feed/posts/${postId}/bookmark`,
  );
  return data;
}

// ---------------------------------------------------------------------------
// Shares
// ---------------------------------------------------------------------------

/** Share a post — increments share counter and returns a share link */
export async function sharePost(postId: string): Promise<Share> {
  const { data } = await apiClient.post(
    `/feed/api/v1/feed/stories/${postId}/share`,
  );
  return data;
}

// ---------------------------------------------------------------------------
// Comments
// ---------------------------------------------------------------------------

/** Fetch paginated comments for a post */
export async function getComments(
  postId: string,
  params: { page?: number; page_size?: number } = {},
): Promise<PaginatedResponse<Comment>> {
  const { data } = await apiClient.get(
    `/feed/api/v1/feed/posts/${postId}/comments`,
    { params },
  );
  return data;
}

/** Create a top-level comment or a nested reply on a post */
export async function createComment(
  postId: string,
  payload: CreateCommentRequest,
): Promise<Comment> {
  const { data } = await apiClient.post(
    `/feed/api/v1/feed/posts/${postId}/comments`,
    payload,
  );
  return data;
}

/** Reply to an existing comment */
export async function replyToComment(
  commentId: string,
  payload: CreateCommentRequest,
): Promise<Comment> {
  const { data } = await apiClient.post(
    `/feed/api/v1/feed/comments/${commentId}/reply`,
    payload,
  );
  return data;
}

/** Update a comment */
export async function updateComment(
  commentId: string,
  payload: UpdateCommentRequest,
): Promise<Comment> {
  const { data } = await apiClient.put(
    `/feed/api/v1/feed/comments/${commentId}`,
    payload,
  );
  return data;
}

/** Delete a comment */
export async function deleteComment(commentId: string): Promise<void> {
  await apiClient.delete(`/feed/api/v1/feed/comments/${commentId}`);
}

/** Like a comment */
export async function likeComment(commentId: string): Promise<void> {
  await apiClient.post(`/feed/api/v1/feed/comments/${commentId}/like`);
}

/** Unlike a comment */
export async function unlikeComment(commentId: string): Promise<void> {
  await apiClient.delete(`/feed/api/v1/feed/comments/${commentId}/like`);
}
