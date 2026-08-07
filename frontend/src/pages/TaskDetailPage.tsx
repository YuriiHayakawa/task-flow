import {
  ArrowLeft,
  Building2,
  Calendar,
  CheckCircle2,
  FolderKanban,
  ListTodo,
  PencilIcon,
  Trash2,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";

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
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/contexts/AuthContext";
import { useProject } from "@/hooks/useProject";
import { useTask } from "@/hooks/useTask";
import { useWorkspace } from "@/hooks/useWorkspace";
import { useWorkspaceMembers } from "@/hooks/useWorkspaceMembers";
import { cn } from "@/lib/utils";
import {
  PRIORITY_CHIP_CLASS,
  PRIORITY_LABEL,
  STATUS_BADGE_CLASS,
  STATUS_ICON,
  STATUS_LABEL,
} from "@/utils/taskStyle";

export function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const { task, isLoading, error, updateTask, deleteTask } = useTask(taskId ?? "");
  const isWorkspaceTask = Boolean(task?.workspace_id);
  const { workspace } = useWorkspace(isWorkspaceTask ? (task!.workspace_id as string) : "");
  const { members } = useWorkspaceMembers(isWorkspaceTask ? (task!.workspace_id as string) : "");
  const { project } = useProject(task?.project_id ?? "");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isToggling, setIsToggling] = useState(false);

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
    </div>
  );
}
