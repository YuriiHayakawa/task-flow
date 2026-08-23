import axios from "axios";
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
  UserPlus,
  Users,
  type LucideIcon,
} from "lucide-react";
import { useState, type DragEvent, type MouseEvent, type FormEvent } from "react";
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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useProject } from "@/hooks/useProject";
import { useProjectMembers } from "@/hooks/useProjectMembers";
import { useTasks } from "@/hooks/useTasks";
import { useWorkspace } from "@/hooks/useWorkspace";
import { useWorkspaceMembers } from "@/hooks/useWorkspaceMembers";
import { cn } from "@/lib/utils";
import type { ApiError } from "@/types/apiError";
import type { ProjectMember } from "@/types/projectMember";
import type { Project, ProjectUpdate } from "@/types/project";
import type { Task, TaskStatus } from "@/types/task";
import type { WorkspaceMember } from "@/types/workspace";
import { pickAccentColor } from "@/utils/accentColor";
import { getApiErrorMessage } from "@/utils/apiErrorMessage";
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

interface RemoveProjectMemberDialogProps {
  member: ProjectMember;
  onConfirm: () => Promise<void>;
}

/** Mesmo padrão de `RemoveMemberDialog` (`WorkspaceMembersPage.tsx`):
 * estado de erro/"removendo..." autocontido, incl. a lista de tarefas
 * pendentes quando o backend recusa por tarefas ativas no projeto
 * (FR-010).
 *
 * Diferença deliberada: `AlertDialogAction` do Radix fecha o diálogo de
 * forma SÍNCRONA ao ser clicado, antes do resultado de `onConfirm` (que é
 * assíncrono) — sem tratar isso, a mensagem de erro (ex.: lista de tarefas
 * pendentes) nunca chegaria a aparecer, porque o diálogo já teria fechado.
 * Por isso o diálogo é controlado (`open`/`onOpenChange`) e `handleConfirm`
 * chama `event.preventDefault()` antes de qualquer `await` — só fecha
 * manualmente (`setOpen(false)`) quando `onConfirm` realmente é bem-
 * sucedido. */
function RemoveProjectMemberDialog({ member, onConfirm }: RemoveProjectMemberDialogProps) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingTasks, setPendingTasks] = useState<string[]>([]);
  const [isRemoving, setIsRemoving] = useState(false);

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (nextOpen) {
      setError(null);
      setPendingTasks([]);
    }
  }

  async function handleConfirm(event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    setError(null);
    setPendingTasks([]);
    setIsRemoving(true);
    try {
      await onConfirm();
      setOpen(false);
    } catch (err) {
      setError(getApiErrorMessage(err, "Não foi possível remover este membro."));
      if (axios.isAxiosError(err)) {
        const details = (err.response?.data as ApiError | undefined)?.error?.details;
        const titles = details
          ?.map((detail) => (typeof detail.title === "string" ? detail.title : null))
          .filter((title): title is string => title !== null);
        if (titles && titles.length > 0) setPendingTasks(titles);
      }
    } finally {
      setIsRemoving(false);
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label={`Remover ${member.name}`}>
          <Trash2 className="size-4 text-destructive" />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Remover {member.name}?</AlertDialogTitle>
          <AlertDialogDescription>
            Esta pessoa perde acesso ao quadro e às tarefas deste projeto.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {error && (
          <div className="text-sm text-destructive">
            <p>{error}</p>
            {pendingTasks.length > 0 && (
              <ul className="mt-1.5 list-inside list-disc text-xs">
                {pendingTasks.map((title) => (
                  <li key={title}>{title}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isRemoving}>Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} disabled={isRemoving} variant="destructive">
            {isRemoving ? "Removendo..." : "Remover"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

interface AddProjectMemberFormProps {
  /** Só membros do workspace que ainda não são membros deste projeto —
   * FR-002 já exige isso no backend (não é possível adicionar alguém de
   * fora do workspace a um projeto); o dropdown evita até a tentativa,
   * listando só quem já é elegível, em vez de um campo de e-mail livre. */
  availableMembers: WorkspaceMember[];
  onAdd: (userId: string) => Promise<void>;
}

function AddProjectMemberForm({ availableMembers, onAdd }: AddProjectMemberFormProps) {
  const [selectedUserId, setSelectedUserId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onAdd(selectedUserId);
      setSelectedUserId("");
    } catch (err) {
      setError(getApiErrorMessage(err, "Não foi possível adicionar esta pessoa."));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (availableMembers.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Todos os membros do workspace já participam deste projeto.
      </p>
    );
  }

  // Valor exibido no trigger é explícito (só o nome) em vez de deixar o
  // Radix portar o conteúdo rico do SelectItem (avatar + e-mail) para dentro
  // da caixinha fechada — isso manteria o trigger poluído/estourando altura
  // e criaria um estado intermediário onde o nome sozinho fica duplicado no
  // DOM (trigger + linha da lista) até o formulário resetar a seleção.
  const selectedMember = availableMembers.find((member) => member.user_id === selectedUserId);

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="flex flex-col gap-2">
        <Label htmlFor="project-member-select">Adicionar membro</Label>
        <Select value={selectedUserId} onValueChange={setSelectedUserId}>
          <SelectTrigger
            id="project-member-select"
            className="w-full rounded-xl border-input bg-card px-4 text-sm transition-all duration-200 hover:border-blue-300 hover:shadow-sm data-placeholder:text-muted-foreground data-[size=default]:h-11 [&>svg]:text-muted-foreground [&>svg]:transition-transform [&>svg]:duration-200 [&[data-state=open]>svg]:rotate-180"
          >
            <SelectValue placeholder="Selecione uma pessoa do workspace">
              {selectedMember?.name}
            </SelectValue>
          </SelectTrigger>
          {/* position="popper" abre a lista ABAIXO do campo (como um menu
           * normal) em vez do padrão "item-aligned" do Radix, que sobrepõe o
           * painel por cima do próprio campo — o efeito de "tampar" o input
           * que pareceu quebrado. */}
          <SelectContent position="popper" align="start" sideOffset={6} className="rounded-xl p-1.5">
            {availableMembers.map((member) => (
              <SelectItem
                key={member.user_id}
                value={member.user_id}
                className="rounded-lg py-2 pl-2 focus:bg-blue-50 focus:text-foreground dark:focus:bg-blue-500/15"
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  <Avatar size="sm" className="size-7 shrink-0 rounded-lg">
                    <AvatarFallback className="rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 text-[10px] font-semibold text-white">
                      {getInitials(member.name)}
                    </AvatarFallback>
                  </Avatar>
                  <span className="flex min-w-0 flex-col leading-tight">
                    <span className="truncate font-medium">{member.name}</span>
                    <span className="truncate text-xs text-muted-foreground">{member.email}</span>
                  </span>
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Só pessoas que já são membros do workspace aparecem aqui.
        </p>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={isSubmitting || !selectedUserId}
          className="rounded-xl bg-blue-600 text-white hover:bg-blue-500"
        >
          <UserPlus className="size-4" />
          {isSubmitting ? "Adicionando..." : "Adicionar"}
        </Button>
      </div>
    </form>
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
  onManageMembers: () => void;
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
  onManageMembers,
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
                  onClick={onManageMembers}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 text-xs font-semibold text-slate-200 transition-colors hover:bg-white/10"
                >
                  <Users className="size-3.5" />
                  Membros
                </button>
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
  const {
    members: projectMembers,
    isLoading: projectMembersLoading,
    addMember: addProjectMember,
    removeMember: removeProjectMember,
  } = useProjectMembers(projectId ?? "");
  const [editOpen, setEditOpen] = useState(false);
  const [membersOpen, setMembersOpen] = useState(false);
  const [draggingId, setDraggingId] = useState<string | null>(null);

  if (!workspaceId || !projectId) {
    return <Navigate to="/workspaces" replace />;
  }

  const canManage = workspace?.my_role === "OWNER" || workspace?.my_role === "ADMIN";
  // FR-002: só quem já é membro do workspace pode ser adicionado ao
  // projeto — filtra fora de quem já está no projeto para o dropdown de
  // "adicionar" não repetir gente já adicionada.
  const availableToAddToProject = members.filter(
    (workspaceMember) =>
      !projectMembers.some((projectMember) => projectMember.user_id === workspaceMember.user_id),
  );

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

  async function handleAddProjectMember(userId: string) {
    await addProjectMember({ user_id: userId });
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
            onManageMembers={() => setMembersOpen(true)}
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

          <Sheet open={membersOpen} onOpenChange={setMembersOpen}>
            <SheetContent>
              <SheetHeader>
                <div className="flex items-center gap-2.5">
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/20">
                    <Users className="size-4 text-white" />
                  </div>
                  <SheetTitle>Membros do projeto</SheetTitle>
                </div>
              </SheetHeader>
              <div className="flex flex-col gap-4 px-4 pb-4">
                {projectMembersLoading && (
                  <div className="flex flex-col gap-2">
                    <Skeleton className="h-14 w-full rounded-xl" />
                    <Skeleton className="h-14 w-full rounded-xl" />
                  </div>
                )}
                {!projectMembersLoading && (
                  <div className="flex flex-col gap-2">
                    {projectMembers.map((member) => (
                      <div
                        key={member.user_id}
                        className="flex items-center gap-3 rounded-xl border bg-card p-3"
                      >
                        <Avatar size="sm" className="rounded-lg">
                          <AvatarFallback className="rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 text-[11px] font-semibold text-white">
                            {getInitials(member.name)}
                          </AvatarFallback>
                        </Avatar>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{member.name}</p>
                          <p className="truncate text-xs text-muted-foreground">{member.email}</p>
                        </div>
                        <RemoveProjectMemberDialog
                          member={member}
                          onConfirm={() => removeProjectMember(member.user_id)}
                        />
                      </div>
                    ))}
                  </div>
                )}

                <div className="border-t pt-4">
                  <AddProjectMemberForm
                    availableMembers={availableToAddToProject}
                    onAdd={handleAddProjectMember}
                  />
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </>
      )}
    </div>
  );
}
