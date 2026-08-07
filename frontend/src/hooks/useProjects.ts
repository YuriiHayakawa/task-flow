import { useCallback, useEffect, useState } from "react";

import * as projectService from "@/services/projectService";
import type { Project, ProjectCreate } from "@/types/project";

interface UseProjectsResult {
  projects: Project[];
  isLoading: boolean;
  error: string | null;
  createProject: (payload: ProjectCreate) => Promise<Project>;
  refetch: () => Promise<void>;
}

/** Projetos de um workspace específico — `GET /workspaces/{id}/projects`
 * já restringe a membros desse workspace (qualquer role visualiza). */
export function useProjects(workspaceId: string): UseProjectsResult {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProjects = useCallback(async () => {
    // Guarda contra `workspaceId` ainda vazio (ex.: telas que só descobrem
    // o workspace de forma assíncrona) — evita uma requisição fadada a 404.
    if (!workspaceId) {
      setProjects([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await projectService.list(workspaceId);
      setProjects(response.items);
    } catch {
      setError("Não foi possível carregar os projetos deste workspace.");
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    void fetchProjects();
  }, [fetchProjects]);

  const createProject = useCallback(
    async (payload: ProjectCreate) => {
      const created = await projectService.create(workspaceId, payload);
      await fetchProjects();
      return created;
    },
    [workspaceId, fetchProjects],
  );

  return { projects, isLoading, error, createProject, refetch: fetchProjects };
}
