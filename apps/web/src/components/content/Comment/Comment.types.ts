export interface CommentProps {
  id: string;
  author: { id: string; displayName: string; avatarUrl: string | null; username: string };
  body: string;
  likesCount: number;
  isLiked: boolean;
  createdAt: string;
  onLike?: (id: string, liked: boolean) => void;
  onReply?: (id: string) => void;
  isReply?: boolean;
}
