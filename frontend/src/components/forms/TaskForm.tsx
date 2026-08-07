import { AlignLeft, Calendar, Check, Flag, Type, X } from "lucide-react";
import { useState, type SubmitEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { Task, TaskPriority, TaskStatus } from "@/types/task";

export interface TaskFormValues {
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  /** Formato `yyyy-mm-dd` (input `date`); string vazia quando ausente. */
  due_date: string;
}

/** Mesmas cores das colunas do board kanban — o formulário "conversa"
 * visualmente com a tela onde a tarefa vai aparecer. */
const STATUS_OPTIONS: { value: TaskStatus; label: string; dotClass: string }[] = [
  { value: "PENDING", label: "Pendente", dotClass: "bg-slate-500" },
  { value: "IN_PROGRESS", label: "Em andamento", dotClass: "bg-blue-500" },
  { value: "DONE", label: "Concluída", dotClass: "bg-emerald-500" },
];

const PRIORITY_OPTIONS: { value: TaskPriority; label: string; activeClass: string }[] = [
  {
    value: "LOW",
    label: "Baixa",
    activeClass: "border-slate-400 bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  },
  {
    value: "MEDIUM",
    label: "Média",
    activeClass: "border-blue-400 bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  },
  {
    value: "HIGH",
    label: "Alta",
    activeClass: "border-amber-400 bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  },
  {
    value: "URGENT",
    label: "Urgente",
    activeClass: "border-red-400 bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  },
];

interface TaskFormProps {
  /** Presente em modo de edição; ausente em modo de criação. */
  task?: Task;
  onSubmit: (values: TaskFormValues) => Promise<void>;
  onCancel: () => void;
}

export function TaskForm({ task, onSubmit, onCancel }: TaskFormProps) {
  const [title, setTitle] = useState(task?.title ?? "");
  const [description, setDescription] = useState(task?.description ?? "");
  const [status, setStatus] = useState<TaskStatus>(task?.status ?? "PENDING");
  const [priority, setPriority] = useState<TaskPriority>(task?.priority ?? "MEDIUM");
  const [dueDate, setDueDate] = useState(task?.due_date ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({ title, description, status, priority, due_date: dueDate });
    } catch {
      setError("Não foi possível salvar a tarefa. Tente novamente.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <Label htmlFor="task-title">Título</Label>
        <div className="relative">
          <Type className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="task-title"
            required
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="h-11 rounded-xl pl-9"
            placeholder="Ex.: Preparar apresentação"
          />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="task-description">Descrição</Label>
        <div className="relative">
          <AlignLeft className="pointer-events-none absolute top-3 left-3 size-4 text-muted-foreground" />
          <Textarea
            id="task-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="min-h-24 rounded-xl pl-9"
            placeholder="Detalhes da tarefa (opcional)"
          />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label>Status</Label>
        <div className="grid grid-cols-3 gap-2">
          {STATUS_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setStatus(option.value)}
              className={cn(
                "flex items-center justify-center gap-1.5 rounded-xl border px-2 py-2 text-xs font-medium transition-colors",
                status === option.value
                  ? "border-blue-400 bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                  : "border-border text-muted-foreground hover:bg-muted",
              )}
            >
              <span className={cn("size-1.5 rounded-full", option.dotClass)} />
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label className="flex items-center gap-1.5">
          <Flag className="size-3.5" />
          Prioridade
        </Label>
        <div className="grid grid-cols-4 gap-2">
          {PRIORITY_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setPriority(option.value)}
              className={cn(
                "rounded-xl border px-2 py-2 text-xs font-medium transition-colors",
                priority === option.value
                  ? option.activeClass
                  : "border-border text-muted-foreground hover:bg-muted",
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="task-due-date">Prazo</Label>
        <div className="relative">
          <Calendar className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="task-due-date"
            type="date"
            value={dueDate}
            onChange={(event) => setDueDate(event.target.value)}
            className="h-11 rounded-xl pl-9"
          />
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="mt-2 flex justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={isSubmitting}
          className="rounded-xl"
        >
          <X className="size-4" />
          Cancelar
        </Button>
        <Button
          type="submit"
          disabled={isSubmitting || title.trim() === ""}
          className="rounded-xl bg-blue-600 text-white hover:bg-blue-500"
        >
          <Check className="size-4" />
          {isSubmitting ? "Salvando..." : task ? "Salvar" : "Criar tarefa"}
        </Button>
      </div>
    </form>
  );
}
