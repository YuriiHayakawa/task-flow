import httpClient from "@/services/httpClient";
import type { PaginatedResponse } from "@/types/common";
import type { Task, TaskCreate, TaskSearchParams, TaskUpdate } from "@/types/task";

export function list(params: TaskSearchParams = {}): Promise<PaginatedResponse<Task>> {
  return httpClient
    .get<PaginatedResponse<Task>>("/tasks", { params })
    .then((response) => response.data);
}

export function create(payload: TaskCreate): Promise<Task> {
  return httpClient.post<Task>("/tasks", payload).then((response) => response.data);
}

export function update(taskId: string, payload: TaskUpdate): Promise<Task> {
  return httpClient.patch<Task>(`/tasks/${taskId}`, payload).then((response) => response.data);
}
