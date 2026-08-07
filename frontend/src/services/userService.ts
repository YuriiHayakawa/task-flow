import httpClient from "@/services/httpClient";
import type { UserLookup } from "@/types/user";

/** `GET /users/lookup` — resolve um e-mail em dados mínimos de usuário
 * (`id`/`name`/`email`), único propósito é viabilizar "adicionar membro
 * por e-mail" em workspaces (`workspaceService.addMember` exige `user_id`). */
export function lookupByEmail(email: string): Promise<UserLookup> {
  return httpClient
    .get<UserLookup>("/users/lookup", { params: { email } })
    .then((response) => response.data);
}
