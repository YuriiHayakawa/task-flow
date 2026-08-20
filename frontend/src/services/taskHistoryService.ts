import httpClient from "@/services/httpClient";
import type { PaginatedResponse } from "@/types/common";
import type { TaskHistoryEntry } from "@/types/taskHistory";

/** Envelope paginado (mesmo atalho de Comments/Notifications — `page=1`,
 * sem paginação real em SQL). Já chega ordenado por `changed_at`
 * descendente do backend. */
export function list(taskId: string): Promise<PaginatedResponse<TaskHistoryEntry>> {
  return httpClient
    .get<PaginatedResponse<TaskHistoryEntry>>(`/tasks/${taskId}/history`)
    .then((response) => response.data);
}
