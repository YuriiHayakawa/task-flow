import { useCallback } from "react";

import { useAuth } from "@/contexts/AuthContext";
import * as userService from "@/services/userService";
import type { User, UserUpdate } from "@/types/user";

interface UseProfileResult {
  user: User | null;
  updateProfile: (payload: UserUpdate) => Promise<void>;
}

/** Perfil do usuário autenticado (US7). Não faz fetch próprio: o
 * `AuthContext` já carrega `/users/me` na inicialização da aplicação (é
 * pré-requisito para qualquer rota protegida), então reaproveitar esse
 * estado evita uma segunda chamada redundante. `updateProfile` propaga o
 * erro ao chamador em vez de engoli-lo (mesmo padrão de
 * `useWorkspaceMembers`/`useProjectMembers` — a UI que disparou a ação sabe
 * exibir a mensagem certa, ex.: "Este e-mail já está em uso.") e sincroniza
 * o `AuthContext` em caso de sucesso, para a sidebar refletir nome/e-mail
 * novos sem precisar recarregar a página. */
export function useProfile(): UseProfileResult {
  const { user, updateUser } = useAuth();

  const updateProfile = useCallback(
    async (payload: UserUpdate) => {
      const updated = await userService.updateMe(payload);
      updateUser(updated);
    },
    [updateUser],
  );

  return { user, updateProfile };
}
