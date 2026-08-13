export interface DashboardCounts {
  pending: number;
  in_progress: number;
  done: number;
  overdue: number;
  due_today: number;
}

export interface DashboardSummary {
  counts: DashboardCounts;
}

/** Filtro de escopo opcional de `GET /dashboard` — no máximo um por vez
 * (contracts/dashboard-and-notifications.md, seção "Escopo opcional"). */
export interface DashboardScopeParams {
  workspace_id?: string;
  project_id?: string;
  personal_only?: boolean;
}
