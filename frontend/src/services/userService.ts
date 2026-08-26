import httpClient from "@/services/httpClient";
import type { User, UserLookup, UserUpdate } from "@/types/user";

/** `GET /users/lookup` — resolve um e-mail em dados mínimos de usuário
 * (`id`/`name`/`email`), único propósito é viabilizar "adicionar membro
 * por e-mail" em workspaces (`workspaceService.addMember` exige `user_id`). */
export function lookupByEmail(email: string): Promise<UserLookup> {
  return httpClient
    .get<UserLookup>("/users/lookup", { params: { email } })
    .then((response) => response.data);
}

/** `GET /users/me` (US7) — perfil completo do usuário autenticado. */
export function getMe(): Promise<User> {
  return httpClient.get<User>("/users/me").then((response) => response.data);
}

/** `PATCH /users/me` (US7, FR-051 a FR-054) — `name`/`email` opcionais (ao
 * menos um obrigatório, já validado pelo backend); nunca aceita senha/foto. */
export function updateMe(payload: UserUpdate): Promise<User> {
  return httpClient.patch<User>("/users/me", payload).then((response) => response.data);
}
