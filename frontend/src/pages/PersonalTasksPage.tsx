import { useState } from "react";
import { PencilIcon, PlusIcon } from "lucide-react";

import { TaskForm, type TaskFormValues } from "@/components/forms/TaskForm";
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
import type { Task, TaskCreate, TaskUpdate } from "@/types/task";

const STATUS_LABEL: Record<Task["status"], string> = {
  PENDING: "Pendente",
  IN_PROGRESS: "Em andamento",
  DONE: "Concluída",
};

const PRIORITY_LABEL: Record<Task["priority"], string> = {
  LOW: "Baixa",
  MEDIUM: "Média",
  HIGH: "Alta",
  URGENT: "Urgente",
};

const PRIORITY_VARIANT: Record<Task["priority"], "outline" | "secondary" | "destructive"> = {
  LOW: "outline",
  MEDIUM: "secondary",
  HIGH: "destructive",
  URGENT: "destructive",
};

function formatDueDate(dueDate: string): string {
  return new Date(`${dueDate}T00:00:00`).toLocaleDateString("pt-BR");
}

export function PersonalTasksPage() {
  const { tasks, isLoading, error, createTask, updateTask } = usePersonalTasks();
  const [formOpen, setFormOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);

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

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Minhas tarefas</h1>
          <p className="text-sm text-muted-foreground">
            Gerencie suas tarefas pessoais: crie, edite e acompanhe o status.
          </p>
        </div>
        <Button onClick={openCreateForm}>
          <PlusIcon />
          Nova tarefa
        </Button>
      </div>

      {isLoading && (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      )}

      {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

      {!isLoading && !error && tasks.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Você ainda não tem tarefas pessoais. Crie a primeira clicando em &quot;Nova
          tarefa&quot;.
        </p>
      )}

      {!isLoading && !error && tasks.length > 0 && (
        <ul className="flex flex-col gap-2">
          {tasks.map((task) => (
            <li key={task.id} className="flex items-center gap-3 rounded-lg border p-3">
              <Checkbox
                checked={task.status === "DONE"}
                onCheckedChange={() => toggleDone(task)}
                aria-label={
                  task.status === "DONE" ? "Marcar como pendente" : "Marcar como concluída"
                }
              />
              <div className="flex-1">
                <p
                  className={
                    task.status === "DONE"
                      ? "text-sm font-medium text-muted-foreground line-through"
                      : "text-sm font-medium"
                  }
                >
                  {task.title}
                </p>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <Badge variant="outline">{STATUS_LABEL[task.status]}</Badge>
                  <Badge variant={PRIORITY_VARIANT[task.priority]}>
                    {PRIORITY_LABEL[task.priority]}
                  </Badge>
                  {task.due_date && (
                    <span className="text-xs text-muted-foreground">
                      Prazo: {formatDueDate(task.due_date)}
                    </span>
                  )}
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => openEditForm(task)}
                aria-label="Editar tarefa"
              >
                <PencilIcon />
              </Button>
            </li>
          ))}
        </ul>
      )}

      <Sheet open={formOpen} onOpenChange={setFormOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>{editingTask ? "Editar tarefa" : "Nova tarefa"}</SheetTitle>
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
