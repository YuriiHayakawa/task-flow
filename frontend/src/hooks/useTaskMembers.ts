import { useCallback, useEffect, useState } from "react";

import * as taskMemberService from "@/services/taskMemberService";
import type { TaskMember, TaskMemberCreate } from "@/types/taskMember";

interface UseTaskMembersResult {
  members: TaskMember[];
  isLoading: boolean;
  error: string | null;
  addMember: (payload: TaskMemberCreate) => Promise<void>;
  removeMember: (userId: string) => Promise<void>;
  refetch: () => Promise<void>;
}

/** Participantes de uma tarefa — a lista sempre inclui o responsável como
 * participante implícito (`added_at: null` quando não foi adicionado
 * manualmente), mesmo em tarefa pessoal (contracts/projects-and-tasks.md).
 * `addMember`/`removeMember` propagam o erro ao chamador (mesmo padrão de
 * `useWorkspaceMembers`), pois cada mensagem de erro do backend já é
 * acionável por si só (ex.: "tarefas pessoais não podem ter
 * participantes"). */
export function useTaskMembers(taskId: string): UseTaskMembersResult {
  const [members, setMembers] = useState<TaskMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMembers = useCallback(async () => {
    if (!taskId) {
      setMembers([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await taskMemberService.list(taskId);
      setMembers(result);
    } catch {
      setError("Não foi possível carregar os participantes desta tarefa.");
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    void fetchMembers();
  }, [fetchMembers]);

  const addMember = useCallback(
    async (payload: TaskMemberCreate) => {
      await taskMemberService.add(taskId, payload);
      await fetchMembers();
    },
    [taskId, fetchMembers],
  );

  const removeMember = useCallback(
    async (userId: string) => {
      await taskMemberService.remove(taskId, userId);
      await fetchMembers();
    },
    [taskId, fetchMembers],
  );

  return { members, isLoading, error, addMember, removeMember, refetch: fetchMembers };
}
