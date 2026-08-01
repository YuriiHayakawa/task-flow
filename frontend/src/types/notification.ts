export type NotificationType = "DUE_SOON" | "NEW_COMMENT" | "TASK_CHANGED";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  task_id: string | null;
  is_read: boolean;
  created_at: string;
}
