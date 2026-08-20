import { useCallback, useEffect, useState } from "react";

import * as checklistService from "@/services/checklistService";
import type { ChecklistItem, ChecklistItemCreate } from "@/types/checklistItem";

interface UseChecklistResult {
  items: ChecklistItem[];
  isLoading: boolean;
  error: string | null;
  addItem: (payload: ChecklistItemCreate) => Promise<void>;
  toggleItem: (itemId: string, isDone: boolean) => Promise<void>;
  removeItem: (itemId: string) => Promise<void>;
  refetch: () => Promise<void>;
}

/** Checklist de uma tarefa — mesmo padrão de `useTaskMembers`/`useComments`.
 * `toggleItem` só envia `is_done` (único campo suportado por `PATCH`,
 * refinamento #7 — sem edição textual do item neste MVP). */
export function useChecklist(taskId: string): UseChecklistResult {
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchItems = useCallback(async () => {
    if (!taskId) {
      setItems([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await checklistService.list(taskId);
      setItems(result);
    } catch {
      setError("Não foi possível carregar o checklist desta tarefa.");
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    void fetchItems();
  }, [fetchItems]);

  const addItem = useCallback(
    async (payload: ChecklistItemCreate) => {
      await checklistService.create(taskId, payload);
      await fetchItems();
    },
    [taskId, fetchItems],
  );

  const toggleItem = useCallback(
    async (itemId: string, isDone: boolean) => {
      await checklistService.update(taskId, itemId, { is_done: isDone });
      await fetchItems();
    },
    [taskId, fetchItems],
  );

  const removeItem = useCallback(
    async (itemId: string) => {
      await checklistService.remove(taskId, itemId);
      await fetchItems();
    },
    [taskId, fetchItems],
  );

  return { items, isLoading, error, addItem, toggleItem, removeItem, refetch: fetchItems };
}
