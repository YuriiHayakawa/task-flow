export interface Comment {
  id: string;
  author_id: string;
  author_name: string;
  author_email: string;
  content: string;
  created_at: string;
}

export interface CommentCreate {
  content: string;
}
