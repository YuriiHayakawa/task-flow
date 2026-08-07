import { useCallback, useEffect, useState } from "react";

import * as taskService from "@/services/taskService";
import type { Task, TaskCreate, TaskSearchParams } from "@/types/task";

interface UseTasksResult {
  tasks: Task[];
  isLoading: boolean;
  error: string | null;
  createTask: (payload: TaskCreate) => Promise<Task>;
  refetch: () => Promise<void>;
}

/** Lista de tarefas com filtros arbitrários (`GET /tasks` — mesmo endpoint
 * central de `usePersonalTasks`, mas sem o filtro fixo de tarefa pessoal).
 * Usado por telas que listam tarefas de um projeto/workspace específico
 * (ex.: `ProjectDetailPage` filtrando por `project_id`). */
export function useTasks(params: TaskSearchParams): UseTasksResult {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Chave estável para o efeito não re-executar a cada render por causa de
  // um novo objeto `params` com o mesmo conteúdo.
  const paramsKey = JSON.stringify(params);

  const fetchTasks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await taskService.list(JSON.parse(paramsKey) as TaskSearchParams);
      setTasks(response.items);
    } catch {
      setError("Não foi possível carregar as tarefas.");
    } finally {
      setIsLoading(false);
    }
  }, [paramsKey]);

  useEffect(() => {
    void fetchTasks();
  }, [fetchTasks]);

  const createTask = useCallback(
    async (payload: TaskCreate) => {
      const created = await taskService.create(payload);
      await fetchTasks();
      return created;
    },
    [fetchTasks],
  );

  return { tasks, isLoading, error, createTask, refetch: fetchTasks };
}
