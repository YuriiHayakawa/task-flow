import { useCallback, useEffect, useState } from "react";

import * as workspaceService from "@/services/workspaceService";
import type { Workspace, WorkspaceUpdate } from "@/types/workspace";

interface UseWorkspaceResult {
  workspace: Workspace | null;
  isLoading: boolean;
  error: string | null;
  updateWorkspace: (payload: WorkspaceUpdate) => Promise<void>;
  deleteWorkspace: () => Promise<void>;
  refetch: () => Promise<void>;
}

/** Um único workspace (inclui `my_role`, necessário para condicionar ações
 * de `WorkspaceDetailPage`/`WorkspaceMembersPage` à role do usuário atual
 * nesse workspace — o mesmo `require_workspace_member` do backend garante
 * `404` aqui se o usuário não for membro). */
export function useWorkspace(workspaceId: string): UseWorkspaceResult {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkspace = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await workspaceService.get(workspaceId);
      setWorkspace(result);
    } catch {
      setError("Não foi possível carregar este workspace.");
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    void fetchWorkspace();
  }, [fetchWorkspace]);

  const updateWorkspace = useCallback(
    async (payload: WorkspaceUpdate) => {
      await workspaceService.update(workspaceId, payload);
      await fetchWorkspace();
    },
    [workspaceId, fetchWorkspace],
  );

  const deleteWorkspace = useCallback(async () => {
    await workspaceService.remove(workspaceId);
  }, [workspaceId]);

  return { workspace, isLoading, error, updateWorkspace, deleteWorkspace, refetch: fetchWorkspace };
}
