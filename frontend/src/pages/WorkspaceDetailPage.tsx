import { ArrowLeft, Building2, PencilIcon, Trash2, Users } from "lucide-react";
import { useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";

import { WorkspaceForm, type WorkspaceFormValues } from "@/components/forms/WorkspaceForm";
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
import { useWorkspace } from "@/hooks/useWorkspace";
import { cn } from "@/lib/utils";
import type { WorkspaceUpdate } from "@/types/workspace";
import { ROLE_BADGE_CLASS, ROLE_ICON, ROLE_LABEL } from "@/utils/workspaceRole";

export function WorkspaceDetailPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const { workspace, isLoading, error, updateWorkspace, deleteWorkspace } = useWorkspace(
    workspaceId ?? "",
  );
  const [editOpen, setEditOpen] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  if (!workspaceId) {
    return <Navigate to="/workspaces" replace />;
  }

  async function handleEditSubmit(values: WorkspaceFormValues) {
    const payload: WorkspaceUpdate = {
      name: values.name,
      description: values.description.trim() === "" ? null : values.description,
    };
    await updateWorkspace(payload);
    setEditOpen(false);
  }

  async function handleDelete() {
    setDeleteError(null);
    setIsDeleting(true);
    try {
      await deleteWorkspace();
      navigate("/workspaces");
    } catch {
      setDeleteError("Não foi possível excluir este workspace. Tente novamente.");
      setIsDeleting(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate("/workspaces")}
        className="w-fit gap-1.5 text-muted-foreground"
      >
        <ArrowLeft className="size-4" />
        Workspaces
      </Button>

      {isLoading && <Skeleton className="h-28 w-full rounded-2xl" />}

      {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

      {!isLoading && !error && workspace && (
        <>
          <PageHeader
            icon={Building2}
            title={workspace.name}
            description={workspace.description ?? "Sem descrição."}
          >
            <div className="flex flex-wrap items-center gap-2">
              {(() => {
                const RoleIcon = ROLE_ICON[workspace.my_role];
                return (
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium",
                      ROLE_BADGE_CLASS[workspace.my_role],
                    )}
                  >
                    <RoleIcon className="size-3" />
                    Você é {ROLE_LABEL[workspace.my_role]}
                  </span>
                );
              })()}
            </div>
          </PageHeader>

          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              className="gap-1.5 rounded-lg"
              onClick={() => navigate(`/workspaces/${workspace.id}/members`)}
            >
              <Users className="size-4" />
              Ver membros
            </Button>
            {workspace.my_role === "OWNER" && (
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
                      Excluir workspace
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Excluir "{workspace.name}"?</AlertDialogTitle>
                      <AlertDialogDescription>
                        Esta ação remove permanentemente o workspace, seus projetos, tarefas e
                        todos os dados relacionados (comentários, checklists, anexos, histórico).
                        Não é possível desfazer.
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

          <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed py-14 text-center">
            <p className="text-sm text-muted-foreground">
              Projetos e tarefas deste workspace chegam na próxima fase.
            </p>
          </div>

          <Sheet open={editOpen} onOpenChange={setEditOpen}>
            <SheetContent>
              <SheetHeader>
                <div className="flex items-center gap-2.5">
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/20">
                    <PencilIcon className="size-4 text-white" />
                  </div>
                  <SheetTitle>Editar workspace</SheetTitle>
                </div>
              </SheetHeader>
              <div className="px-4 pb-4">
                <WorkspaceForm
                  workspace={workspace}
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
