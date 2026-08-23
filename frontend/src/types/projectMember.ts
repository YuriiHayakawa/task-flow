export interface ProjectMember {
  user_id: string;
  name: string;
  email: string;
  joined_at: string;
}

export interface ProjectMemberCreate {
  user_id: string;
}
