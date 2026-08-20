import httpClient from "@/services/httpClient";
import type { ChecklistItem, ChecklistItemCreate, ChecklistItemUpdate } from "@/types/checklistItem";

/** Sem envelope de paginação (contracts/collaboration.md: "lista de
 * ChecklistItemRead", volume esperado baixo por tarefa) — mesmo padrão de
 * `taskMemberService`. */
export function list(taskId: string): Promise<ChecklistItem[]> {
  return httpClient.get<ChecklistItem[]>(`/tasks/${taskId}/checklist`).then((response) => response.data);
}

export function create(taskId: string, payload: ChecklistItemCreate): Promise<ChecklistItem> {
  return httpClient
    .post<ChecklistItem>(`/tasks/${taskId}/checklist`, payload)
    .then((response) => response.data);
}

export function update(
  taskId: string,
  itemId: string,
  payload: ChecklistItemUpdate,
): Promise<ChecklistItem> {
  return httpClient
    .patch<ChecklistItem>(`/tasks/${taskId}/checklist/${itemId}`, payload)
    .then((response) => response.data);
}

export function remove(taskId: string, itemId: string): Promise<void> {
  return httpClient.delete(`/tasks/${taskId}/checklist/${itemId}`).then(() => undefined);
}
