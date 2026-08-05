import { useState, type DragEvent } from "react";
import { AlertTriangle, ListTodo, PencilIcon, PlusIcon } from "lucide-react";

import { TaskForm, type TaskFormValues } from "@/components/forms/TaskForm";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { usePersonalTasks } from "@/hooks/usePersonalTasks";
import { cn } from "@/lib/utils";
import type { Task, TaskCreate, TaskStatus, TaskUpdate } from "@/types/task";

/** Mesma paleta de status usada no mockup do board kanban da tela de
 * login (`BrandPanel`) — fecha o círculo da identidade visual entre a
 * vitrine e o produto real. */
const COLUMNS: { status: TaskStatus; label: string; dotClass: string; headerClass: string }[] = [
  {
    status: "PENDING",
    label: "Pendente",
    dotClass: "bg-slate-500",
    headerClass: "bg-slate-50 dark:bg-slate-900/40",
  },
  {
    status: "IN_PROGRESS",
    label: "Em andamento",
    dotClass: "bg-blue-500",
    headerClass: "bg-blue-50 dark:bg-blue-950/30",
  },
  {
    status: "DONE",
    label: "Concluída",
    dotClass: "bg-emerald-500",
    headerClass: "bg-emerald-50 dark:bg-emerald-950/30",
  },
];

const PRIORITY_LABEL: Record<Task["priority"], string> = {
  LOW: "Baixa",
  MEDIUM: "Média",
  HIGH: "Alta",
  URGENT: "Urgente",
};

const PRIORITY_BADGE_CLASS: Record<Task["priority"], string> = {
  LOW: "border-slate-300 text-slate-600 dark:border-slate-700 dark:text-slate-400",
  MEDIUM:
    "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400",
  HIGH: "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400",
  URGENT: "border-red-300 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400",
};

const PRIORITY_BORDER_CLASS: Record<Task["priority"], string> = {
  LOW: "border-l-slate-300",
  MEDIUM: "border-l-blue-400",
  HIGH: "border-l-amber-400",
  URGENT: "border-l-red-500",
};

interface DueInfo {
  label: string;
  tone: "neutral" | "warning" | "danger";
}

const DUE_TONE_CLASS: Record<DueInfo["tone"], string> = {
  neutral: "text-muted-foreground",
  warning: "text-amber-600 dark:text-amber-400",
  danger: "text-destructive",
};

/** Rótulo relativo e amigável de prazo — indicador de contexto no cartão,
 * não a fonte oficial de "atrasada"/"vencendo hoje" (essa é o Dashboard,
 * calculado no backend com `APP_TIMEZONE`). */
function describeDueDate(dueDate: string, isDone: boolean): DueInfo {
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

interface TaskCardProps {
  task: Task;
  isDragging: boolean;
  onEdit: () => void;
  onToggleDone: () => void;
  onDragStart: (event: DragEvent<HTMLDivElement>) => void;
  onDragEnd: () => void;
}

function TaskCard({ task, isDragging, onEdit, onToggleDone, onDragStart, onDragEnd }: TaskCardProps) {
  const due = task.due_date ? describeDueDate(task.due_date, task.status === "DONE") : null;

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      className={cn(
        "group flex cursor-grab flex-col gap-2 rounded-lg border border-l-4 bg-card p-3 shadow-sm transition-all hover:shadow-md active:cursor-grabbing",
        PRIORITY_BORDER_CLASS[task.priority],
        isDragging && "opacity-40",
      )}
    >
      <div className="flex items-start gap-2">
        <Checkbox
          checked={task.status === "DONE"}
          onCheckedChange={onToggleDone}
          aria-label={task.status === "DONE" ? "Marcar como pendente" : "Marcar como concluída"}
          className="mt-0.5"
        />
        <p
          className={cn(
            "flex-1 text-sm font-medium",
            task.status === "DONE" && "text-muted-foreground line-through",
          )}
        >
          {task.title}
        </p>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onEdit}
          aria-label="Editar tarefa"
          className="opacity-0 transition-opacity group-hover:opacity-100"
        >
          <PencilIcon />
        </Button>
      </div>
      <div className="flex flex-wrap items-center gap-1.5 pl-6">
        <Badge variant="outline" className={PRIORITY_BADGE_CLASS[task.priority]}>
          {PRIORITY_LABEL[task.priority]}
        </Badge>
        {due && (
          <span className={cn("flex items-center gap-1 text-xs", DUE_TONE_CLASS[due.tone])}>
            {due.tone === "danger" && <AlertTriangle className="size-3" />}
            {due.label}
          </span>
        )}
      </div>
    </div>
  );
}

interface TaskColumnProps {
  status: TaskStatus;
  label: string;
  dotClass: string;
  headerClass: string;
  tasks: Task[];
  draggingId: string | null;
  onEdit: (task: Task) => void;
  onToggleDone: (task: Task) => void;
  onDragStartTask: (taskId: string) => (event: DragEvent<HTMLDivElement>) => void;
  onDragEndTask: () => void;
  onDropTask: (taskId: string, status: TaskStatus) => void;
}

function TaskColumn({
  status,
  label,
  dotClass,
  headerClass,
  tasks,
  draggingId,
  onEdit,
  onToggleDone,
  onDragStartTask,
  onDragEndTask,
  onDropTask,
}: TaskColumnProps) {
  const [isOver, setIsOver] = useState(false);

  return (
    <div
      aria-label={`Coluna ${label}`}
      onDragOver={(event) => {
        event.preventDefault();
        setIsOver(true);
      }}
      onDragLeave={() => setIsOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsOver(false);
        const taskId = event.dataTransfer.getData("text/plain");
        if (taskId) onDropTask(taskId, status);
      }}
      className={cn(
        "flex min-h-64 flex-col gap-3 rounded-xl border p-3 transition-colors",
        isOver ? "border-blue-400 bg-blue-50/50 dark:bg-blue-950/20" : "border-border",
      )}
    >
      <div className={cn("flex items-center gap-2 rounded-lg px-2.5 py-1.5", headerClass)}>
        <span className={cn("size-2 rounded-full", dotClass)} />
        <span className="text-sm font-semibold">{label}</span>
        <span className="ml-auto text-xs text-muted-foreground">{tasks.length}</span>
      </div>

      <div className="flex flex-1 flex-col gap-2">
        {tasks.length === 0 && (
          <p className="mt-4 text-center text-xs text-muted-foreground">Nenhuma tarefa aqui</p>
        )}
        {tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            isDragging={draggingId === task.id}
            onEdit={() => onEdit(task)}
            onToggleDone={() => onToggleDone(task)}
            onDragStart={onDragStartTask(task.id)}
            onDragEnd={onDragEndTask}
          />
        ))}
      </div>
    </div>
  );
}

export function PersonalTasksPage() {
  const { tasks, isLoading, error, createTask, updateTask } = usePersonalTasks();
  const [formOpen, setFormOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);

  function openCreateForm() {
    setEditingTask(null);
    setFormOpen(true);
  }

  function openEditForm(task: Task) {
    setEditingTask(task);
    setFormOpen(true);
  }

  async function handleSubmit(values: TaskFormValues) {
    const payload = {
      title: values.title,
      description: values.description.trim() === "" ? null : values.description,
      status: values.status,
      priority: values.priority,
      due_date: values.due_date === "" ? null : values.due_date,
    };
    if (editingTask) {
      await updateTask(editingTask.id, payload satisfies TaskUpdate);
    } else {
      await createTask(payload satisfies TaskCreate);
    }
    setFormOpen(false);
  }

  async function toggleDone(task: Task) {
    await updateTask(task.id, { status: task.status === "DONE" ? "PENDING" : "DONE" });
  }

  function handleDragStartTask(taskId: string) {
    return (event: DragEvent<HTMLDivElement>) => {
      event.dataTransfer.setData("text/plain", taskId);
      event.dataTransfer.effectAllowed = "move";
      setDraggingId(taskId);
    };
  }

  async function handleDropTask(taskId: string, status: TaskStatus) {
    const task = tasks.find((item) => item.id === taskId);
    if (task && task.status !== status) {
      await updateTask(taskId, { status });
    }
  }

  const total = tasks.length;
  const doneCount = tasks.filter((task) => task.status === "DONE").length;
  const progressPercent = total > 0 ? Math.round((doneCount / total) * 100) : 0;

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon={ListTodo}
        title="Minhas tarefas"
        description="Arraste os cartões entre as colunas para atualizar o status."
      >
        {!isLoading && !error && total > 0 && (
          <div className="flex items-center gap-3">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-400 to-emerald-400 transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <span className="shrink-0 text-xs font-medium text-muted-foreground">
              {doneCount} de {total} concluídas ({progressPercent}%)
            </span>
          </div>
        )}
      </PageHeader>

      <div className="flex justify-end">
        <Button
          onClick={openCreateForm}
          className="h-10 gap-1.5 rounded-lg bg-blue-600 px-5 text-sm text-white shadow-sm shadow-blue-600/20 hover:bg-blue-500"
        >
          <PlusIcon className="size-4" />
          Nova tarefa
        </Button>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}

      {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

      {!isLoading && !error && tasks.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed py-16 text-center">
          <p className="text-sm text-muted-foreground">
            Você ainda não tem tarefas pessoais. Crie a primeira clicando em &quot;Nova
            tarefa&quot;.
          </p>
        </div>
      )}

      {!isLoading && !error && tasks.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {COLUMNS.map((column) => (
            <TaskColumn
              key={column.status}
              status={column.status}
              label={column.label}
              dotClass={column.dotClass}
              headerClass={column.headerClass}
              tasks={tasks.filter((task) => task.status === column.status)}
              draggingId={draggingId}
              onEdit={openEditForm}
              onToggleDone={toggleDone}
              onDragStartTask={handleDragStartTask}
              onDragEndTask={() => setDraggingId(null)}
              onDropTask={handleDropTask}
            />
          ))}
        </div>
      )}

      <Sheet open={formOpen} onOpenChange={setFormOpen}>
        <SheetContent>
          <SheetHeader>
            <div className="flex items-center gap-2.5">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/20">
                {editingTask ? (
                  <PencilIcon className="size-4 text-white" />
                ) : (
                  <PlusIcon className="size-4 text-white" />
                )}
              </div>
              <SheetTitle>{editingTask ? "Editar tarefa" : "Nova tarefa"}</SheetTitle>
            </div>
          </SheetHeader>
          <div className="px-4 pb-4">
            <TaskForm
              key={editingTask?.id ?? "new"}
              task={editingTask ?? undefined}
              onSubmit={handleSubmit}
              onCancel={() => setFormOpen(false)}
            />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
