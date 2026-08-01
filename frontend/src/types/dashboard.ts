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
