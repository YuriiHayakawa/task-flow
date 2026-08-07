import httpClient from "@/services/httpClient";
import type { PaginatedResponse } from "@/types/common";
import type { Project, ProjectCreate, ProjectUpdate } from "@/types/project";

export function list(workspaceId: string): Promise<PaginatedResponse<Project>> {
  return httpClient
    .get<PaginatedResponse<Project>>(`/workspaces/${workspaceId}/projects`)
    .then((response) => response.data);
}

export function get(projectId: string): Promise<Project> {
  return httpClient.get<Project>(`/projects/${projectId}`).then((response) => response.data);
}

export function create(workspaceId: string, payload: ProjectCreate): Promise<Project> {
  return httpClient
    .post<Project>(`/workspaces/${workspaceId}/projects`, payload)
    .then((response) => response.data);
}

export function update(projectId: string, payload: ProjectUpdate): Promise<Project> {
  return httpClient
    .patch<Project>(`/projects/${projectId}`, payload)
    .then((response) => response.data);
}

export function remove(projectId: string): Promise<void> {
  return httpClient.delete(`/projects/${projectId}`).then(() => undefined);
}
