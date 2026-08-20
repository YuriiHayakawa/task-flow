import httpClient from "@/services/httpClient";
import type {
  RecurringTask,
  RecurringTaskCreate,
  RecurringTaskUpdate,
} from "@/types/recurringTask";

/** Sem envelope de paginação (contracts/recurring-tasks.md: volume esperado
 * baixo por usuário) — mesmo padrão de Checklist/Attachments. */
export function list(): Promise<RecurringTask[]> {
  return httpClient.get<RecurringTask[]>("/recurring-tasks").then((response) => response.data);
}

export function create(payload: RecurringTaskCreate): Promise<RecurringTask> {
  return httpClient
    .post<RecurringTask>("/recurring-tasks", payload)
    .then((response) => response.data);
}

export function update(id: string, payload: RecurringTaskUpdate): Promise<RecurringTask> {
  return httpClient
    .patch<RecurringTask>(`/recurring-tasks/${id}`, payload)
    .then((response) => response.data);
}

export function remove(id: string): Promise<void> {
  return httpClient.delete(`/recurring-tasks/${id}`).then(() => undefined);
}

/** Marca/desmarca a ocorrência de **hoje** — nunca uma data escolhida pelo
 * cliente (contracts/recurring-tasks.md, research.md #4). */
export function completeToday(id: string): Promise<RecurringTask> {
  return httpClient
    .post<RecurringTask>(`/recurring-tasks/${id}/completions`)
    .then((response) => response.data);
}

export function uncompleteToday(id: string): Promise<RecurringTask> {
  return httpClient
    .delete<RecurringTask>(`/recurring-tasks/${id}/completions`)
    .then((response) => response.data);
}
