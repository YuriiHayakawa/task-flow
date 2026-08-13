import { useCallback, useEffect, useState } from "react";

import * as projectService from "@/services/projectService";
import type { Project, ProjectUpdate } from "@/types/project";

interface UseProjectResult {
  project: Project | null;
  isLoading: boolean;
  error: string | null;
  updateProject: (payload: ProjectUpdate) => Promise<void>;
  deleteProject: () => Promise<void>;
  refetch: () => Promise<void>;
}

/** Um único projeto — `GET /projects/{id}` exige que o usuário seja membro
 * do workspace ao qual o projeto pertence (qualquer role). */
export function useProject(projectId: string): UseProjectResult {
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProject = useCallback(async () => {
    // Guarda contra `projectId` ainda vazio (ex.: `TaskDetailPage` só sabe
    // o `project_id` depois que a própria tarefa carrega) — evita uma
    // requisição fadada a 404.
    if (!projectId) {
      setProject(null);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await projectService.get(projectId);
      setProject(result);
    } catch {
      setError("Não foi possível carregar este projeto.");
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void fetchProject();
  }, [fetchProject]);

  const updateProject = useCallback(
    async (payload: ProjectUpdate) => {
      await projectService.update(projectId, payload);
      await fetchProject();
    },
    [projectId, fetchProject],
  );

  const deleteProject = useCallback(async () => {
    await projectService.remove(projectId);
  }, [projectId]);

  return { project, isLoading, error, updateProject, deleteProject, refetch: fetchProject };
}
