import { useCallback, useEffect, useState } from "react";

import * as taskService from "@/services/taskService";
import type { Task, TaskUpdate } from "@/types/task";

interface UseTaskResult {
  task: Task | null;
  isLoading: boolean;
  error: string | null;
  updateTask: (payload: TaskUpdate) => Promise<void>;
  deleteTask: () => Promise<void>;
  refetch: () => Promise<void>;
}

/** Uma única tarefa — `GET /tasks/{id}` exige ser membro do workspace da
 * tarefa (visibilidade ampla) ou, para tarefa pessoal, o próprio criador. */
export function useTask(taskId: string): UseTaskResult {
  const [task, setTask] = useState<Task | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTask = useCallback(async () => {
    // Guarda contra `taskId` vazio (ex.: `TaskFormPage` em modo de criação
    // reaproveita este hook só em modo de edição, mas chama `useTask`
    // incondicionalmente por regra dos Hooks) — sem isso, `GET /tasks/`
    // (id vazio) cai no endpoint de listagem por redirecionamento de barra
    // final, devolvendo um envelope paginado em vez de 404.
    if (!taskId) {
      setTask(null);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await taskService.get(taskId);
      setTask(result);
    } catch {
      setError("Não foi possível carregar esta tarefa.");
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    void fetchTask();
  }, [fetchTask]);

  const updateTask = useCallback(
    async (payload: TaskUpdate) => {
      await taskService.update(taskId, payload);
      await fetchTask();
    },
    [taskId, fetchTask],
  );

  const deleteTask = useCallback(async () => {
    await taskService.remove(taskId);
  }, [taskId]);

  return { task, isLoading, error, updateTask, deleteTask, refetch: fetchTask };
}
