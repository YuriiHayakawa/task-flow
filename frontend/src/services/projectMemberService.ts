import httpClient from "@/services/httpClient";
import type { PaginatedResponse } from "@/types/common";
import type { ProjectMember, ProjectMemberCreate } from "@/types/projectMember";

export function list(projectId: string): Promise<PaginatedResponse<ProjectMember>> {
  return httpClient
    .get<PaginatedResponse<ProjectMember>>(`/projects/${projectId}/members`)
    .then((response) => response.data);
}

export function add(projectId: string, payload: ProjectMemberCreate): Promise<ProjectMember> {
  return httpClient
    .post<ProjectMember>(`/projects/${projectId}/members`, payload)
    .then((response) => response.data);
}

export function remove(projectId: string, userId: string): Promise<void> {
  return httpClient.delete(`/projects/${projectId}/members/${userId}`).then(() => undefined);
}
