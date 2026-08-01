export interface TaskHistoryEntry {
  id: string;
  field_changed: string;
  old_value: string | null;
  new_value: string | null;
  changed_by_id: string;
  changed_by_name: string;
  changed_by_email: string;
  changed_at: string;
}
