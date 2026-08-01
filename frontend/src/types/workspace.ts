export type WorkspaceRole = "OWNER" | "ADMIN" | "MEMBER";

export interface Workspace {
  id: string;
  name: string;
  description: string | null;
  my_role: WorkspaceRole;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceCreate {
  name: string;
  description?: string | null;
}

export interface WorkspaceUpdate {
  name?: string;
  description?: string | null;
}

export interface WorkspaceMember {
  user_id: string;
  name: string;
  email: string;
  role: WorkspaceRole;
  joined_at: string;
}

export interface WorkspaceMemberCreate {
  user_id: string;
  role?: WorkspaceRole;
}

export interface WorkspaceMemberRoleUpdate {
  role: WorkspaceRole;
}

export interface TransferOwnershipRequest {
  new_owner_user_id: string;
}
