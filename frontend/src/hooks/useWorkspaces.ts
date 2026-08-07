import { useCallback, useEffect, useState } from "react";

import * as workspaceService from "@/services/workspaceService";
import type { Workspace, WorkspaceCreate } from "@/types/workspace";

interface UseWorkspacesResult {
  workspaces: Workspace[];
  isLoading: boolean;
  error: string | null;
  createWorkspace: (payload: WorkspaceCreate) => Promise<Workspace>;
  refetch: () => Promise<void>;
}

/** Workspaces dos quais o usuário atual é membro (qualquer role) — `GET
 * /workspaces` já restringe isso no backend (contracts/workspaces.md). */
export function useWorkspaces(): UseWorkspacesResult {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkspaces = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await workspaceService.list();
      setWorkspaces(response.items);
    } catch {
      setError("Não foi possível carregar seus workspaces.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchWorkspaces();
  }, [fetchWorkspaces]);

  const createWorkspace = useCallback(
    async (payload: WorkspaceCreate) => {
      const created = await workspaceService.create(payload);
      await fetchWorkspaces();
      return created;
    },
    [fetchWorkspaces],
  );

  return { workspaces, isLoading, error, createWorkspace, refetch: fetchWorkspaces };
}
