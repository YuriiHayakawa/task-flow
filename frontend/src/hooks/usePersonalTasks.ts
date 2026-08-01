import { useCallback, useEffect, useState } from "react";

import * as taskService from "@/services/taskService";
import type { Task, TaskCreate, TaskUpdate } from "@/types/task";

interface UsePersonalTasksResult {
  tasks: Task[];
  isLoading: boolean;
  error: string | null;
  createTask: (payload: TaskCreate) => Promise<void>;
  updateTask: (taskId: string, payload: TaskUpdate) => Promise<void>;
  refetch: () => Promise<void>;
}

/** Tarefas pessoais do usuário atual (`workspace_id === null`).
 * `GET /tasks` já retorna apenas as tarefas pessoais do próprio chamador
 * unidas às tarefas dos workspaces dos quais participa (nunca tarefas
 * pessoais de terceiros) — o filtro abaixo só restringe a exibição desta
 * página às pessoais, sem implicar em risco de acesso a dados de terceiros. */
export function usePersonalTasks(): UsePersonalTasksResult {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTasks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await taskService.list();
      setTasks(response.items.filter((task) => task.workspace_id === null));
    } catch {
      setError("Não foi possível carregar suas tarefas.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchTasks();
  }, [fetchTasks]);

  const createTask = useCallback(
    async (payload: TaskCreate) => {
      await taskService.create(payload);
      await fetchTasks();
    },
    [fetchTasks],
  );

  const updateTask = useCallback(
    async (taskId: string, payload: TaskUpdate) => {
      await taskService.update(taskId, payload);
      await fetchTasks();
    },
    [fetchTasks],
  );

  return { tasks, isLoading, error, createTask, updateTask, refetch: fetchTasks };
}
