import httpClient from "@/services/httpClient";
import type { PaginatedResponse } from "@/types/common";
import type { Notification } from "@/types/notification";

/** `GET /notifications` (US11) — lista paginada, mais recentes primeiro
 * (ordenação já é responsabilidade do backend). `page_size` maior que o
 * default (20): notificação é uma lista que o usuário espera ver por
 * inteiro de uma vez, não paginada como tarefas — sem UI de paginação
 * nesta primeira versão (`contracts/dashboard-and-notifications.md`). */
export function list(): Promise<PaginatedResponse<Notification>> {
  return httpClient
    .get<PaginatedResponse<Notification>>("/notifications", { params: { page_size: 50 } })
    .then((response) => response.data);
}

export function markAsRead(notificationId: string): Promise<Notification> {
  return httpClient
    .patch<Notification>(`/notifications/${notificationId}/read`)
    .then((response) => response.data);
}

export function markAllAsRead(): Promise<{ updated: number }> {
  return httpClient
    .patch<{ updated: number }>("/notifications/read-all")
    .then((response) => response.data);
}
