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

/** Cor sólida (não o tint claro de `STATUS_BADGE_CLASS`) — mesmos tons do
 * friso/ícone das colunas do board kanban (`PersonalTasksPage`), reaproveitada
 * em qualquer gráfico de distribuição por status (ex.: Dashboard). */
export const STATUS_ACCENT_CLASS: Record<TaskStatus, string> = {
  PENDING: "bg-slate-400",
  IN_PROGRESS: "bg-blue-500",
  DONE: "bg-emerald-500",
};

/** Mesmos tons de `STATUS_ACCENT_CLASS`, como cor de texto/ícone —
 * classes completas e estáticas (o JIT do Tailwind não detecta nomes de
 * classe montados via template string em tempo de execução). */
export const STATUS_ICON_COLOR_CLASS: Record<TaskStatus, string> = {
  PENDING: "text-slate-500",
  IN_PROGRESS: "text-blue-500",
  DONE: "text-emerald-500",
};

/** Mesmos tons, como cor de traço de SVG (`stroke-*`) — usado no donut de
 * distribuição por status do Dashboard. */
export const STATUS_STROKE_CLASS: Record<TaskStatus, string> = {
  PENDING: "stroke-slate-400",
  IN_PROGRESS: "stroke-blue-500",
  DONE: "stroke-emerald-500",
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

/** Borda lateral por prioridade — usada nos cartões de tarefa de qualquer
 * board kanban do app (`PersonalTasksPage`, `ProjectDetailPage`). */
export const PRIORITY_BORDER_CLASS: Record<TaskPriority, string> = {
  LOW: "border-l-slate-300",
  MEDIUM: "border-l-blue-400",
  HIGH: "border-l-amber-400",
  URGENT: "border-l-red-500",
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

export interface StatusColumnStyle {
  iconWrapperClass: string;
  columnTintClass: string;
  countBadgeClass: string;
  dropRingClass: string;
}

/** Estilo visual de cada coluna de um board kanban de tarefas (ícone,
 * tinta de fundo, badge de contagem, aro ao soltar um cartão) — usado por
 * qualquer tela que renderize tarefas como board de 3 colunas
 * (`PersonalTasksPage`, `ProjectDetailPage`), evitando reconstruir essa
 * paleta em cada uma. */
export const STATUS_COLUMN_STYLE: Record<TaskStatus, StatusColumnStyle> = {
  PENDING: {
    iconWrapperClass: "bg-slate-500/10 text-slate-600 dark:text-slate-400",
    columnTintClass: "bg-slate-50/60 dark:bg-slate-900/10",
    countBadgeClass: "bg-slate-200/70 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    dropRingClass: "ring-slate-400",
  },
  IN_PROGRESS: {
    iconWrapperClass: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
    columnTintClass: "bg-blue-50/50 dark:bg-blue-950/10",
    countBadgeClass: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
    dropRingClass: "ring-blue-400",
  },
  DONE: {
    iconWrapperClass: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    columnTintClass: "bg-emerald-50/50 dark:bg-emerald-950/10",
    countBadgeClass: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
    dropRingClass: "ring-emerald-400",
  },
};
