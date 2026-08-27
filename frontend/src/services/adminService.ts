import httpClient from "@/services/httpClient";
import type { PaginatedResponse } from "@/types/common";
import type { User, UserStatusUpdate } from "@/types/user";

export interface AdminUsersQuery {
  is_active?: boolean;
  page?: number;
  page_size?: number;
}

/** `GET /admin/users` (US13, FR-043) — só acessível a `is_system_admin`
 * (backend rejeita com 403 quem não é; `AdminRoute` no frontend só evita a
 * navegação, não é a barreira de segurança real — Constitution IV). */
export function listUsers(params: AdminUsersQuery = {}): Promise<PaginatedResponse<User>> {
  return httpClient
    .get<PaginatedResponse<User>>("/admin/users", { params })
    .then((response) => response.data);
}

/** `PATCH /admin/users/{id}/status` (FR-043) — só ativa/desativa; nunca
 * altera nome/e-mail (fora do escopo do System Admin, FR-045). */
export function setUserStatus(userId: string, isActive: boolean): Promise<User> {
  const payload: UserStatusUpdate = { is_active: isActive };
  return httpClient
    .patch<User>(`/admin/users/${userId}/status`, payload)
    .then((response) => response.data);
}
