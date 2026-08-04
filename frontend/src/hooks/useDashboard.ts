import { useCallback, useEffect, useState } from "react";

import * as dashboardService from "@/services/dashboardService";
import type { DashboardCounts } from "@/types/dashboard";

interface UseDashboardResult {
  counts: DashboardCounts | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useDashboard(): UseDashboardResult {
  const [counts, setCounts] = useState<DashboardCounts | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const summary = await dashboardService.getSummary();
      setCounts(summary.counts);
    } catch {
      setError("Não foi possível carregar o resumo do dashboard.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchSummary();
  }, [fetchSummary]);

  return { counts, isLoading, error, refetch: fetchSummary };
}
