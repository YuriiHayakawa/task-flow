import {
  ArrowLeft,
  Calendar,
  FolderKanban,
  PencilIcon,
  PlusIcon,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";

import { ProjectForm, type ProjectFormValues } from "@/components/forms/ProjectForm";
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
import type { ProjectUpdate } from "@/types/project";
import {
  DUE_CHIP_CLASS,
  PRIORITY_CHIP_CLASS,
  PRIORITY_LABEL,
  STATUS_BADGE_CLASS,
  STATUS_ICON,
  STATUS_LABEL,
  describeDueDate,
} from "@/utils/taskStyle";

export function ProjectDetailPage() {
  const { workspaceId, projectId } = useParams<{ workspaceId: string; projectId: string }>();
  const navigate = useNavigate();
  const { workspace } = useWorkspace(workspaceId ?? "");
  const { members } = useWorkspaceMembers(workspaceId ?? "");
  const { project, isLoading, error, updateProject, deleteProject } = useProject(projectId ?? "");
  const { tasks, isLoading: tasksLoading, error: tasksError } = useTasks({ project_id: projectId ?? "" });
  const [editOpen, setEditOpen] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

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
    setDeleteError(null);
    setIsDeleting(true);
    try {
      await deleteProject();
      navigate(`/workspaces/${workspaceId}/projects`);
    } catch {
      setDeleteError("Não foi possível excluir este projeto. Tente novamente.");
      setIsDeleting(false);
    }
  }

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

      {isLoading && <Skeleton className="h-28 w-full rounded-2xl" />}

      {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

      {!isLoading && !error && project && (
        <>
          <PageHeader
            icon={FolderKanban}
            title={project.name}
            description={project.description ?? "Sem descrição."}
          />

          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap gap-2">
              {canManage && (
                <>
                  <Button
                    variant="outline"
                    className="gap-1.5 rounded-lg"
                    onClick={() => setEditOpen(true)}
                  >
                    <PencilIcon className="size-4" />
                    Editar
                  </Button>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="outline"
                        className="gap-1.5 rounded-lg border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
                      >
                        <Trash2 className="size-4" />
                        Excluir projeto
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Excluir "{project.name}"?</AlertDialogTitle>
                        <AlertDialogDescription>
                          As tarefas deste projeto não são excluídas — elas continuam no
                          workspace, sem projeto vinculado. Comentários, checklists, anexos e
                          histórico permanecem intactos.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      {deleteError && <p className="text-sm text-destructive">{deleteError}</p>}
                      <AlertDialogFooter>
                        <AlertDialogCancel disabled={isDeleting}>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={handleDelete}
                          disabled={isDeleting}
                          variant="destructive"
                        >
                          {isDeleting ? "Excluindo..." : "Excluir"}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </>
              )}
            </div>
            <Button
              onClick={() => navigate(`/tasks/new?workspace_id=${workspaceId}&project_id=${projectId}`)}
              className="h-10 gap-1.5 rounded-lg bg-blue-600 px-5 text-sm text-white shadow-sm shadow-blue-600/20 hover:bg-blue-500"
            >
              <PlusIcon className="size-4" />
              Nova tarefa
            </Button>
          </div>

          {tasksLoading && (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-16 w-full rounded-xl" />
              <Skeleton className="h-16 w-full rounded-xl" />
            </div>
          )}

          {!tasksLoading && tasksError && <p className="text-sm text-destructive">{tasksError}</p>}

          {!tasksLoading && !tasksError && tasks.length === 0 && (
            <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed py-14 text-center">
              <p className="text-sm text-muted-foreground">
                Nenhuma tarefa neste projeto ainda. Crie a primeira clicando em "Nova tarefa".
              </p>
            </div>
          )}

          {!tasksLoading && !tasksError && tasks.length > 0 && (
            <div className="flex flex-col gap-2">
              {tasks.map((task) => {
                const StatusIcon = STATUS_ICON[task.status];
                const due = task.due_date ? describeDueDate(task.due_date, task.status === "DONE") : null;
                return (
                  <button
                    key={task.id}
                    type="button"
                    onClick={() => navigate(`/tasks/${task.id}`)}
                    className="flex flex-wrap items-center gap-3 rounded-xl border bg-card p-3 text-left transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
                  >
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium",
                        STATUS_BADGE_CLASS[task.status],
                      )}
                    >
                      <StatusIcon className="size-3" />
                      {STATUS_LABEL[task.status]}
                    </span>
                    <p
                      className={cn(
                        "min-w-0 flex-1 truncate text-sm font-medium",
                        task.status === "DONE" && "text-muted-foreground line-through",
                      )}
                    >
                      {task.title}
                    </p>
                    <span className="text-xs text-muted-foreground">{assigneeName(task.assignee_id)}</span>
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
                        <Calendar className="size-2.5" />
                        {due.label}
                      </span>
                    )}
                  </button>
                );
              })}
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
