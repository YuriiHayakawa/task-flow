import { useCallback, useEffect, useState } from "react";

import * as taskHistoryService from "@/services/taskHistoryService";
import type { TaskHistoryEntry } from "@/types/taskHistory";

interface UseTaskHistoryResult {
  entries: TaskHistoryEntry[];
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/** Histórico de alterações de uma tarefa — só leitura (não há escrita
 * manual, as entradas são geradas automaticamente por `TaskService.update`,
 * US12). Mesmo padrão de fetch de `useComments`/`useTaskMembers`. */
export function useTaskHistory(taskId: string): UseTaskHistoryResult {
  const [entries, setEntries] = useState<TaskHistoryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEntries = useCallback(async () => {
    if (!taskId) {
      setEntries([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await taskHistoryService.list(taskId);
      setEntries(result.items);
    } catch {
      setError("Não foi possível carregar o histórico desta tarefa.");
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    void fetchEntries();
  }, [fetchEntries]);

  return { entries, isLoading, error, refetch: fetchEntries };
}
