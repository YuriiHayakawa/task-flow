import { useCallback, useEffect, useState } from "react";

import * as recurringTaskService from "@/services/recurringTaskService";
import type { RecurringTask, RecurringTaskCreate, RecurringTaskUpdate } from "@/types/recurringTask";

interface UseRecurringTasksResult {
  recurringTasks: RecurringTask[];
  isLoading: boolean;
  error: string | null;
  createRecurringTask: (payload: RecurringTaskCreate) => Promise<void>;
  updateRecurringTask: (id: string, payload: RecurringTaskUpdate) => Promise<void>;
  removeRecurringTask: (id: string) => Promise<void>;
  toggleToday: (recurringTask: RecurringTask) => Promise<void>;
  refetch: () => Promise<void>;
}

/** Tarefas Fixas do usuário autenticado — mesmo padrão de
 * `usePersonalTasks`/`useTaskMembers`. `toggleToday` decide sozinho entre
 * concluir/desconcluir com base no `completed_today` já carregado, então
 * quem usa o hook nunca precisa saber qual dos dois endpoints chamar. */
export function useRecurringTasks(): UseRecurringTasksResult {
  const [recurringTasks, setRecurringTasks] = useState<RecurringTask[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRecurringTasks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await recurringTaskService.list();
      setRecurringTasks(result);
    } catch {
      setError("Não foi possível carregar as tarefas fixas.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchRecurringTasks();
  }, [fetchRecurringTasks]);

  const createRecurringTask = useCallback(
    async (payload: RecurringTaskCreate) => {
      await recurringTaskService.create(payload);
      await fetchRecurringTasks();
    },
    [fetchRecurringTasks],
  );

  const updateRecurringTask = useCallback(
    async (id: string, payload: RecurringTaskUpdate) => {
      await recurringTaskService.update(id, payload);
      await fetchRecurringTasks();
    },
    [fetchRecurringTasks],
  );

  const removeRecurringTask = useCallback(
    async (id: string) => {
      await recurringTaskService.remove(id);
      await fetchRecurringTasks();
    },
    [fetchRecurringTasks],
  );

  const toggleToday = useCallback(
    async (recurringTask: RecurringTask) => {
      if (recurringTask.completed_today) {
        await recurringTaskService.uncompleteToday(recurringTask.id);
      } else {
        await recurringTaskService.completeToday(recurringTask.id);
      }
      await fetchRecurringTasks();
    },
    [fetchRecurringTasks],
  );

  return {
    recurringTasks,
    isLoading,
    error,
    createRecurringTask,
    updateRecurringTask,
    removeRecurringTask,
    toggleToday,
    refetch: fetchRecurringTasks,
  };
}
