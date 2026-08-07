import { ArrowLeft, FolderKanban, PlusIcon } from "lucide-react";
import { useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";

import { ProjectForm, type ProjectFormValues } from "@/components/forms/ProjectForm";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useProjects } from "@/hooks/useProjects";
import { useWorkspace } from "@/hooks/useWorkspace";
import type { ProjectCreate } from "@/types/project";

export function ProjectsPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const { workspace } = useWorkspace(workspaceId ?? "");
  const { projects, isLoading, error, createProject } = useProjects(workspaceId ?? "");
  const [formOpen, setFormOpen] = useState(false);

  if (!workspaceId) {
    return <Navigate to="/workspaces" replace />;
  }

  const canCreate = workspace?.my_role === "OWNER" || workspace?.my_role === "ADMIN";

  async function handleSubmit(values: ProjectFormValues) {
    const payload: ProjectCreate = {
      name: values.name,
      description: values.description.trim() === "" ? null : values.description,
    };
    const created = await createProject(payload);
    setFormOpen(false);
    navigate(`/workspaces/${workspaceId}/projects/${created.id}`);
  }

  return (
    <div className="flex flex-col gap-5">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate(`/workspaces/${workspaceId}`)}
        className="w-fit gap-1.5 text-muted-foreground"
      >
        <ArrowLeft className="size-4" />
        {workspace?.name ?? "Workspace"}
      </Button>

      <PageHeader
        icon={FolderKanban}
        title="Projetos"
        description={
          workspace ? `Projetos de "${workspace.name}" — só Owner e Admin criam novos.` : "Carregando..."
        }
      />

      {canCreate && (
        <div className="flex justify-end">
          <Button
            onClick={() => setFormOpen(true)}
            className="h-10 gap-1.5 rounded-lg bg-blue-600 px-5 text-sm text-white shadow-sm shadow-blue-600/20 hover:bg-blue-500"
          >
            <PlusIcon className="size-4" />
            Novo projeto
          </Button>
        </div>
      )}

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
      )}

      {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

      {!isLoading && !error && projects.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed py-16 text-center">
          <FolderKanban className="size-8 text-muted-foreground/30" strokeWidth={1.5} />
          <p className="text-sm text-muted-foreground">
            {canCreate
              ? 'Nenhum projeto ainda. Crie o primeiro clicando em "Novo projeto".'
              : "Nenhum projeto neste workspace ainda."}
          </p>
        </div>
      )}

      {!isLoading && !error && projects.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <button
              key={project.id}
              type="button"
              onClick={() => navigate(`/workspaces/${workspaceId}/projects/${project.id}`)}
              className="group flex flex-col gap-3 rounded-xl border bg-card p-4 text-left shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/20">
                <FolderKanban className="size-5 text-white" strokeWidth={2.25} />
              </div>
              <div>
                <p className="font-semibold">{project.name}</p>
                <p className="line-clamp-2 text-sm text-muted-foreground">
                  {project.description ?? "Sem descrição."}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}

      <Sheet open={formOpen} onOpenChange={setFormOpen}>
        <SheetContent>
          <SheetHeader>
            <div className="flex items-center gap-2.5">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/20">
                <PlusIcon className="size-4 text-white" />
              </div>
              <SheetTitle>Novo projeto</SheetTitle>
            </div>
          </SheetHeader>
          <div className="px-4 pb-4">
            <ProjectForm onSubmit={handleSubmit} onCancel={() => setFormOpen(false)} />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
