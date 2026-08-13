import {
  ArrowLeft,
  Building2,
  Calendar,
  CheckCircle2,
  FolderKanban,
  ListTodo,
  PencilIcon,
  Trash2,
  UserPlus,
  UserRound,
  Users,
} from "lucide-react";
import { useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";

import { AddMemberByEmailForm } from "@/components/forms/AddMemberByEmailForm";
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
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/contexts/AuthContext";
import { useProject } from "@/hooks/useProject";
import { useTask } from "@/hooks/useTask";
import { useTaskMembers } from "@/hooks/useTaskMembers";
import { useWorkspace } from "@/hooks/useWorkspace";
import { useWorkspaceMembers } from "@/hooks/useWorkspaceMembers";
import { cn } from "@/lib/utils";
import * as userService from "@/services/userService";
import { getApiErrorMessage } from "@/utils/apiErrorMessage";
import { getInitials } from "@/utils/initials";
import {
  PRIORITY_CHIP_CLASS,
  PRIORITY_LABEL,
  STATUS_BADGE_CLASS,
  STATUS_ICON,
  STATUS_LABEL,
} from "@/utils/taskStyle";

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

  async function handleAddParticipant(email: string) {
    const found = await userService.lookupByEmail(email);
    await addParticipant({ user_id: found.id });
    setAddParticipantOpen(false);
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

      <PageHeader
        icon={ListTodo}
        title={task.title}
        description={task.description ?? "Sem descrição."}
      >
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium",
              STATUS_BADGE_CLASS[task.status],
            )}
          >
            <StatusIcon className="size-3" />
            {STATUS_LABEL[task.status]}
          </span>
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium",
              PRIORITY_CHIP_CLASS[task.priority],
            )}
          >
            {PRIORITY_LABEL[task.priority]}
          </span>
          {task.due_date && (
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
              <Calendar className="size-3" />
              {new Date(`${task.due_date}T00:00:00`).toLocaleDateString("pt-BR")}
            </span>
          )}
        </div>
      </PageHeader>

      <div className="grid grid-cols-1 gap-4 rounded-2xl border bg-card p-5 sm:grid-cols-2">
        <div className="flex items-center gap-2 text-sm">
          <UserRound className="size-4 text-muted-foreground" />
          <span className="text-muted-foreground">Responsável:</span>
          <span className="font-medium">{memberName(task.assignee_id)}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <UserRound className="size-4 text-muted-foreground" />
          <span className="text-muted-foreground">Criada por:</span>
          <span className="font-medium">{memberName(task.creator_id)}</span>
        </div>
        {workspace && (
          <div className="flex items-center gap-2 text-sm">
            <Building2 className="size-4 text-muted-foreground" />
            <span className="text-muted-foreground">Workspace:</span>
            <span className="font-medium">{workspace.name}</span>
          </div>
        )}
        {project && (
          <div className="flex items-center gap-2 text-sm">
            <FolderKanban className="size-4 text-muted-foreground" />
            <span className="text-muted-foreground">Projeto:</span>
            <span className="font-medium">{project.name}</span>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {canEdit && (
          <Button
            variant="outline"
            className="gap-1.5 rounded-lg"
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
            className="gap-1.5 rounded-lg"
            onClick={() => navigate(`/tasks/${task.id}/edit`)}
          >
            <PencilIcon className="size-4" />
            Editar
          </Button>
        )}
        {canDelete && (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="outline"
                className="gap-1.5 rounded-lg border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                <Trash2 className="size-4" />
                Excluir
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

      {isWorkspaceTask && (
        <div className="flex flex-col gap-3 rounded-2xl border bg-card p-5">
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-1.5 text-sm font-semibold">
              <Users className="size-4 text-muted-foreground" />
              Participantes
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
                  <div
                    key={participant.user_id}
                    className="flex items-center gap-3 rounded-xl border p-2.5"
                  >
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
