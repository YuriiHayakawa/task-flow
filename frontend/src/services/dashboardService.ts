import httpClient from "@/services/httpClient";
import type { DashboardSummary } from "@/types/dashboard";

export function getSummary(): Promise<DashboardSummary> {
  return httpClient.get<DashboardSummary>("/dashboard").then((response) => response.data);
}
