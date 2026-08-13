import { useCallback, useEffect, useState } from "react";

import * as workspaceService from "@/services/workspaceService";
import type {
  TransferOwnershipRequest,
  WorkspaceMember,
  WorkspaceMemberCreate,
  WorkspaceRole,
} from "@/types/workspace";

interface UseWorkspaceMembersResult {
  members: WorkspaceMember[];
  isLoading: boolean;
  error: string | null;
  addMember: (payload: WorkspaceMemberCreate) => Promise<void>;
  updateMemberRole: (userId: string, role: WorkspaceRole) => Promise<void>;
  removeMember: (userId: string) => Promise<void>;
  transferOwnership: (payload: TransferOwnershipRequest) => Promise<void>;
  refetch: () => Promise<void>;
}

/** Membros de um workspace específico. As ações (`addMember`,
 * `updateMemberRole`, `removeMember`, `transferOwnership`) propagam o erro
 * ao chamador em vez de engoli-lo — mesmo padrão de `usePersonalTasks`
 * (`createTask`/`updateTask`), pois cada ação tem mensagens de erro
 * específicas (ex.: "tarefas ativas pendentes de reatribuição") que só a UI
 * que a disparou sabe exibir com o contexto certo. */
export function useWorkspaceMembers(workspaceId: string): UseWorkspaceMembersResult {
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMembers = useCallback(async () => {
    // Guarda contra `workspaceId` ainda vazio (ex.: telas que só descobrem
    // o workspace de forma assíncrona, como `TaskFormPage` em modo de
    // edição) — evita uma requisição fadada a 404 e, mais importante, evita
    // um `isLoading=false` prematuro com `members` ainda vazio.
    if (!workspaceId) {
      setMembers([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await workspaceService.listMembers(workspaceId);
      setMembers(response.items);
    } catch {
      setError("Não foi possível carregar os membros deste workspace.");
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    void fetchMembers();
  }, [fetchMembers]);

  const addMember = useCallback(
    async (payload: WorkspaceMemberCreate) => {
      await workspaceService.addMember(workspaceId, payload);
      await fetchMembers();
    },
    [workspaceId, fetchMembers],
  );

  const updateMemberRole = useCallback(
    async (userId: string, role: WorkspaceRole) => {
      await workspaceService.updateMemberRole(workspaceId, userId, { role });
      await fetchMembers();
    },
    [workspaceId, fetchMembers],
  );

  const removeMember = useCallback(
    async (userId: string) => {
      await workspaceService.removeMember(workspaceId, userId);
      await fetchMembers();
    },
    [workspaceId, fetchMembers],
  );

  const transferOwnership = useCallback(
    async (payload: TransferOwnershipRequest) => {
      await workspaceService.transferOwnership(workspaceId, payload);
      await fetchMembers();
    },
    [workspaceId, fetchMembers],
  );

  return {
    members,
    isLoading,
    error,
    addMember,
    updateMemberRole,
    removeMember,
    transferOwnership,
    refetch: fetchMembers,
  };
}
