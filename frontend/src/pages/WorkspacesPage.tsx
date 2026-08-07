import { Building2, PlusIcon } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { WorkspaceForm, type WorkspaceFormValues } from "@/components/forms/WorkspaceForm";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import { cn } from "@/lib/utils";
import type { WorkspaceCreate } from "@/types/workspace";
import { ROLE_BADGE_CLASS, ROLE_ICON, ROLE_LABEL } from "@/utils/workspaceRole";

export function WorkspacesPage() {
  const { workspaces, isLoading, error, createWorkspace } = useWorkspaces();
  const [formOpen, setFormOpen] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(values: WorkspaceFormValues) {
    const payload: WorkspaceCreate = {
      name: values.name,
      description: values.description.trim() === "" ? null : values.description,
    };
    const created = await createWorkspace(payload);
    setFormOpen(false);
    navigate(`/workspaces/${created.id}`);
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon={Building2}
        title="Workspaces"
        description="Espaços colaborativos para organizar projetos e tarefas com sua equipe."
      />

      <div className="flex justify-end">
        <Button
          onClick={() => setFormOpen(true)}
          className="h-10 gap-1.5 rounded-lg bg-blue-600 px-5 text-sm text-white shadow-sm shadow-blue-600/20 hover:bg-blue-500"
        >
          <PlusIcon className="size-4" />
          Novo workspace
        </Button>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}

      {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

      {!isLoading && !error && workspaces.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed py-16 text-center">
          <Building2 className="size-8 text-muted-foreground/30" strokeWidth={1.5} />
          <p className="text-sm text-muted-foreground">
            Você ainda não participa de nenhum workspace. Crie o primeiro clicando em
            &quot;Novo workspace&quot;.
          </p>
        </div>
      )}

      {!isLoading && !error && workspaces.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {workspaces.map((workspace) => {
            const RoleIcon = ROLE_ICON[workspace.my_role];
            return (
              <button
                key={workspace.id}
                type="button"
                onClick={() => navigate(`/workspaces/${workspace.id}`)}
                className="group flex flex-col gap-3 rounded-xl border bg-card p-4 text-left shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/20">
                    <Building2 className="size-5 text-white" strokeWidth={2.25} />
                  </div>
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
                      ROLE_BADGE_CLASS[workspace.my_role],
                    )}
                  >
                    <RoleIcon className="size-2.5" />
                    {ROLE_LABEL[workspace.my_role]}
                  </span>
                </div>
                <div>
                  <p className="font-semibold">{workspace.name}</p>
                  <p className="line-clamp-2 text-sm text-muted-foreground">
                    {workspace.description ?? "Sem descrição."}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      )}

      <Sheet open={formOpen} onOpenChange={setFormOpen}>
        <SheetContent>
          <SheetHeader>
            <div className="flex items-center gap-2.5">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/20">
                <PlusIcon className="size-4 text-white" />
              </div>
              <SheetTitle>Novo workspace</SheetTitle>
            </div>
          </SheetHeader>
          <div className="px-4 pb-4">
            <WorkspaceForm onSubmit={handleSubmit} onCancel={() => setFormOpen(false)} />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
