import { useCallback, useEffect, useState } from "react";

import * as adminService from "@/services/adminService";
import type { AdminUsersQuery } from "@/services/adminService";
import type { User } from "@/types/user";

interface UseAdminUsersResult {
  users: User[];
  total: number;
  isLoading: boolean;
  error: string | null;
  setUserActive: (userId: string, isActive: boolean) => Promise<void>;
  refetch: () => Promise<void>;
}

/** Contas da plataforma (US13) — `AdminUsersPage` é a única consumidora.
 * Mesmo padrão "mutate then refetch" dos demais hooks (`useChecklist`,
 * `useNotifications`); `params` inclui filtro de status e paginação, então
 * troca de filtro/página aqui já refaz a busca sozinha (mesma técnica de
 * `useTasks` — chave estável via `JSON.stringify` evita refetch por causa
 * de um novo objeto `params` com o mesmo conteúdo). */
export function useAdminUsers(params: AdminUsersQuery): UseAdminUsersResult {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const paramsKey = JSON.stringify(params);

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await adminService.listUsers(JSON.parse(paramsKey) as AdminUsersQuery);
      setUsers(response.items);
      setTotal(response.total);
    } catch {
      setError("Não foi possível carregar as contas da plataforma.");
    } finally {
      setIsLoading(false);
    }
  }, [paramsKey]);

  useEffect(() => {
    void fetchUsers();
  }, [fetchUsers]);

  const setUserActive = useCallback(
    async (userId: string, isActive: boolean) => {
      await adminService.setUserStatus(userId, isActive);
      await fetchUsers();
    },
    [fetchUsers],
  );

  return { users, total, isLoading, error, setUserActive, refetch: fetchUsers };
}
