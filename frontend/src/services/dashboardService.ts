import httpClient from "@/services/httpClient";
import type { DashboardScopeParams, DashboardSummary } from "@/types/dashboard";

export function getSummary(params: DashboardScopeParams = {}): Promise<DashboardSummary> {
  return httpClient
    .get<DashboardSummary>("/dashboard", { params })
    .then((response) => response.data);
}
