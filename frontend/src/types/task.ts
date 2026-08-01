export type TaskStatus = "PENDING" | "IN_PROGRESS" | "DONE";
export type TaskPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";
export type TaskSortBy = "due_date" | "priority" | "created_at";
export type TaskSortOrder = "asc" | "desc";

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  assignee_id: string;
  creator_id: string;
  workspace_id: string | null;
  project_id: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskCreate {
  title: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_date?: string | null;
  assignee_id?: string | null;
  workspace_id?: string | null;
  project_id?: string | null;
}

export interface TaskUpdate {
  // workspace_id/project_id existem em TaskUpdate no backend só para serem
  // rejeitados (conversão de tarefa pessoal ainda não suportada) — omitidos
  // aqui porque nenhum fluxo do frontend deve tentar enviá-los.
  title?: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_date?: string | null;
  assignee_id?: string | null;
}

export interface TaskSearchParams {
  search?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  workspace_id?: string;
  project_id?: string;
  assignee_id?: string;
  sort_by?: TaskSortBy;
  sort_order?: TaskSortOrder;
  page?: number;
  page_size?: number;
}
