import { useState, type DragEvent } from "react";
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Circle,
  CircleDot,
  Flag,
  GripVertical,
  ListTodo,
  PlusIcon,
  type LucideIcon,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { TaskForm, type TaskFormValues } from "@/components/forms/TaskForm";
import { TasksTabs } from "@/components/layout/TasksTabs";
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
import type { Task, TaskCreate, TaskStatus } from "@/types/task";

/** Mesma linguagem visual do restante do produto: os ícones de status
 * reaproveitam exatamente os do Dashboard (`Circle`/`CircleDot`/
 * `CheckCircle2`), e a paleta reaproveita o mockup do board kanban da
 * tela de login (`BrandPanel`) — cada coluna é uma "esteira" com
 * identidade própria (tinta sutil de fundo, friso no topo, aro de
 * destaque ao soltar um cartão), não apenas uma caixa neutra. */
const COLUMNS: {
  status: TaskStatus;
  label: string;
  icon: LucideIcon;
  iconWrapperClass: string;
  columnTintClass: string;
  accentClass: string;
  countBadgeClass: string;
  dropRingClass: string;
}[] = [
  {
    status: "PENDING",
    label: "Pendente",
    icon: Circle,
    iconWrapperClass: "bg-slate-500/10 text-slate-600 dark:text-slate-400",
    columnTintClass: "bg-slate-50/60 dark:bg-slate-900/10",
    accentClass: "bg-slate-400",
    countBadgeClass: "bg-slate-200/70 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    dropRingClass: "ring-slate-400",
  },
  {
    status: "IN_PROGRESS",
    label: "Em andamento",
    icon: CircleDot,
    iconWrapperClass: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
    columnTintClass: "bg-blue-50/50 dark:bg-blue-950/10",
    accentClass: "bg-blue-500",
    countBadgeClass: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
    dropRingClass: "ring-blue-400",
  },
  {
    status: "DONE",
    label: "Concluída",
    icon: CheckCircle2,
    iconWrapperClass: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    columnTintClass: "bg-emerald-50/50 dark:bg-emerald-950/10",
    accentClass: "bg-emerald-500",
    countBadgeClass: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
    dropRingClass: "ring-emerald-400",
  },
];

const PRIORITY_LABEL: Record<Task["priority"], string> = {
  LOW: "Baixa",
  MEDIUM: "Média",
  HIGH: "Alta",
  URGENT: "Urgente",
};

/** Chips sólidos (não apenas contorno) — mais vivos que o badge outline
 * anterior, mesma paleta usada nos toggles de prioridade do `TaskForm`. */
const PRIORITY_CHIP_CLASS: Record<Task["priority"], string> = {
  LOW: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  MEDIUM: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  HIGH: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  URGENT: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
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

const DUE_CHIP_CLASS: Record<DueInfo["tone"], string> = {
  neutral: "bg-muted text-muted-foreground",
  warning: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400",
  danger: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
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
  index: number;
  isDragging: boolean;
  onOpen: () => void;
  onToggleDone: () => void;
  onDragStart: (event: DragEvent<HTMLDivElement>) => void;
  onDragEnd: () => void;
}

/** Cartão inteiro é clicável (abre a página de detalhes da tarefa,
 * `/tasks/{id}` — mesma usada em Workspace/Projeto), exceto o checkbox
 * (`stopPropagation`, que só alterna concluída/pendente sem navegar). Não é
 * um `<button>` nativo porque o `Checkbox` do Radix já é um botão por
 * dentro — botão dentro de botão é HTML inválido — então usa `role="button"`
 * + teclado (Enter/Espaço) para manter acessibilidade sem essa limitação. */
function TaskCard({ task, index, isDragging, onOpen, onToggleDone, onDragStart, onDragEnd }: TaskCardProps) {
  const due = task.due_date ? describeDueDate(task.due_date, task.status === "DONE") : null;
  const isDone = task.status === "DONE";

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen();
        }
      }}
      style={{ animationDelay: `${Math.min(index * 40, 200)}ms` }}
      className={cn(
        "group animate-in fade-in slide-in-from-bottom-1 flex cursor-grab flex-col gap-2 rounded-xl border border-l-4 bg-card p-3 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md active:cursor-grabbing",
        PRIORITY_BORDER_CLASS[task.priority],
        isDragging && "rotate-2 opacity-40 shadow-lg",
      )}
    >
      <div className="flex items-start gap-1">
        <GripVertical className="mt-1.5 size-3.5 shrink-0 text-transparent transition-colors group-hover:text-muted-foreground/40" />
        <span onClick={(event) => event.stopPropagation()}>
          <Checkbox
            checked={isDone}
            onCheckedChange={onToggleDone}
            aria-label={isDone ? "Marcar como pendente" : "Marcar como concluída"}
            className="mt-0.5"
          />
        </span>
        <p
          className={cn(
            "flex-1 text-sm font-medium",
            isDone && "text-muted-foreground line-through",
          )}
        >
          {task.title}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-1.5 pl-9">
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
            PRIORITY_CHIP_CLASS[task.priority],
          )}
        >
          <Flag className="size-2.5" />
          {PRIORITY_LABEL[task.priority]}
        </span>
        {due && (
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
              DUE_CHIP_CLASS[due.tone],
            )}
          >
            {due.tone === "danger" ? (
              <AlertTriangle className="size-2.5" />
            ) : (
              <Calendar className="size-2.5" />
            )}
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
  icon: LucideIcon;
  iconWrapperClass: string;
  columnTintClass: string;
  accentClass: string;
  countBadgeClass: string;
  dropRingClass: string;
  tasks: Task[];
  draggingId: string | null;
  onOpenTask: (task: Task) => void;
  onToggleDone: (task: Task) => void;
  onDragStartTask: (taskId: string) => (event: DragEvent<HTMLDivElement>) => void;
  onDragEndTask: () => void;
  onDropTask: (taskId: string, status: TaskStatus) => void;
}

function TaskColumn({
  status,
  label,
  icon: Icon,
  iconWrapperClass,
  columnTintClass,
  accentClass,
  countBadgeClass,
  dropRingClass,
  tasks,
  draggingId,
  onOpenTask,
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
        "relative flex min-h-64 flex-col gap-3 overflow-hidden rounded-2xl border p-3 pt-4 transition-all",
        columnTintClass,
        isOver ? cn("border-transparent ring-2", dropRingClass) : "border-border",
      )}
    >
      <div className={cn("absolute inset-x-0 top-0 h-1", accentClass)} />

      <div className="flex items-center gap-2">
        <div className={cn("flex size-7 shrink-0 items-center justify-center rounded-lg", iconWrapperClass)}>
          <Icon className="size-4" />
        </div>
        <span className="text-sm font-semibold">{label}</span>
        <span
          className={cn(
            "ml-auto flex size-5 items-center justify-center rounded-full text-[11px] font-semibold tabular-nums",
            countBadgeClass,
          )}
        >
          {tasks.length}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-2">
        {tasks.length === 0 && (
          <div className="mt-6 flex flex-col items-center gap-1.5 text-center">
            <Icon className="size-6 text-muted-foreground/25" strokeWidth={1.5} />
            <p className="text-xs text-muted-foreground">Nenhuma tarefa aqui</p>
          </div>
        )}
        {tasks.map((task, index) => (
          <TaskCard
            key={task.id}
            task={task}
            index={index}
            isDragging={draggingId === task.id}
            onOpen={() => onOpenTask(task)}
            onToggleDone={() => onToggleDone(task)}
            onDragStart={onDragStartTask(task.id)}
            onDragEnd={onDragEndTask}
          />
        ))}
      </div>
    </div>
  );
}

interface FlowStageProps {
  icon: LucideIcon;
  label: string;
  count: number;
  iconClass: string;
  badgeClass: string;
}

/** Ícone junto da frase (lado a lado, sem linha/animação de trilho — tirada
 * por ficar estranha cruzando o texto) — número em destaque de verdade
 * (`text-xl`, a maior peça de texto do bloco todo), rótulo pequeno embaixo. */
function FlowStage({ icon: Icon, label, count, iconClass, badgeClass }: FlowStageProps) {
  return (
    <div className="flex items-center gap-2.5">
      <div className={cn("flex size-9 shrink-0 items-center justify-center rounded-full", badgeClass)}>
        <Icon className={cn("size-4", iconClass)} />
      </div>
      <div className="leading-tight">
        <p className="text-xl font-bold tabular-nums text-white">{count}</p>
        <p className="text-[11px] font-medium text-slate-400">{label}</p>
      </div>
    </div>
  );
}

interface TasksHeroProps {
  pendingCount: number;
  inProgressCount: number;
  doneCount: number;
  total: number;
  progressPercent: number;
  onCreate: () => void;
}

/** Cabeçalho próprio de "Minhas tarefas" — reconstruído do zero (não
 * reaproveita `PageHeader`, genérico demais para a tela mais visitada do
 * produto). Traz para dentro do app a identidade "TaskFlow" que hoje só
 * aparece na tela pública (`BrandPanel`, tela de login): fundo azul-marinho,
 * malha de pontos, blobs — e a MESMA animação do ponto viajando pelas
 * colunas do mini kanban do login (classes `kanban-token`/`kanban-flow` de
 * `global.css`, reaproveitadas tal qual, sem CSS novo), só que agora sobre
 * uma trilha com as contagens REAIS do usuário (Pendente/Em andamento/
 * Concluída) em vez de um mockup decorativo — a "prévia viva" do board
 * kanban logo abaixo. */
function TasksHero({
  pendingCount,
  inProgressCount,
  doneCount,
  total,
  progressPercent,
  onCreate,
}: TasksHeroProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0b1220] via-[#0a0f1e] to-[#05070f] p-5 shadow-xl shadow-black/20 sm:p-6">
      <div className="blob-drift-a pointer-events-none absolute -top-20 -left-14 size-56 rounded-full bg-blue-600/25 blur-[80px]" />
      <div className="blob-drift-b pointer-events-none absolute -right-16 -bottom-20 size-64 rounded-full bg-indigo-500/20 blur-[90px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] bg-[size:32px_32px]" />
      <ListTodo
        className="pointer-events-none absolute -right-8 -bottom-10 size-44 -rotate-12 text-blue-500/[0.06]"
        strokeWidth={1}
      />

      <div className="relative flex flex-col gap-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="relative flex size-10 shrink-0 items-center justify-center">
              <div className="absolute inset-0 rounded-xl bg-blue-500/30 blur-md" />
              <div className="relative flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-400 to-blue-700 shadow-lg shadow-blue-900/40">
                <ListTodo className="size-5 text-white" strokeWidth={2.25} />
              </div>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
                Minhas tarefas
              </h1>
              <p className="text-xs text-slate-400 sm:text-sm">
                Arraste os cartões entre as colunas para atualizar o status.
              </p>
            </div>
          </div>
          <Button
            onClick={onCreate}
            className="h-10 w-fit gap-1.5 rounded-xl bg-white px-4 text-sm font-semibold text-[#05070f] shadow-lg shadow-black/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-xl hover:shadow-blue-500/10"
          >
            <PlusIcon className="size-4" />
            Nova tarefa
          </Button>
        </div>

        {total > 0 && (
          <div className="flex flex-col gap-3 border-t border-white/10 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-1 flex-col gap-2.5">
              {/* Trilho numa faixa própria — nunca sobrepõe ícone nem texto
                 dos indicadores abaixo, só "flutua" conectando os três,
                 alinhado às mesmas 3 colunas (16,6% / 50% / 83,3%, mesma
                 matemática do mini kanban do login). */}
              <div className="relative h-1.5">
                <div className="pointer-events-none absolute inset-x-[16.6%] top-1/2 h-px -translate-y-1/2 bg-gradient-to-r from-slate-500/0 via-white/25 to-slate-500/0" />
                <span className="kanban-token pointer-events-none absolute top-1/2 size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-400 shadow-[0_0_10px_2px_rgba(96,165,250,0.6)]" />
              </div>
              <div className="grid grid-cols-3 justify-items-center gap-2">
                <FlowStage
                  icon={Circle}
                  label="Pendente"
                  count={pendingCount}
                  iconClass="text-slate-300"
                  badgeClass="bg-slate-400/15"
                />
                <FlowStage
                  icon={CircleDot}
                  label="Em andamento"
                  count={inProgressCount}
                  iconClass="text-blue-300"
                  badgeClass="bg-blue-400/15"
                />
                <FlowStage
                  icon={CheckCircle2}
                  label="Concluída"
                  count={doneCount}
                  iconClass="text-emerald-300"
                  badgeClass="bg-emerald-400/15"
                />
              </div>
            </div>
            <p className="shrink-0 text-xs font-medium text-slate-400 sm:text-right">
              <span className="text-sm font-bold text-white">{progressPercent}%</span> concluído ·{" "}
              {doneCount} de {total}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export function PersonalTasksPage() {
  const navigate = useNavigate();
  const { tasks, isLoading, error, createTask, updateTask } = usePersonalTasks();
  const [formOpen, setFormOpen] = useState(false);
  const [draggingId, setDraggingId] = useState<string | null>(null);

  function openCreateForm() {
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
    await createTask(payload satisfies TaskCreate);
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
  const pendingCount = tasks.filter((task) => task.status === "PENDING").length;
  const inProgressCount = tasks.filter((task) => task.status === "IN_PROGRESS").length;
  const doneCount = tasks.filter((task) => task.status === "DONE").length;
  const progressPercent = total > 0 ? Math.round((doneCount / total) * 100) : 0;

  return (
    <div className="flex flex-col gap-5">
      <TasksTabs />

      <TasksHero
        pendingCount={pendingCount}
        inProgressCount={inProgressCount}
        doneCount={doneCount}
        total={total}
        progressPercent={progressPercent}
        onCreate={openCreateForm}
      />

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
              icon={column.icon}
              iconWrapperClass={column.iconWrapperClass}
              columnTintClass={column.columnTintClass}
              accentClass={column.accentClass}
              countBadgeClass={column.countBadgeClass}
              dropRingClass={column.dropRingClass}
              tasks={tasks.filter((task) => task.status === column.status)}
              draggingId={draggingId}
              onOpenTask={(task) => navigate(`/tasks/${task.id}`)}
              onToggleDone={toggleDone}
              onDragStartTask={handleDragStartTask}
              onDragEndTask={() => setDraggingId(null)}
              onDropTask={handleDropTask}
            />
          ))}
        </div>
      )}

      {/* Edição de tarefa existente acontece na página de detalhes
         (`/tasks/{id}`, botão "Editar") — este Sheet fica só para criação,
         mesma divisão de responsabilidade já usada em Workspace/Projeto. */}
      <Sheet open={formOpen} onOpenChange={setFormOpen}>
        <SheetContent>
          <SheetHeader>
            <div className="flex items-center gap-2.5">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/20">
                <PlusIcon className="size-4 text-white" />
              </div>
              <SheetTitle>Nova tarefa</SheetTitle>
            </div>
          </SheetHeader>
          <div className="px-4 pb-4">
            <TaskForm onSubmit={handleSubmit} onCancel={() => setFormOpen(false)} />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
