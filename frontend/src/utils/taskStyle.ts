import { CheckCircle2, Circle, CircleDot, type LucideIcon } from "lucide-react";

import type { Task, TaskPriority, TaskStatus } from "@/types/task";

/** Mesma paleta/ícones já usados no board kanban de "Minhas tarefas" e no
 * Dashboard — reaproveitada aqui para as telas de projeto/tarefa de
 * workspace, mantendo uma única linguagem visual por status/prioridade
 * em todo o app (Constitution V). */
export const STATUS_LABEL: Record<TaskStatus, string> = {
  PENDING: "Pendente",
  IN_PROGRESS: "Em andamento",
  DONE: "Concluída",
};

export const STATUS_ICON: Record<TaskStatus, LucideIcon> = {
  PENDING: Circle,
  IN_PROGRESS: CircleDot,
  DONE: CheckCircle2,
};

export const STATUS_BADGE_CLASS: Record<TaskStatus, string> = {
  PENDING: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  IN_PROGRESS: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  DONE: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
};

export const PRIORITY_LABEL: Record<TaskPriority, string> = {
  LOW: "Baixa",
  MEDIUM: "Média",
  HIGH: "Alta",
  URGENT: "Urgente",
};

export const PRIORITY_CHIP_CLASS: Record<TaskPriority, string> = {
  LOW: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  MEDIUM: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  HIGH: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  URGENT: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
};

export interface DueInfo {
  label: string;
  tone: "neutral" | "warning" | "danger";
}

export const DUE_CHIP_CLASS: Record<DueInfo["tone"], string> = {
  neutral: "bg-muted text-muted-foreground",
  warning: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400",
  danger: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
};

/** Rótulo relativo e amigável de prazo — indicador de contexto no cartão,
 * não a fonte oficial de "atrasada"/"vencendo hoje" (essa é o Dashboard,
 * calculado no backend com `APP_TIMEZONE`). */
export function describeDueDate(dueDate: string, isDone: boolean): DueInfo {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(`${dueDate}T00:00:00`);
  const diffDays = Math.round((due.getTime() - today.getTime()) / 86_400_000);
  const formatted = due.toLocaleDateString("pt-BR");

  if (!isDone && diffDays < 0) return { label: `Atrasada · ${formatted}`, tone: "danger" };
  if (diffDays === 0) return { label: "Vence hoje", tone: "warning" };
  if (diffDays === 1) return { label: "Vence amanhã", tone: "neutral" };
  return { label: formatted, tone: "neutral" };
}

export function isTaskDone(task: Pick<Task, "status">): boolean {
  return task.status === "DONE";
}
