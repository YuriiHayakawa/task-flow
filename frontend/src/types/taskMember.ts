export interface TaskMember {
  user_id: string;
  name: string;
  email: string;
  added_at: string | null;
}

export interface TaskMemberCreate {
  user_id: string;
}
