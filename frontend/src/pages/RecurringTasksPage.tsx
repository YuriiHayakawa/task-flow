import {
  CalendarClock,
  CalendarDays,
  CheckCircle2,
  Circle,
  PencilIcon,
  PlusIcon,
  Repeat,
  Sun,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

import { RecurringTaskForm, type RecurringTaskFormValues } from "@/components/forms/RecurringTaskForm";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useRecurringTasks } from "@/hooks/useRecurringTasks";
import { cn } from "@/lib/utils";
import type { RecurrenceType, RecurringTask } from "@/types/recurringTask";

/** `date.weekday()` do Python: 0 = segunda ... 6 = domingo — mesma
 * convenção usada em `RecurringTaskForm`. Mesmos rótulos de 3 letras do
 * seletor do formulário (`WEEKDAY_OPTIONS`), para o vocabulário não mudar
 * entre criar e visualizar. */
const WEEKDAY_SHORT_LABEL: Record<number, string> = {
  0: "Seg",
  1: "Ter",
  2: "Qua",
  3: "Qui",
  4: "Sex",
  5: "Sáb",
  6: "Dom",
};

interface RecurrenceStyle {
  label: string;
  icon: LucideIcon;
  borderClass: string;
  badgeClass: string;
  chipClass: string;
  heroChipClass: string;
}

/** Identidade visual própria por padrão de recorrência — mesma linguagem de
 * "cor com significado" já usada em prioridade/status nas tarefas normais
 * (`PersonalTasksPage`), aqui reaproveitada para diferenciar diária/semanal/
 * mensal à primeira vista, sem precisar ler o texto. */
const RECURRENCE_STYLE: Record<RecurrenceType, RecurrenceStyle> = {
  DAILY: {
    label: "Diária",
    icon: Sun,
    borderClass: "border-l-blue-400",
    badgeClass: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
    chipClass: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
    heroChipClass: "bg-blue-400/15 text-blue-300",
  },
  WEEKLY: {
    label: "Semanal",
    icon: CalendarDays,
    borderClass: "border-l-violet-400",
    badgeClass: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
    chipClass: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
    heroChipClass: "bg-violet-400/15 text-violet-300",
  },
  MONTHLY: {
    label: "Mensal",
    icon: CalendarClock,
    borderClass: "border-l-amber-400",
    badgeClass: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
    chipClass: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
    heroChipClass: "bg-amber-400/15 text-amber-300",
  },
};

interface RemoveRecurringTaskDialogProps {
  title: string;
  onConfirm: () => Promise<void>;
}

function RemoveRecurringTaskDialog({ title, onConfirm }: RemoveRecurringTaskDialogProps) {
  const [isRemoving, setIsRemoving] = useState(false);

  async function handleConfirm() {
    setIsRemoving(true);
    try {
      await onConfirm();
    } finally {
      setIsRemoving(false);
    }
  }

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label={`Excluir ${title}`}>
          <Trash2 className="size-4 text-destructive" />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Excluir "{title}"?</AlertDialogTitle>
          <AlertDialogDescription>
            Remove a tarefa fixa e todo o histórico de conclusões associado. Não é possível desfazer.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isRemoving}>Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} disabled={isRemoving} variant="destructive">
            {isRemoving ? "Excluindo..." : "Excluir"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

interface RecurringTaskRowProps {
  recurringTask: RecurringTask;
  onToggle: () => Promise<void>;
  onEdit: () => void;
  onRemove: () => Promise<void>;
}

/** Cartão com borda lateral colorida por tipo de recorrência (mesma
 * linguagem visual do `TaskCard` do kanban) — o rótulo de tipo e o detalhe
 * (dias da semana/dia do mês) viram chips, não mais um texto corrido. */
function RecurringTaskRow({ recurringTask, onToggle, onEdit, onRemove }: RecurringTaskRowProps) {
  const [isToggling, setIsToggling] = useState(false);
  const style = RECURRENCE_STYLE[recurringTask.recurrence_type];
  const Icon = style.icon;
  const isDone = recurringTask.completed_today;
  const isDue = recurringTask.is_due_today;

  async function handleToggle() {
    setIsToggling(true);
    try {
      await onToggle();
    } finally {
      setIsToggling(false);
    }
  }

  return (
    <div
      className={cn(
        "group flex items-center gap-3 rounded-xl border border-l-4 bg-card p-3 shadow-sm transition-all duration-200",
        style.borderClass,
        isDue ? "hover:-translate-y-0.5 hover:shadow-md" : "opacity-70",
      )}
    >
      <button
        type="button"
        onClick={() => void handleToggle()}
        disabled={!isDue || isToggling}
        aria-label={isDone ? "Marcar como pendente" : "Marcar como concluída"}
        className="shrink-0 disabled:cursor-not-allowed disabled:opacity-30"
      >
        {isDone ? (
          <CheckCircle2 className="size-6 text-emerald-500" />
        ) : (
          <Circle className="size-6 text-muted-foreground transition-colors group-hover:text-foreground/60" />
        )}
      </button>

      <div className={cn("flex size-8 shrink-0 items-center justify-center rounded-lg", style.badgeClass)}>
        <Icon className="size-4" />
      </div>

      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "truncate text-sm font-medium",
            isDone && "text-muted-foreground line-through",
          )}
        >
          {recurringTask.title}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-1">
          <span
            className={cn(
              "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium",
              style.chipClass,
            )}
          >
            {style.label}
          </span>
          {recurringTask.recurrence_type === "WEEKLY" &&
            recurringTask.weekdays.map((day) => (
              <span
                key={day}
                className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium",
                  style.chipClass,
                )}
              >
                {WEEKDAY_SHORT_LABEL[day]}
              </span>
            ))}
          {recurringTask.recurrence_type === "MONTHLY" && (
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium",
                style.chipClass,
              )}
            >
              Dia {recurringTask.month_day}
            </span>
          )}
          {!isDue && <span className="px-1 text-[11px] text-muted-foreground">não é hoje</span>}
        </div>
      </div>

      <Button variant="ghost" size="icon-sm" aria-label={`Editar ${recurringTask.title}`} onClick={onEdit}>
        <PencilIcon className="size-4" />
      </Button>
      <RemoveRecurringTaskDialog title={recurringTask.title} onConfirm={onRemove} />
    </div>
  );
}

interface RecurringTasksHeroProps {
  dueTodayCount: number;
  completedTodayCount: number;
  dailyCount: number;
  weeklyCount: number;
  monthlyCount: number;
  total: number;
  onCreate: () => void;
}

function pluralizeRecurrenceCount(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

/** Cabeçalho próprio, mesma identidade visual do `TasksHero` de "Minhas
 * tarefas" (fundo azul-marinho, malha de pontos, blobs) — sem reaproveitar
 * o trilho animado das 3 colunas do kanban: aqui não existe pipeline de
 * status, cada ocorrência é só pendente/concluída, então o resumo é uma
 * barra de progresso simples ("concluídas hoje") em vez da bolinha
 * viajando entre estágios. */
function RecurringTasksHero({
  dueTodayCount,
  completedTodayCount,
  dailyCount,
  weeklyCount,
  monthlyCount,
  total,
  onCreate,
}: RecurringTasksHeroProps) {
  const progressPercent = dueTodayCount > 0 ? Math.round((completedTodayCount / dueTodayCount) * 100) : 0;

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0b1220] via-[#0a0f1e] to-[#05070f] p-5 shadow-xl shadow-black/20 sm:p-6">
      <div className="blob-drift-a pointer-events-none absolute -top-20 -left-14 size-56 rounded-full bg-violet-600/25 blur-[80px]" />
      <div className="blob-drift-b pointer-events-none absolute -right-16 -bottom-20 size-64 rounded-full bg-blue-500/20 blur-[90px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] bg-[size:32px_32px]" />
      <Repeat
        className="pointer-events-none absolute -right-8 -bottom-10 size-44 -rotate-12 text-blue-500/[0.06]"
        strokeWidth={1}
      />

      <div className="relative flex flex-col gap-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="relative flex size-10 shrink-0 items-center justify-center">
              <div className="absolute inset-0 rounded-xl bg-blue-500/30 blur-md" />
              <div className="relative flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-400 to-blue-700 shadow-lg shadow-blue-900/40">
                <Repeat className="size-5 text-white" strokeWidth={2.25} />
              </div>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
                Tarefas Fixas
              </h1>
              <p className="text-xs text-slate-400 sm:text-sm">
                Rotinas que se repetem sozinhas — diária, semanal ou mensal.
              </p>
            </div>
          </div>
          <Button
            onClick={onCreate}
            className="h-10 w-fit gap-1.5 rounded-xl bg-white px-4 text-sm font-semibold text-[#05070f] shadow-lg shadow-black/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-xl hover:shadow-blue-500/10"
          >
            <PlusIcon className="size-4" />
            Nova tarefa fixa
          </Button>
        </div>

        {total > 0 && (
          <div className="flex flex-col gap-3 border-t border-white/10 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-1 flex-col gap-2">
              <div className="flex items-center gap-2.5">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-blue-400/15">
                  <CheckCircle2 className="size-4 text-blue-300" />
                </div>
                <div className="leading-tight">
                  <p className="text-xl font-bold tabular-nums text-white">
                    {completedTodayCount}
                    <span className="text-slate-500">/{dueTodayCount}</span>
                  </p>
                  <p className="text-[11px] font-medium text-slate-400">Concluídas hoje</p>
                </div>
              </div>
              {dueTodayCount > 0 && (
                <div className="h-1.5 w-full max-w-56 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-400 to-blue-600 transition-all duration-500"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              )}
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-1.5">
              {dailyCount > 0 && (
                <span
                  className={cn(
                    "rounded-full px-2.5 py-1 text-[11px] font-semibold tabular-nums",
                    RECURRENCE_STYLE.DAILY.heroChipClass,
                  )}
                >
                  {pluralizeRecurrenceCount(dailyCount, "diária", "diárias")}
                </span>
              )}
              {weeklyCount > 0 && (
                <span
                  className={cn(
                    "rounded-full px-2.5 py-1 text-[11px] font-semibold tabular-nums",
                    RECURRENCE_STYLE.WEEKLY.heroChipClass,
                  )}
                >
                  {pluralizeRecurrenceCount(weeklyCount, "semanal", "semanais")}
                </span>
              )}
              {monthlyCount > 0 && (
                <span
                  className={cn(
                    "rounded-full px-2.5 py-1 text-[11px] font-semibold tabular-nums",
                    RECURRENCE_STYLE.MONTHLY.heroChipClass,
                  )}
                >
                  {pluralizeRecurrenceCount(monthlyCount, "mensal", "mensais")}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function RecurringTasksPage() {
  const {
    recurringTasks,
    isLoading,
    error,
    createRecurringTask,
    updateRecurringTask,
    removeRecurringTask,
    toggleToday,
  } = useRecurringTasks();
  const [formOpen, setFormOpen] = useState(false);
  const [editingRecurringTask, setEditingRecurringTask] = useState<RecurringTask | null>(null);

  function openCreateForm() {
    setEditingRecurringTask(null);
    setFormOpen(true);
  }

  function openEditForm(recurringTask: RecurringTask) {
    setEditingRecurringTask(recurringTask);
    setFormOpen(true);
  }

  async function handleSubmit(values: RecurringTaskFormValues) {
    if (editingRecurringTask) {
      await updateRecurringTask(editingRecurringTask.id, values);
    } else {
      await createRecurringTask(values);
    }
    setFormOpen(false);
  }

  const total = recurringTasks.length;
  const dueTodayCount = recurringTasks.filter((task) => task.is_due_today).length;
  const completedTodayCount = recurringTasks.filter(
    (task) => task.is_due_today && task.completed_today,
  ).length;
  const dailyCount = recurringTasks.filter((task) => task.recurrence_type === "DAILY").length;
  const weeklyCount = recurringTasks.filter((task) => task.recurrence_type === "WEEKLY").length;
  const monthlyCount = recurringTasks.filter((task) => task.recurrence_type === "MONTHLY").length;

  // Ocorrências de hoje primeiro (pendentes antes de concluídas), depois o
  // resto — quem exige ação do usuário agora fica sempre no topo.
  const sortedRecurringTasks = [...recurringTasks].sort((a, b) => {
    if (a.is_due_today !== b.is_due_today) return a.is_due_today ? -1 : 1;
    if (a.completed_today !== b.completed_today) return a.completed_today ? 1 : -1;
    return 0;
  });

  return (
    <div className="flex flex-col gap-5">
      <RecurringTasksHero
        dueTodayCount={dueTodayCount}
        completedTodayCount={completedTodayCount}
        dailyCount={dailyCount}
        weeklyCount={weeklyCount}
        monthlyCount={monthlyCount}
        total={total}
        onCreate={openCreateForm}
      />

      {isLoading && (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
        </div>
      )}

      {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

      {!isLoading && !error && recurringTasks.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed py-16 text-center">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-blue-500/10">
            <Repeat className="size-7 text-blue-500/60" strokeWidth={1.5} />
          </div>
          <p className="max-w-xs text-sm text-muted-foreground">
            Você ainda não tem tarefas fixas. Crie a primeira clicando em &quot;Nova tarefa
            fixa&quot;.
          </p>
        </div>
      )}

      {!isLoading && !error && recurringTasks.length > 0 && (
        <div className="flex flex-col gap-2">
          {sortedRecurringTasks.map((recurringTask) => (
            <RecurringTaskRow
              key={recurringTask.id}
              recurringTask={recurringTask}
              onToggle={() => toggleToday(recurringTask)}
              onEdit={() => openEditForm(recurringTask)}
              onRemove={() => removeRecurringTask(recurringTask.id)}
            />
          ))}
        </div>
      )}

      <Sheet open={formOpen} onOpenChange={setFormOpen}>
        <SheetContent>
          <SheetHeader>
            <div className="flex items-center gap-2.5">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/20">
                {editingRecurringTask ? (
                  <PencilIcon className="size-4 text-white" />
                ) : (
                  <PlusIcon className="size-4 text-white" />
                )}
              </div>
              <SheetTitle>
                {editingRecurringTask ? "Editar tarefa fixa" : "Nova tarefa fixa"}
              </SheetTitle>
            </div>
          </SheetHeader>
          <div className="px-4 pb-4">
            <RecurringTaskForm
              key={editingRecurringTask?.id ?? "new"}
              recurringTask={editingRecurringTask ?? undefined}
              onSubmit={handleSubmit}
              onCancel={() => setFormOpen(false)}
            />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
