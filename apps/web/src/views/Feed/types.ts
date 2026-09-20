/**
 * Feed View — Normalized response types
 *
 * The Axios interceptor in axios.ts automatically converts all snake_case
 * response keys to camelCase. These types reflect the data as it arrives
 * in the frontend — camelCase throughout.
 *
 * Backend field → Frontend field:
 *   author_id        → authorId
 *   community_id     → communityId
 *   cover_image_url  → coverImageUrl
 *   tag_list         → tagList
 *   like_count       → likeCount
 *   comment_count    → commentCount
 *   share_count      → shareCount
 *   is_liked         → isLiked
 *   is_bookmarked    → isBookmarked
 *   created_at       → createdAt
 *   updated_at       → updatedAt
 *   media_url        → mediaUrl
 *   object_key       → objectKey
 *   display_order    → displayOrder
 *   alt_text         → altText
 *   media_type       → mediaType
 */

// Normalized shape for a single media item inside a post (PostMediaSchema after camelCase transform)
export interface RawPostMedia {
  id: string;
  postId: string;
  mediaUrl: string;
  objectKey: string;
  mediaType: string;
  displayOrder: number;
  altText: string | null;
  createdAt: string;
  updatedAt: string;
}

// Normalized shape from GET /feed/stories (PostSummarySchema after camelCase transform)
export interface RawPost {
  id: string;
  authorId: string;
  communityId: string | null;
  title: string;
  location: string | null;
  status: string;
  visibility: string;
  /** Cover image — first media item URL, or null (from PostSummarySchema) */
  coverImageUrl: string | null;
  /**
   * Full media array — present when the post has been fetched via PostSchema
   * (GET /feed/posts/{id}) or optimistically merged after upload.
   * Empty array when only a summary is available.
   */
  media: RawPostMedia[];
  tagList: string[];
  likeCount: number;
  commentCount: number;
  shareCount: number;
  isLiked: boolean;
  isBookmarked: boolean;
  createdAt: string;
  updatedAt: string;
}

// Normalized shape from GET /feed/stories (PostListResponse after camelCase transform)
export interface RawPostListResponse {
  posts: RawPost[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

// Normalized shape from GET /feed/posts/{id}/comments (CommentSchema after camelCase transform)
export interface RawComment {
  id: string;
  postId: string;
  authorId: string;
  parentCommentId: string | null;
  content: string;
  isDeleted: boolean;
  replies: RawComment[];
  createdAt: string;
  updatedAt: string;
}

// Normalized shape from GET /feed/posts/{id}/comments (CommentListResponse after camelCase transform)
export interface RawCommentListResponse {
  comments: RawComment[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

// Normalized like action response (LikeActionResponse after camelCase transform)
export interface NormalizedLikeResponse {
  postId: string;
  isLiked: boolean;
  likeCount: number;
}

// Normalized bookmark action response (BookmarkActionResponse after camelCase transform)
export interface NormalizedBookmarkResponse {
  postId: string;
  isBookmarked: boolean;
}
