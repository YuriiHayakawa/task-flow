import {
  AlignLeft,
  ArrowLeft,
  Building2,
  Calendar,
  CheckCircle2,
  ClipboardList,
  Clock,
  Download,
  FileText,
  FolderKanban,
  History,
  ListChecks,
  MessageSquare,
  Paperclip,
  PencilIcon,
  Plus,
  Send,
  Trash2,
  UserPlus,
  UserRound,
  Users,
  type LucideIcon,
} from "lucide-react";
import { useRef, useState, type ChangeEvent, type SubmitEvent } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";

import { AddMemberByEmailForm } from "@/components/forms/AddMemberByEmailForm";
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
import { Input } from "@/components/ui/input";
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
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/contexts/AuthContext";
import { useAttachments } from "@/hooks/useAttachments";
import { useChecklist } from "@/hooks/useChecklist";
import { useComments } from "@/hooks/useComments";
import { useProject } from "@/hooks/useProject";
import { useTask } from "@/hooks/useTask";
import { useTaskHistory } from "@/hooks/useTaskHistory";
import { useTaskMembers } from "@/hooks/useTaskMembers";
import { useWorkspace } from "@/hooks/useWorkspace";
import { useWorkspaceMembers } from "@/hooks/useWorkspaceMembers";
import { cn } from "@/lib/utils";
import type { Attachment } from "@/types/attachment";
import type { TaskHistoryEntry } from "@/types/taskHistory";
import type { TaskPriority, TaskStatus } from "@/types/task";
import * as userService from "@/services/userService";
import { getApiErrorMessage } from "@/utils/apiErrorMessage";
import { getInitials } from "@/utils/initials";
import {
  PRIORITY_CHIP_CLASS,
  PRIORITY_LABEL,
  STATUS_BADGE_CLASS,
  STATUS_ICON,
  STATUS_LABEL,
  describeDueDate,
} from "@/utils/taskStyle";

/** Variantes das mesmas cores de `taskStyle.ts`, para uso sobre o fundo
 * escuro do cabeçalho (não exportadas — só esta página tem um cabeçalho
 * escuro hoje; se uma segunda precisar, aí sim vale extrair). */
const STATUS_BADGE_DARK_CLASS: Record<TaskStatus, string> = {
  PENDING: "bg-slate-400/15 text-slate-300",
  IN_PROGRESS: "bg-blue-400/20 text-blue-200",
  DONE: "bg-emerald-400/20 text-emerald-200",
};

const PRIORITY_CHIP_DARK_CLASS: Record<TaskPriority, string> = {
  LOW: "bg-slate-400/15 text-slate-300",
  MEDIUM: "bg-blue-400/20 text-blue-200",
  HIGH: "bg-amber-400/20 text-amber-200",
  URGENT: "bg-red-400/20 text-red-200",
};

const DUE_BADGE_DARK_CLASS: Record<"neutral" | "warning" | "danger", string> = {
  neutral: "bg-white/10 text-slate-300",
  warning: "bg-amber-400/20 text-amber-200",
  danger: "bg-red-400/20 text-red-200",
};

/** Cor do pontinho do histórico por campo alterado (research.md/T110: os
 * únicos 4 campos rastreados) — a mesma paleta de sempre, uma cor por tipo
 * de mudança em vez de tudo azul, pra dar pra "escanear" o histórico pela
 * cor sem ler o texto inteiro. */
const HISTORY_DOT_CLASS: Record<string, string> = {
  status: "bg-blue-500 ring-blue-500/15",
  priority: "bg-amber-500 ring-amber-500/15",
  due_date: "bg-indigo-500 ring-indigo-500/15",
  assignee_id: "bg-emerald-500 ring-emerald-500/15",
};

const ATTACHMENT_ACCEPT = "image/png,image/jpeg,application/pdf,text/plain";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function formatDateOnly(value: string): string {
  return new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR");
}

/** Traduz uma `TaskHistoryEntry` crua (campo técnico + valores brutos) para
 * uma frase legível — os únicos 4 campos rastreados por `TaskService.update`
 * (status/priority/due_date/assignee_id, T110). `resolveMemberName` só
 * entra para `assignee_id` (único campo cujo valor é um id, não já um rótulo
 * pronto). */
function describeHistoryEntry(
  entry: TaskHistoryEntry,
  resolveMemberName: (userId: string) => string,
): string {
  switch (entry.field_changed) {
    case "status":
      return `Status alterado de "${STATUS_LABEL[entry.old_value as TaskStatus] ?? entry.old_value}" para "${STATUS_LABEL[entry.new_value as TaskStatus] ?? entry.new_value}"`;
    case "priority":
      return `Prioridade alterada de "${PRIORITY_LABEL[entry.old_value as TaskPriority] ?? entry.old_value}" para "${PRIORITY_LABEL[entry.new_value as TaskPriority] ?? entry.new_value}"`;
    case "due_date":
      if (!entry.new_value) return "Prazo removido";
      if (!entry.old_value) return `Prazo definido para ${formatDateOnly(entry.new_value)}`;
      return `Prazo alterado para ${formatDateOnly(entry.new_value)}`;
    case "assignee_id":
      return `Responsável alterado para ${entry.new_value ? resolveMemberName(entry.new_value) : "—"}`;
    default:
      return `${entry.field_changed} alterado`;
  }
}

interface SectionIconProps {
  icon: LucideIcon;
  className: string;
}

/** Ícone de cabeçalho de seção, em bloco colorido em gradiente — cada
 * seção da página (Descrição/Participantes/Checklist/Comentários/Anexos/
 * Detalhes/Histórico) ganha sua própria cor, no lugar do mesmo ícone cinza-
 * neutro repetido em todo canto (era isso que deixava a tela "sem vida"). */
function SectionIcon({ icon: Icon, className }: SectionIconProps) {
  return (
    <span className={cn("flex size-6 shrink-0 items-center justify-center rounded-lg text-white shadow-sm", className)}>
      <Icon className="size-3.5" />
    </span>
  );
}

interface DetailRowIconProps {
  icon: LucideIcon;
  className: string;
}

/** Mesma ideia de `SectionIcon`, em círculo pequeno, para as linhas de
 * "Detalhes da tarefa" (pessoas em azul, workspace em neutro, projeto em
 * índigo) — ecoa a linguagem visual dos avatares de Participantes. */
function DetailRowIcon({ icon: Icon, className }: DetailRowIconProps) {
  return (
    <span className={cn("flex size-6 shrink-0 items-center justify-center rounded-full", className)}>
      <Icon className="size-3.5" />
    </span>
  );
}

interface RemoveParticipantDialogProps {
  name: string;
  onConfirm: () => Promise<void>;
}

function RemoveParticipantDialog({ name, onConfirm }: RemoveParticipantDialogProps) {
  const [error, setError] = useState<string | null>(null);
  const [isRemoving, setIsRemoving] = useState(false);

  async function handleConfirm() {
    setError(null);
    setIsRemoving(true);
    try {
      await onConfirm();
    } catch (err) {
      setError(getApiErrorMessage(err, "Não foi possível remover este participante."));
      setIsRemoving(false);
    }
  }

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label={`Remover ${name}`}>
          <Trash2 className="size-4 text-destructive" />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Remover {name} da tarefa?</AlertDialogTitle>
          <AlertDialogDescription>
            Comentários, anexos e histórico já existentes não são afetados.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {error && <p className="text-sm text-destructive">{error}</p>}
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

interface CommentFormProps {
  disabled: boolean;
  onSubmit: (content: string) => Promise<void>;
}

/** Formulário de um único campo (conteúdo) — não reaproveitado em nenhuma
 * outra tela, ao contrário de `AddMemberByEmailForm`, então fica local a
 * esta página. Permanece visível mesmo quando `disabled` (não é
 * participante) — só o campo/botão ficam desabilitados, com uma dica do
 * motivo, em vez de a seção sumir por completo (listagem continua visível a
 * todo membro do workspace, contracts/collaboration.md). */
function CommentForm({ disabled, onSubmit }: CommentFormProps) {
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit(content);
      setContent("");
    } catch (err) {
      setError(getApiErrorMessage(err, "Não foi possível adicionar o comentário."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <Textarea
        value={content}
        onChange={(event) => setContent(event.target.value)}
        disabled={disabled || isSubmitting}
        placeholder={
          disabled
            ? "Você precisa ser participante desta tarefa para comentar."
            : "Escreva um comentário..."
        }
        className="min-h-20 rounded-xl"
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="flex justify-end">
        <Button
          type="submit"
          size="sm"
          disabled={disabled || isSubmitting || content.trim() === ""}
          className="gap-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-500"
        >
          <Send className="size-4" />
          {isSubmitting ? "Enviando..." : "Comentar"}
        </Button>
      </div>
    </form>
  );
}

interface ChecklistItemRowProps {
  description: string;
  isDone: boolean;
  canEdit: boolean;
  onToggle: () => Promise<void>;
  onRemove: () => Promise<void>;
}

function ChecklistItemRow({ description, isDone, canEdit, onToggle, onRemove }: ChecklistItemRowProps) {
  const [isBusy, setIsBusy] = useState(false);

  async function handleToggle() {
    setIsBusy(true);
    try {
      await onToggle();
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRemove() {
    setIsBusy(true);
    try {
      await onRemove();
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <div className="group flex items-center gap-2.5">
      <button
        type="button"
        role="checkbox"
        aria-checked={isDone}
        aria-label={isDone ? "Marcar como pendente" : "Marcar como concluído"}
        onClick={() => void handleToggle()}
        disabled={!canEdit || isBusy}
        className={cn(
          "flex size-[18px] shrink-0 items-center justify-center rounded-[5px] border transition-colors disabled:cursor-not-allowed disabled:opacity-60",
          isDone ? "border-emerald-600 bg-emerald-600 text-white" : "border-input bg-transparent",
        )}
      >
        {isDone && (
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 6 9 17l-5-5" />
          </svg>
        )}
      </button>
      <span className={cn("flex-1 text-sm", isDone && "text-muted-foreground line-through")}>
        {description}
      </span>
      {canEdit && (
        <button
          type="button"
          onClick={() => void handleRemove()}
          disabled={isBusy}
          aria-label={`Remover item "${description}"`}
          className="shrink-0 rounded-lg p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-muted hover:text-destructive group-hover:opacity-100 disabled:opacity-50"
        >
          <Trash2 className="size-3.5" />
        </button>
      )}
    </div>
  );
}

interface AddChecklistItemFormProps {
  onAdd: (description: string) => Promise<void>;
}

function AddChecklistItemForm({ onAdd }: AddChecklistItemFormProps) {
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    if (description.trim() === "") return;
    setError(null);
    setIsSubmitting(true);
    try {
      await onAdd(description.trim());
      setDescription("");
    } catch (err) {
      setError(getApiErrorMessage(err, "Não foi possível adicionar o item."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-1.5">
      <div className="flex gap-2">
        <Input
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Adicionar item..."
          disabled={isSubmitting}
          className="h-9 rounded-lg text-sm"
        />
        <Button
          type="submit"
          size="icon"
          variant="outline"
          disabled={isSubmitting || description.trim() === ""}
          className="size-9 shrink-0 rounded-lg"
          aria-label="Adicionar item ao checklist"
        >
          <Plus className="size-4" />
        </Button>
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </form>
  );
}

interface RemoveAttachmentDialogProps {
  filename: string;
  onConfirm: () => Promise<void>;
}

function RemoveAttachmentDialog({ filename, onConfirm }: RemoveAttachmentDialogProps) {
  const [error, setError] = useState<string | null>(null);
  const [isRemoving, setIsRemoving] = useState(false);

  async function handleConfirm() {
    setError(null);
    setIsRemoving(true);
    try {
      await onConfirm();
    } catch (err) {
      setError(getApiErrorMessage(err, "Não foi possível remover este anexo."));
      setIsRemoving(false);
    }
  }

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label={`Remover ${filename}`}>
          <Trash2 className="size-4 text-destructive" />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Remover "{filename}"?</AlertDialogTitle>
          <AlertDialogDescription>
            O arquivo é removido definitivamente. Não é possível desfazer.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {error && <p className="text-sm text-destructive">{error}</p>}
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

interface AttachmentRowProps {
  attachment: Attachment;
  canRemove: boolean;
  onDownload: () => void;
  onRemove: () => Promise<void>;
}

function AttachmentRow({ attachment, canRemove, onDownload, onRemove }: AttachmentRowProps) {
  const isImage = attachment.content_type.startsWith("image/");
  const isPdf = attachment.content_type === "application/pdf";

  return (
    <div className="flex items-center gap-3 rounded-xl border p-2.5">
      <div
        className={cn(
          "flex size-9 shrink-0 items-center justify-center rounded-lg",
          isImage && "bg-blue-100 text-blue-600 dark:bg-blue-950 dark:text-blue-300",
          isPdf && "bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-300",
          !isImage && !isPdf && "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
        )}
      >
        <FileText className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{attachment.original_filename}</p>
        <p className="truncate text-xs text-muted-foreground">
          {formatFileSize(attachment.size_bytes)} · {attachment.uploaded_by_name} ·{" "}
          {formatDateTime(attachment.created_at)}
        </p>
      </div>
      <Button variant="ghost" size="icon-sm" aria-label={`Baixar ${attachment.original_filename}`} onClick={onDownload}>
        <Download className="size-4" />
      </Button>
      {canRemove && <RemoveAttachmentDialog filename={attachment.original_filename} onConfirm={onRemove} />}
    </div>
  );
}

interface AttachmentUploadButtonProps {
  onUpload: (file: File) => Promise<void>;
}

function AttachmentUploadButton({ onUpload }: AttachmentUploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError(null);
    setIsUploading(true);
    try {
      await onUpload(file);
    } catch (err) {
      setError(getApiErrorMessage(err, "Não foi possível enviar o arquivo."));
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <input
        ref={inputRef}
        type="file"
        accept={ATTACHMENT_ACCEPT}
        onChange={(event) => void handleChange(event)}
        className="hidden"
      />
      <Button
        variant="outline"
        size="sm"
        className="gap-1.5 rounded-lg"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
      >
        <Paperclip className="size-4" />
        {isUploading ? "Enviando..." : "Adicionar anexo"}
      </Button>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

export function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const { task, isLoading, error, updateTask, deleteTask } = useTask(taskId ?? "");
  const isWorkspaceTask = Boolean(task?.workspace_id);
  const { workspace } = useWorkspace(isWorkspaceTask ? (task!.workspace_id as string) : "");
  const { members } = useWorkspaceMembers(isWorkspaceTask ? (task!.workspace_id as string) : "");
  const { project } = useProject(task?.project_id ?? "");
  const {
    members: participants,
    isLoading: participantsLoading,
    error: participantsError,
    addMember: addParticipant,
    removeMember: removeParticipant,
  } = useTaskMembers(taskId ?? "");
  const {
    comments,
    isLoading: commentsLoading,
    error: commentsError,
    addComment,
  } = useComments(taskId ?? "");
  const {
    items: checklistItems,
    isLoading: checklistLoading,
    error: checklistError,
    addItem: addChecklistItem,
    toggleItem: toggleChecklistItem,
    removeItem: removeChecklistItem,
  } = useChecklist(taskId ?? "");
  const {
    attachments,
    isLoading: attachmentsLoading,
    error: attachmentsError,
    uploadFile,
    removeAttachment,
    downloadAttachment,
  } = useAttachments(taskId ?? "");
  const {
    entries: historyEntries,
    isLoading: historyLoading,
    error: historyError,
  } = useTaskHistory(taskId ?? "");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isToggling, setIsToggling] = useState(false);
  const [addParticipantOpen, setAddParticipantOpen] = useState(false);

  if (!taskId) {
    return <Navigate to="/workspaces" replace />;
  }

  if (isLoading) {
    return <Skeleton className="h-96 w-full rounded-2xl" />;
  }

  if (error || !task) {
    return <p className="text-sm text-destructive">{error ?? "Tarefa não encontrada."}</p>;
  }

  const isPersonal = task.workspace_id === null;
  const isCreator = task.creator_id === currentUser?.id;
  const isAssignee = task.assignee_id === currentUser?.id;
  const isWorkspaceManager = workspace?.my_role === "OWNER" || workspace?.my_role === "ADMIN";

  // Espelha exatamente require_task_editor/require_task_delete do backend
  // (contracts/projects-and-tasks.md) — nunca decide autorização por conta
  // própria, só reflete na UI o que o backend já impõe.
  const canEdit = isPersonal ? isCreator : isCreator || isAssignee || isWorkspaceManager;
  const canDelete = isPersonal ? isCreator : isCreator || isWorkspaceManager;
  // Colaboração ≠ visibilidade (require_task_participant, contracts/
  // collaboration.md): responsável e participantes explícitos comentam,
  // mexem no checklist e enviam anexo; Owner/Admin só se também forem
  // participantes — nunca por posição. O responsável já vem embutido em
  // `participants` (implícito), então basta checar a lista.
  const isParticipant = participants.some((participant) => participant.user_id === currentUser?.id);

  function memberName(userId: string): string {
    if (userId === currentUser?.id) return "Você";
    return members.find((member) => member.user_id === userId)?.name ?? "—";
  }

  const backTo = task.project_id
    ? `/workspaces/${task.workspace_id}/projects/${task.project_id}`
    : task.workspace_id
      ? `/workspaces/${task.workspace_id}`
      : "/tasks";

  async function handleToggleDone() {
    setIsToggling(true);
    try {
      await updateTask({ status: task!.status === "DONE" ? "PENDING" : "DONE" });
    } finally {
      setIsToggling(false);
    }
  }

  async function handleStatusChange(value: string) {
    await updateTask({ status: value as TaskStatus });
  }

  async function handlePriorityChange(value: string) {
    await updateTask({ priority: value as TaskPriority });
  }

  async function handleAddParticipant(email: string) {
    const found = await userService.lookupByEmail(email);
    await addParticipant({ user_id: found.id });
    setAddParticipantOpen(false);
  }

  async function handleAddComment(content: string) {
    await addComment({ content });
  }

  async function handleAddChecklistItem(description: string) {
    await addChecklistItem({ description });
  }

  async function handleDelete() {
    setDeleteError(null);
    setIsDeleting(true);
    try {
      await deleteTask();
      navigate(backTo);
    } catch {
      setDeleteError("Não foi possível excluir esta tarefa. Tente novamente.");
      setIsDeleting(false);
    }
  }

  const StatusIcon = STATUS_ICON[task.status];
  const due = task.due_date ? describeDueDate(task.due_date, task.status === "DONE") : null;
  const checklistDoneCount = checklistItems.filter((item) => item.is_done).length;
  const checklistProgress =
    checklistItems.length > 0 ? Math.round((checklistDoneCount / checklistItems.length) * 100) : 0;

  return (
    <div className="flex flex-col gap-5">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate(backTo)}
        className="w-fit gap-1.5 text-muted-foreground"
      >
        <ArrowLeft className="size-4" />
        Voltar
      </Button>

      {/* Cabeçalho — mesma identidade escura/textura/blobs do hero de
         "Minhas tarefas" (BrandPanel), trazida também para a página de
         detalhes: as duas telas mais visitadas do produto agora conversam
         visualmente entre si. */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0b1220] via-[#0a0f1e] to-[#05070f] p-6 shadow-xl shadow-black/20 sm:p-7">
        <div className="blob-drift-a pointer-events-none absolute -top-24 -left-16 size-64 rounded-full bg-blue-600/25 blur-[80px]" />
        <div className="blob-drift-b pointer-events-none absolute -right-16 -bottom-20 size-64 rounded-full bg-indigo-500/20 blur-[90px]" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] bg-[size:32px_32px]" />

        <div className="relative flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
              {task.title}
            </h1>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium", STATUS_BADGE_DARK_CLASS[task.status])}>
                <StatusIcon className="size-3" />
                {STATUS_LABEL[task.status]}
              </span>
              <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium", PRIORITY_CHIP_DARK_CLASS[task.priority])}>
                {PRIORITY_LABEL[task.priority]}
              </span>
              {due && (
                <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium", DUE_BADGE_DARK_CLASS[due.tone])}>
                  <Calendar className="size-3" />
                  {due.label}
                </span>
              )}
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            {canEdit && (
              <Button
                variant="outline"
                className="gap-1.5 rounded-xl border-white/15 bg-white/5 text-white hover:bg-white/10"
                onClick={() => void handleToggleDone()}
                disabled={isToggling}
              >
                <CheckCircle2 className="size-4" />
                {task.status === "DONE" ? "Reabrir" : "Marcar como concluída"}
              </Button>
            )}
            {canEdit && (
              <Button
                variant="outline"
                className="gap-1.5 rounded-xl border-white/15 bg-white/5 text-white hover:bg-white/10"
                onClick={() => navigate(`/tasks/${task.id}/edit`)}
              >
                <PencilIcon className="size-4" />
                Editar
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* ===== Coluna principal ===== */}
        <div className="flex flex-col gap-5 lg:col-span-2">
          <div className="flex flex-col gap-2 rounded-2xl border bg-card p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <SectionIcon icon={AlignLeft} className="bg-gradient-to-br from-slate-400 to-slate-600" />
              Descrição
            </h2>
            <p className="text-sm text-muted-foreground">{task.description ?? "Sem descrição."}</p>
          </div>

          {isWorkspaceTask && (
            <div className="flex flex-col gap-3 rounded-2xl border bg-card p-5">
              <div className="flex items-center justify-between">
                <h2 className="flex items-center gap-2 text-sm font-semibold">
                  <SectionIcon icon={Users} className="bg-gradient-to-br from-blue-400 to-blue-700" />
                  Participantes
                  {participants.length > 0 && (
                    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                      {participants.length}
                    </span>
                  )}
                </h2>
                {canEdit && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5 rounded-lg"
                    onClick={() => setAddParticipantOpen(true)}
                  >
                    <UserPlus className="size-4" />
                    Adicionar
                  </Button>
                )}
              </div>

              {participantsLoading && <Skeleton className="h-14 w-full rounded-xl" />}
              {!participantsLoading && participantsError && (
                <p className="text-sm text-destructive">{participantsError}</p>
              )}
              {!participantsLoading && !participantsError && (
                <div className="flex flex-col gap-2">
                  {participants.map((participant) => {
                    const isTaskAssignee = participant.user_id === task.assignee_id;
                    return (
                      <div key={participant.user_id} className="flex items-center gap-3 rounded-xl border p-2.5">
                        <Avatar size="sm" className="rounded-lg">
                          <AvatarFallback className="rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 text-[11px] font-semibold text-white">
                            {getInitials(participant.name)}
                          </AvatarFallback>
                        </Avatar>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">
                            {participant.name}
                            {participant.user_id === currentUser?.id && (
                              <span className="ml-1.5 text-xs text-muted-foreground">(você)</span>
                            )}
                          </p>
                          <p className="truncate text-xs text-muted-foreground">{participant.email}</p>
                        </div>
                        {isTaskAssignee && (
                          <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                            Responsável
                          </span>
                        )}
                        {canEdit && !isTaskAssignee && (
                          <RemoveParticipantDialog
                            name={participant.name}
                            onConfirm={() => removeParticipant(participant.user_id)}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          <div className="flex flex-col gap-3 rounded-2xl border bg-card p-5">
            <div className="flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-sm font-semibold">
                <SectionIcon icon={ListChecks} className="bg-gradient-to-br from-emerald-400 to-emerald-600" />
                Checklist
              </h2>
              {checklistItems.length > 0 && (
                <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                  {checklistDoneCount} de {checklistItems.length}
                </span>
              )}
            </div>

            {checklistLoading && <Skeleton className="h-14 w-full rounded-xl" />}
            {!checklistLoading && checklistError && (
              <p className="text-sm text-destructive">{checklistError}</p>
            )}
            {!checklistLoading && !checklistError && (
              <>
                {checklistItems.length > 0 && (
                  <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-blue-400 to-emerald-400 transition-all duration-500"
                      style={{ width: `${checklistProgress}%` }}
                    />
                  </div>
                )}
                {checklistItems.length === 0 && (
                  <p className="text-sm text-muted-foreground">Nenhum item ainda.</p>
                )}
                <div className="flex flex-col gap-2">
                  {checklistItems.map((item) => (
                    <ChecklistItemRow
                      key={item.id}
                      description={item.description}
                      isDone={item.is_done}
                      canEdit={isParticipant}
                      onToggle={() => toggleChecklistItem(item.id, !item.is_done)}
                      onRemove={() => removeChecklistItem(item.id)}
                    />
                  ))}
                </div>
                {isParticipant && <AddChecklistItemForm onAdd={handleAddChecklistItem} />}
              </>
            )}
          </div>

          <div className="flex flex-col gap-3 rounded-2xl border bg-card p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <SectionIcon icon={MessageSquare} className="bg-gradient-to-br from-indigo-400 to-indigo-600" />
              Comentários
              {comments.length > 0 && (
                <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                  {comments.length}
                </span>
              )}
            </h2>

            {commentsLoading && <Skeleton className="h-14 w-full rounded-xl" />}
            {!commentsLoading && commentsError && (
              <p className="text-sm text-destructive">{commentsError}</p>
            )}
            {!commentsLoading && !commentsError && (
              <div className="flex flex-col gap-3">
                {comments.length === 0 && (
                  <p className="text-sm text-muted-foreground">Nenhum comentário ainda.</p>
                )}
                {comments.map((comment) => (
                  <div key={comment.id} className="flex items-start gap-3">
                    <Avatar size="sm" className="mt-0.5 rounded-lg">
                      <AvatarFallback className="rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 text-[11px] font-semibold text-white">
                        {getInitials(comment.author_name)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0 flex-1 rounded-xl border bg-muted/40 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-sm font-medium">
                          {comment.author_name}
                          {comment.author_id === currentUser?.id && (
                            <span className="ml-1.5 text-xs text-muted-foreground">(você)</span>
                          )}
                        </p>
                        <span className="shrink-0 text-xs text-muted-foreground">
                          {formatDateTime(comment.created_at)}
                        </span>
                      </div>
                      <p className="mt-1 text-sm whitespace-pre-wrap">{comment.content}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <CommentForm disabled={!isParticipant} onSubmit={handleAddComment} />
          </div>

          <div className="flex flex-col gap-3 rounded-2xl border bg-card p-5">
            <div className="flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-sm font-semibold">
                <SectionIcon icon={Paperclip} className="bg-gradient-to-br from-amber-400 to-amber-600" />
                Anexos
                {attachments.length > 0 && (
                  <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                    {attachments.length}
                  </span>
                )}
              </h2>
              {isParticipant && <AttachmentUploadButton onUpload={uploadFile} />}
            </div>
            <p className="-mt-2 text-xs text-muted-foreground">PNG, JPG, PDF ou TXT · até 10 MB</p>

            {attachmentsLoading && <Skeleton className="h-14 w-full rounded-xl" />}
            {!attachmentsLoading && attachmentsError && (
              <p className="text-sm text-destructive">{attachmentsError}</p>
            )}
            {!attachmentsLoading && !attachmentsError && (
              <div className="flex flex-col gap-2">
                {attachments.length === 0 && (
                  <p className="text-sm text-muted-foreground">Nenhum anexo ainda.</p>
                )}
                {attachments.map((attachment) => (
                  <AttachmentRow
                    key={attachment.id}
                    attachment={attachment}
                    canRemove={attachment.uploaded_by_id === currentUser?.id || isWorkspaceManager}
                    onDownload={() => void downloadAttachment(attachment.id, attachment.original_filename)}
                    onRemove={() => removeAttachment(attachment.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ===== Barra lateral ===== */}
        <div className="flex flex-col gap-5 lg:sticky lg:top-6 lg:col-span-1 lg:self-start">
          <div className="flex flex-col gap-1 rounded-2xl border bg-card p-5">
            <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <SectionIcon icon={ClipboardList} className="bg-gradient-to-br from-blue-400 to-blue-700" />
              Detalhes da tarefa
            </h2>

            <div className="flex items-center justify-between py-2">
              <span className="text-xs text-muted-foreground">Status</span>
              <Select value={task.status} onValueChange={handleStatusChange} disabled={!canEdit}>
                <SelectTrigger
                  size="sm"
                  aria-label="Status"
                  className={cn("h-7 gap-1 rounded-full border-none px-2.5 text-xs font-medium", STATUS_BADGE_CLASS[task.status])}
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(["PENDING", "IN_PROGRESS", "DONE"] as TaskStatus[]).map((option) => (
                    <SelectItem key={option} value={option}>
                      {STATUS_LABEL[option]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <hr className="border-border" />

            <div className="flex items-center justify-between py-2">
              <span className="text-xs text-muted-foreground">Prioridade</span>
              <Select value={task.priority} onValueChange={handlePriorityChange} disabled={!canEdit}>
                <SelectTrigger
                  size="sm"
                  aria-label="Prioridade"
                  className={cn("h-7 gap-1 rounded-full border-none px-2.5 text-xs font-medium", PRIORITY_CHIP_CLASS[task.priority])}
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(["LOW", "MEDIUM", "HIGH", "URGENT"] as TaskPriority[]).map((option) => (
                    <SelectItem key={option} value={option}>
                      {PRIORITY_LABEL[option]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <hr className="border-border" />

            <div className="flex items-center justify-between py-2">
              <span className="text-xs text-muted-foreground">Prazo</span>
              <span className={cn("text-sm font-medium", due?.tone === "danger" && "text-destructive", due?.tone === "warning" && "text-amber-600 dark:text-amber-400")}>
                {task.due_date ? formatDateOnly(task.due_date) : "Sem prazo"}
              </span>
            </div>
            <hr className="border-border" />

            <div className="flex items-center justify-between py-2">
              <span className="text-xs text-muted-foreground">Criada em</span>
              <span className="text-sm font-medium">{formatDateTime(task.created_at)}</span>
            </div>
            <hr className="border-border" />

            <div className="flex items-center justify-between py-2">
              <span className="text-xs text-muted-foreground">Criada por</span>
              <span className="flex items-center gap-2 text-sm font-medium">
                <DetailRowIcon icon={UserRound} className="bg-blue-100 text-blue-600 dark:bg-blue-950 dark:text-blue-300" />
                {memberName(task.creator_id)}
              </span>
            </div>
            <hr className="border-border" />

            <div className="flex items-center justify-between py-2">
              <span className="text-xs text-muted-foreground">Responsável</span>
              <span className="flex items-center gap-2 text-sm font-medium">
                <DetailRowIcon icon={UserRound} className="bg-blue-100 text-blue-600 dark:bg-blue-950 dark:text-blue-300" />
                {memberName(task.assignee_id)}
              </span>
            </div>

            {workspace && (
              <>
                <hr className="border-border" />
                <div className="flex items-center justify-between py-2">
                  <span className="text-xs text-muted-foreground">Workspace</span>
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <DetailRowIcon icon={Building2} className="bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300" />
                    {workspace.name}
                  </span>
                </div>
              </>
            )}
            {project && (
              <>
                <hr className="border-border" />
                <div className="flex items-center justify-between py-2">
                  <span className="text-xs text-muted-foreground">Projeto</span>
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <DetailRowIcon icon={FolderKanban} className="bg-indigo-100 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-300" />
                    {project.name}
                  </span>
                </div>
              </>
            )}
          </div>

          <div className="flex flex-col gap-3 rounded-2xl border bg-card p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <SectionIcon icon={History} className="bg-gradient-to-br from-slate-400 to-slate-600" />
              Histórico
            </h2>

            {historyLoading && <Skeleton className="h-14 w-full rounded-xl" />}
            {!historyLoading && historyError && <p className="text-sm text-destructive">{historyError}</p>}
            {!historyLoading && !historyError && historyEntries.length === 0 && (
              <p className="text-sm text-muted-foreground">Nenhuma alteração registrada ainda.</p>
            )}
            {!historyLoading && !historyError && historyEntries.length > 0 && (
              <div className="flex flex-col">
                {historyEntries.map((entry, index) => (
                  <div key={entry.id} className="flex gap-3">
                    <div className="flex shrink-0 flex-col items-center">
                      <span
                        className={cn(
                          "mt-1 size-2 shrink-0 rounded-full ring-4",
                          HISTORY_DOT_CLASS[entry.field_changed] ?? "bg-slate-400 ring-slate-400/15",
                        )}
                      />
                      {index < historyEntries.length - 1 && <span className="w-px flex-1 bg-border" />}
                    </div>
                    <div className={cn("min-w-0", index < historyEntries.length - 1 ? "pb-4" : "")}>
                      <p className="text-sm">{describeHistoryEntry(entry, memberName)}</p>
                      <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="size-3" />
                        {entry.changed_by_name} · {formatDateTime(entry.changed_at)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {canDelete && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  className="w-fit gap-1.5 self-start px-2 text-sm text-destructive hover:bg-destructive/10 hover:text-destructive"
                >
                  <Trash2 className="size-4" />
                  Excluir tarefa
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Excluir "{task.title}"?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Esta ação remove permanentemente a tarefa, seus comentários, checklist, anexos e
                    histórico. Não é possível desfazer.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                {deleteError && <p className="text-sm text-destructive">{deleteError}</p>}
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={isDeleting}>Cancelar</AlertDialogCancel>
                  <AlertDialogAction onClick={handleDelete} disabled={isDeleting} variant="destructive">
                    {isDeleting ? "Excluindo..." : "Excluir"}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      </div>

      <Sheet open={addParticipantOpen} onOpenChange={setAddParticipantOpen}>
        <SheetContent>
          <SheetHeader>
            <div className="flex items-center gap-2.5">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/20">
                <UserPlus className="size-4 text-white" />
              </div>
              <SheetTitle>Adicionar participante</SheetTitle>
            </div>
          </SheetHeader>
          <div className="px-4 pb-4">
            <AddMemberByEmailForm
              onAdd={handleAddParticipant}
              onCancel={() => setAddParticipantOpen(false)}
              helperText="A pessoa precisa já ser membro do workspace desta tarefa."
            />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
