import { CheckCircle2, Circle, PencilIcon, PlusIcon, Repeat, Trash2 } from "lucide-react";
import { useState } from "react";

import { RecurringTaskForm, type RecurringTaskFormValues } from "@/components/forms/RecurringTaskForm";
import { PageHeader } from "@/components/layout/PageHeader";
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
import type { RecurringTask } from "@/types/recurringTask";

/** `date.weekday()` do Python: 0 = segunda ... 6 = domingo — mesma
 * convenção usada em `RecurringTaskForm`. */
const WEEKDAY_SHORT_LABEL: Record<number, string> = {
  0: "seg",
  1: "ter",
  2: "qua",
  3: "qui",
  4: "sex",
  5: "sáb",
  6: "dom",
};

function describeRecurrence(recurringTask: RecurringTask): string {
  if (recurringTask.recurrence_type === "DAILY") return "Todo dia";
  if (recurringTask.recurrence_type === "WEEKLY") {
    return recurringTask.weekdays.map((day) => WEEKDAY_SHORT_LABEL[day]).join(", ");
  }
  return `Todo dia ${recurringTask.month_day}`;
}

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

function RecurringTaskRow({ recurringTask, onToggle, onEdit, onRemove }: RecurringTaskRowProps) {
  const [isToggling, setIsToggling] = useState(false);

  async function handleToggle() {
    setIsToggling(true);
    try {
      await onToggle();
    } finally {
      setIsToggling(false);
    }
  }

  return (
    <div className="flex items-center gap-3 rounded-xl border bg-card p-3">
      <button
        type="button"
        onClick={() => void handleToggle()}
        disabled={!recurringTask.is_due_today || isToggling}
        aria-label={recurringTask.completed_today ? "Marcar como pendente" : "Marcar como concluída"}
        className="shrink-0 disabled:cursor-not-allowed disabled:opacity-30"
      >
        {recurringTask.completed_today ? (
          <CheckCircle2 className="size-6 text-emerald-500" />
        ) : (
          <Circle className="size-6 text-muted-foreground" />
        )}
      </button>
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "truncate text-sm font-medium",
            recurringTask.completed_today && "text-muted-foreground line-through",
          )}
        >
          {recurringTask.title}
        </p>
        <p className="flex items-center gap-1 truncate text-xs text-muted-foreground">
          <Repeat className="size-3" />
          {describeRecurrence(recurringTask)}
          {!recurringTask.is_due_today && " · não é hoje"}
        </p>
      </div>
      <Button variant="ghost" size="icon-sm" aria-label={`Editar ${recurringTask.title}`} onClick={onEdit}>
        <PencilIcon className="size-4" />
      </Button>
      <RemoveRecurringTaskDialog title={recurringTask.title} onConfirm={onRemove} />
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

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon={Repeat}
        title="Tarefas Fixas"
        description="Rotinas que se repetem sozinhas — diária, semanal ou mensal."
      />

      <div className="flex justify-end">
        <Button
          onClick={openCreateForm}
          className="h-10 gap-1.5 rounded-lg bg-blue-600 px-5 text-sm text-white shadow-sm shadow-blue-600/20 hover:bg-blue-500"
        >
          <PlusIcon className="size-4" />
          Nova tarefa fixa
        </Button>
      </div>

      {isLoading && (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
        </div>
      )}

      {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

      {!isLoading && !error && recurringTasks.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed py-16 text-center">
          <p className="text-sm text-muted-foreground">
            Você ainda não tem tarefas fixas. Crie a primeira clicando em &quot;Nova tarefa
            fixa&quot;.
          </p>
        </div>
      )}

      {!isLoading && !error && recurringTasks.length > 0 && (
        <div className="flex flex-col gap-2">
          {recurringTasks.map((recurringTask) => (
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
