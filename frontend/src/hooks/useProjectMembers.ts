import { useCallback, useEffect, useState } from "react";

import * as projectMemberService from "@/services/projectMemberService";
import type { ProjectMember, ProjectMemberCreate } from "@/types/projectMember";

interface UseProjectMembersResult {
  members: ProjectMember[];
  isLoading: boolean;
  error: string | null;
  addMember: (payload: ProjectMemberCreate) => Promise<void>;
  removeMember: (userId: string) => Promise<void>;
  refetch: () => Promise<void>;
}

/** Membros de um projeto específico (003-membros-projeto) — mesmo padrão de
 * `useWorkspaceMembers`, sem role (lista flat). `addMember`/`removeMember`
 * propagam o erro ao chamador em vez de engoli-lo (mesmo motivo de
 * `useWorkspaceMembers`: a UI que disparou a ação sabe exibir a mensagem
 * certa — ex.: tarefas ativas pendentes de reatribuição). */
export function useProjectMembers(projectId: string): UseProjectMembersResult {
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMembers = useCallback(async () => {
    if (!projectId) {
      setMembers([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await projectMemberService.list(projectId);
      setMembers(response.items);
    } catch {
      setError("Não foi possível carregar os membros deste projeto.");
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void fetchMembers();
  }, [fetchMembers]);

  const addMember = useCallback(
    async (payload: ProjectMemberCreate) => {
      await projectMemberService.add(projectId, payload);
      await fetchMembers();
    },
    [projectId, fetchMembers],
  );

  const removeMember = useCallback(
    async (userId: string) => {
      await projectMemberService.remove(projectId, userId);
      await fetchMembers();
    },
    [projectId, fetchMembers],
  );

  return { members, isLoading, error, addMember, removeMember, refetch: fetchMembers };
}
