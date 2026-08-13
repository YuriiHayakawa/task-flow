import httpClient from "@/services/httpClient";
import type { TaskMember, TaskMemberCreate } from "@/types/taskMember";

/** Sem envelope de paginação (ao contrário de workspace members) — o
 * contrato retorna a lista de participantes direta (contracts/
 * projects-and-tasks.md). */
export function list(taskId: string): Promise<TaskMember[]> {
  return httpClient.get<TaskMember[]>(`/tasks/${taskId}/members`).then((response) => response.data);
}

export function add(taskId: string, payload: TaskMemberCreate): Promise<TaskMember> {
  return httpClient
    .post<TaskMember>(`/tasks/${taskId}/members`, payload)
    .then((response) => response.data);
}

export function remove(taskId: string, userId: string): Promise<void> {
  return httpClient.delete(`/tasks/${taskId}/members/${userId}`).then(() => undefined);
}
