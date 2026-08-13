import { useCallback, useEffect, useState } from "react";

import * as dashboardService from "@/services/dashboardService";
import type { DashboardCounts, DashboardScopeParams } from "@/types/dashboard";

interface UseDashboardResult {
  counts: DashboardCounts | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/** `params` filtra o resumo por escopo (workspace/projeto/só pessoal — ver
 * `DashboardScopeParams`); por padrão (`{}`) é o resumo combinado de
 * sempre (FR-048). Refaz a busca sempre que o escopo muda. */
export function useDashboard(params: DashboardScopeParams = {}): UseDashboardResult {
  const [counts, setCounts] = useState<DashboardCounts | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const paramsKey = JSON.stringify(params);

  const fetchSummary = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const summary = await dashboardService.getSummary(JSON.parse(paramsKey) as DashboardScopeParams);
      setCounts(summary.counts);
    } catch {
      setError("Não foi possível carregar o resumo do dashboard.");
    } finally {
      setIsLoading(false);
    }
  }, [paramsKey]);

  useEffect(() => {
    void fetchSummary();
  }, [fetchSummary]);

  return { counts, isLoading, error, refetch: fetchSummary };
}
