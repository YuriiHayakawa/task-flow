import {
  AlertTriangle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Circle,
  CircleDot,
  FolderKanban,
  GripVertical,
  PencilIcon,
  PlusIcon,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import { useState, type DragEvent } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";

import { ProjectForm, type ProjectFormValues } from "@/components/forms/ProjectForm";
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
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useProject } from "@/hooks/useProject";
import { useTasks } from "@/hooks/useTasks";
import { useWorkspace } from "@/hooks/useWorkspace";
import { useWorkspaceMembers } from "@/hooks/useWorkspaceMembers";
import { cn } from "@/lib/utils";
import type { Project, ProjectUpdate } from "@/types/project";
import type { Task, TaskStatus } from "@/types/task";
import { pickAccentColor } from "@/utils/accentColor";
import { getInitials } from "@/utils/initials";
import {
  DUE_CHIP_CLASS,
  PRIORITY_BORDER_CLASS,
  PRIORITY_CHIP_CLASS,
  PRIORITY_LABEL,
  STATUS_ACCENT_CLASS,
  STATUS_COLUMN_STYLE,
  STATUS_ICON,
  STATUS_LABEL,
  describeDueDate,
} from "@/utils/taskStyle";

/** Mesma paleta/ícones de `taskStyle.ts` — igual ao board de "Minhas
 * tarefas", só que aqui as colunas são deste projeto especificamente. */
const COLUMNS: {
  status: TaskStatus;
  label: string;
  icon: LucideIcon;
  iconWrapperClass: string;
  columnTintClass: string;
  accentClass: string;
  countBadgeClass: string;
  dropRingClass: string;
}[] = (["PENDING", "IN_PROGRESS", "DONE"] as const).map((status) => ({
  status,
  label: STATUS_LABEL[status],
  icon: STATUS_ICON[status],
  accentClass: STATUS_ACCENT_CLASS[status],
  ...STATUS_COLUMN_STYLE[status],
}));

interface DeleteProjectDialogProps {
  projectName: string;
  onConfirm: () => Promise<void>;
}

function DeleteProjectDialog({ projectName, onConfirm }: DeleteProjectDialogProps) {
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirm() {
    setError(null);
    setIsDeleting(true);
    try {
      await onConfirm();
    } catch {
      setError("Não foi possível excluir este projeto. Tente novamente.");
      setIsDeleting(false);
    }
  }

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <button
          type="button"
          className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-red-400/30 bg-red-500/10 px-3 text-xs font-semibold text-red-300 transition-colors hover:bg-red-500/20"
        >
          <Trash2 className="size-3.5" />
          Excluir
        </button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Excluir "{projectName}"?</AlertDialogTitle>
          <AlertDialogDescription>
            As tarefas deste projeto não são excluídas — elas continuam no workspace, sem
            projeto vinculado. Comentários, checklists, anexos e histórico permanecem intactos.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} disabled={isDeleting} variant="destructive">
            {isDeleting ? "Excluindo..." : "Excluir"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

interface FlowStageProps {
  icon: LucideIcon;
  label: string;
  count: number;
  iconClass: string;
  badgeClass: string;
}

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

interface ProjectHeroProps {
  project: Project;
  canManage: boolean;
  pendingCount: number;
  inProgressCount: number;
  doneCount: number;
  total: number;
  progressPercent: number;
  onCreateTask: () => void;
  onEdit: () => void;
  onDelete: () => Promise<void>;
}

/** Mesma identidade escura dos outros heróis — cor do ícone segue o mesmo
 * `pickAccentColor` do cartão desse projeto na grade de Projetos, e a
 * trilha com a bolinha animada é a MESMA do board de "Minhas tarefas"
 * (aqui faz sentido reaproveitar a metáfora de pipeline: este board tem os
 * mesmos 3 estágios reais Pendente/Em andamento/Concluída). */
function ProjectHero({
  project,
  canManage,
  pendingCount,
  inProgressCount,
  doneCount,
  total,
  progressPercent,
  onCreateTask,
  onEdit,
  onDelete,
}: ProjectHeroProps) {
  const accent = pickAccentColor(project.id);

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0b1220] via-[#0a0f1e] to-[#05070f] p-5 shadow-xl shadow-black/20 sm:p-6">
      <div className="blob-drift-a pointer-events-none absolute -top-20 -left-14 size-56 rounded-full bg-blue-600/25 blur-[80px]" />
      <div className="blob-drift-b pointer-events-none absolute -right-16 -bottom-20 size-64 rounded-full bg-violet-500/20 blur-[90px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] bg-[size:32px_32px]" />
      <FolderKanban
        className="pointer-events-none absolute -right-8 -bottom-10 size-44 -rotate-12 text-blue-500/[0.06]"
        strokeWidth={1}
      />

      <div className="relative flex flex-col gap-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="relative flex size-10 shrink-0 items-center justify-center">
              <div className={cn("absolute inset-0 rounded-xl opacity-70 blur-md", accent.glowClass)} />
              <div
                className={cn(
                  "relative flex size-10 items-center justify-center rounded-xl bg-gradient-to-br shadow-lg",
                  accent.gradientClass,
                  accent.shadowClass,
                )}
              >
                <FolderKanban className="size-5 text-white" strokeWidth={2.25} />
              </div>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
                {project.name}
              </h1>
              <p className="text-xs text-slate-400 sm:text-sm">
                {project.description ?? "Sem descrição."}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {canManage && (
              <>
                <button
                  type="button"
                  onClick={onEdit}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 text-xs font-semibold text-slate-200 transition-colors hover:bg-white/10"
                >
                  <PencilIcon className="size-3.5" />
                  Editar
                </button>
                <DeleteProjectDialog projectName={project.name} onConfirm={onDelete} />
              </>
            )}
            <Button
              onClick={onCreateTask}
              className="h-10 w-fit gap-1.5 rounded-xl bg-white px-4 text-sm font-semibold text-[#05070f] shadow-lg shadow-black/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-xl hover:shadow-blue-500/10"
            >
              <PlusIcon className="size-4" />
              Nova tarefa
            </Button>
          </div>
        </div>

        {total > 0 && (
          <div className="flex flex-col gap-3 border-t border-white/10 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-1 flex-col gap-2.5">
              {/* Mesmo trilho com a bolinha animada do board de "Minhas
                 tarefas" (`kanban-token`/`kanban-flow` de `global.css`) —
                 alinhado às mesmas 3 colunas (16,6% / 50% / 83,3%). */}
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

interface TaskCardProps {
  task: Task;
  index: number;
  isDragging: boolean;
  assigneeName: string;
  onOpen: () => void;
  onDragStart: (event: DragEvent<HTMLDivElement>) => void;
  onDragEnd: () => void;
}

/** Mesmo cartão do board de "Minhas tarefas" (borda por prioridade,
 * animação de entrada, elevação ao arrastar) — com um avatar de
 * responsável no canto (aqui as tarefas têm dono, ao contrário das
 * pessoais, onde o dono é sempre o próprio usuário). */
function TaskCard({ task, index, isDragging, assigneeName, onOpen, onDragStart, onDragEnd }: TaskCardProps) {
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
        <GripVertical className="mt-1 size-3.5 shrink-0 text-transparent transition-colors group-hover:text-muted-foreground/40" />
        <p
          className={cn(
            "flex-1 text-sm font-medium",
            isDone && "text-muted-foreground line-through",
          )}
        >
          {task.title}
        </p>
        <Avatar size="sm" className="shrink-0" title={assigneeName}>
          <AvatarFallback className="bg-gradient-to-br from-blue-400 to-blue-700 text-[10px] font-semibold text-white">
            {getInitials(assigneeName)}
          </AvatarFallback>
        </Avatar>
      </div>
      <div className="flex flex-wrap items-center gap-1.5 pl-5">
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
            PRIORITY_CHIP_CLASS[task.priority],
          )}
        >
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
  assigneeName: (assigneeId: string) => string;
  onOpenTask: (task: Task) => void;
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
  assigneeName,
  onOpenTask,
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
            assigneeName={assigneeName(task.assignee_id)}
            onOpen={() => onOpenTask(task)}
            onDragStart={onDragStartTask(task.id)}
            onDragEnd={onDragEndTask}
          />
        ))}
      </div>
    </div>
  );
}

export function ProjectDetailPage() {
  const { workspaceId, projectId } = useParams<{ workspaceId: string; projectId: string }>();
  const navigate = useNavigate();
  const { workspace } = useWorkspace(workspaceId ?? "");
  const { members } = useWorkspaceMembers(workspaceId ?? "");
  const { project, isLoading, error, updateProject, deleteProject } = useProject(projectId ?? "");
  const {
    tasks,
    isLoading: tasksLoading,
    error: tasksError,
    updateTask,
  } = useTasks({ project_id: projectId ?? "" });
  const [editOpen, setEditOpen] = useState(false);
  const [draggingId, setDraggingId] = useState<string | null>(null);

  if (!workspaceId || !projectId) {
    return <Navigate to="/workspaces" replace />;
  }

  const canManage = workspace?.my_role === "OWNER" || workspace?.my_role === "ADMIN";

  function assigneeName(assigneeId: string): string {
    return members.find((member) => member.user_id === assigneeId)?.name ?? "—";
  }

  async function handleEditSubmit(values: ProjectFormValues) {
    const payload: ProjectUpdate = {
      name: values.name,
      description: values.description.trim() === "" ? null : values.description,
    };
    await updateProject(payload);
    setEditOpen(false);
  }

  async function handleDelete() {
    await deleteProject();
    navigate(`/workspaces/${workspaceId}/projects`);
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
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate(`/workspaces/${workspaceId}/projects`)}
        className="w-fit gap-1.5 text-muted-foreground"
      >
        <ArrowLeft className="size-4" />
        Projetos
      </Button>

      {isLoading && <Skeleton className="h-40 w-full rounded-2xl" />}

      {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

      {!isLoading && !error && project && (
        <>
          <ProjectHero
            project={project}
            canManage={canManage}
            pendingCount={pendingCount}
            inProgressCount={inProgressCount}
            doneCount={doneCount}
            total={total}
            progressPercent={progressPercent}
            onCreateTask={() => navigate(`/tasks/new?workspace_id=${workspaceId}&project_id=${projectId}`)}
            onEdit={() => setEditOpen(true)}
            onDelete={handleDelete}
          />

          {tasksLoading && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <Skeleton className="h-64 w-full" />
              <Skeleton className="h-64 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          )}

          {!tasksLoading && tasksError && <p className="text-sm text-destructive">{tasksError}</p>}

          {!tasksLoading && !tasksError && tasks.length === 0 && (
            <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed py-16 text-center">
              <div className="flex size-14 items-center justify-center rounded-2xl bg-blue-500/10">
                <FolderKanban className="size-7 text-blue-500/60" strokeWidth={1.5} />
              </div>
              <p className="max-w-xs text-sm text-muted-foreground">
                Nenhuma tarefa neste projeto ainda. Crie a primeira clicando em &quot;Nova
                tarefa&quot;.
              </p>
            </div>
          )}

          {!tasksLoading && !tasksError && tasks.length > 0 && (
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
                  assigneeName={assigneeName}
                  onOpenTask={(task) => navigate(`/tasks/${task.id}`)}
                  onDragStartTask={handleDragStartTask}
                  onDragEndTask={() => setDraggingId(null)}
                  onDropTask={handleDropTask}
                />
              ))}
            </div>
          )}

          <Sheet open={editOpen} onOpenChange={setEditOpen}>
            <SheetContent>
              <SheetHeader>
                <div className="flex items-center gap-2.5">
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/20">
                    <PencilIcon className="size-4 text-white" />
                  </div>
                  <SheetTitle>Editar projeto</SheetTitle>
                </div>
              </SheetHeader>
              <div className="px-4 pb-4">
                <ProjectForm
                  project={project}
                  onSubmit={handleEditSubmit}
                  onCancel={() => setEditOpen(false)}
                />
              </div>
            </SheetContent>
          </Sheet>
        </>
      )}
    </div>
  );
}
