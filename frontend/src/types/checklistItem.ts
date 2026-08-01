export interface ChecklistItem {
  id: string;
  description: string;
  is_done: boolean;
  completed_at: string | null;
}

export interface ChecklistItemCreate {
  description: string;
}

export interface ChecklistItemUpdate {
  is_done: boolean;
}
