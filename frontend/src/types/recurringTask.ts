export type RecurrenceType = "DAILY" | "WEEKLY" | "MONTHLY";

export interface RecurringTask {
  id: string;
  title: string;
  recurrence_type: RecurrenceType;
  weekdays: number[];
  month_day: number | null;
  is_due_today: boolean;
  completed_today: boolean;
  created_at: string;
  updated_at: string;
}

export interface RecurringTaskCreate {
  title: string;
  recurrence_type: RecurrenceType;
  weekdays?: number[];
  month_day?: number | null;
}

export interface RecurringTaskUpdate {
  title?: string;
  recurrence_type?: RecurrenceType;
  weekdays?: number[];
  month_day?: number | null;
}
