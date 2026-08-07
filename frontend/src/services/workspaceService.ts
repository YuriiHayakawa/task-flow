import httpClient from "@/services/httpClient";
import type { PaginatedResponse } from "@/types/common";
import type {
  TransferOwnershipRequest,
  Workspace,
  WorkspaceCreate,
  WorkspaceMember,
  WorkspaceMemberCreate,
  WorkspaceMemberRoleUpdate,
  WorkspaceUpdate,
} from "@/types/workspace";

export function list(): Promise<PaginatedResponse<Workspace>> {
  return httpClient
    .get<PaginatedResponse<Workspace>>("/workspaces")
    .then((response) => response.data);
}

export function get(workspaceId: string): Promise<Workspace> {
  return httpClient.get<Workspace>(`/workspaces/${workspaceId}`).then((response) => response.data);
}

export function create(payload: WorkspaceCreate): Promise<Workspace> {
  return httpClient.post<Workspace>("/workspaces", payload).then((response) => response.data);
}

export function update(workspaceId: string, payload: WorkspaceUpdate): Promise<Workspace> {
  return httpClient
    .patch<Workspace>(`/workspaces/${workspaceId}`, payload)
    .then((response) => response.data);
}

export function remove(workspaceId: string): Promise<void> {
  return httpClient.delete(`/workspaces/${workspaceId}`).then(() => undefined);
}

export function listMembers(workspaceId: string): Promise<PaginatedResponse<WorkspaceMember>> {
  return httpClient
    .get<PaginatedResponse<WorkspaceMember>>(`/workspaces/${workspaceId}/members`)
    .then((response) => response.data);
}

export function addMember(
  workspaceId: string,
  payload: WorkspaceMemberCreate,
): Promise<WorkspaceMember> {
  return httpClient
    .post<WorkspaceMember>(`/workspaces/${workspaceId}/members`, payload)
    .then((response) => response.data);
}

export function updateMemberRole(
  workspaceId: string,
  userId: string,
  payload: WorkspaceMemberRoleUpdate,
): Promise<WorkspaceMember> {
  return httpClient
    .patch<WorkspaceMember>(`/workspaces/${workspaceId}/members/${userId}/role`, payload)
    .then((response) => response.data);
}

export function removeMember(workspaceId: string, userId: string): Promise<void> {
  return httpClient.delete(`/workspaces/${workspaceId}/members/${userId}`).then(() => undefined);
}

export function transferOwnership(
  workspaceId: string,
  payload: TransferOwnershipRequest,
): Promise<Workspace> {
  return httpClient
    .post<Workspace>(`/workspaces/${workspaceId}/transfer-ownership`, payload)
    .then((response) => response.data);
}
