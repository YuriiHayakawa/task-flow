import { ArrowLeft, ArrowRight, Calendar, FolderKanban, PlusIcon } from "lucide-react";
import { useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";

import { ProjectForm, type ProjectFormValues } from "@/components/forms/ProjectForm";
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
import { cn } from "@/lib/utils";
import type { Project, ProjectCreate } from "@/types/project";
import { pickAccentColor } from "@/utils/accentColor";

interface ProjectsHeroProps {
  workspaceId: string;
  workspaceName: string;
  total: number;
  canCreate: boolean;
  onCreate: () => void;
}

/** Mesma identidade escura dos outros heróis do app — o badge de ícone usa
 * a MESMA cor determinística do workspace-pai (`pickAccentColor`), dando
 * continuidade visual: a cor "segue" o usuário de Workspaces → dentro do
 * workspace → aqui em Projetos. */
function ProjectsHero({ workspaceId, workspaceName, total, canCreate, onCreate }: ProjectsHeroProps) {
  const accent = pickAccentColor(workspaceId);

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
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
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
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">Projetos</h1>
              <p className="text-xs text-slate-400 sm:text-sm">
                Projetos do workspace &quot;{workspaceName}&quot;.
              </p>
            </div>
          </div>
          {canCreate && (
            <Button
              onClick={onCreate}
              className="h-10 w-fit gap-1.5 rounded-xl bg-white px-4 text-sm font-semibold text-[#05070f] shadow-lg shadow-black/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-xl hover:shadow-blue-500/10"
            >
              <PlusIcon className="size-4" />
              Novo projeto
            </Button>
          )}
        </div>

        {total > 0 && (
          <div className="flex items-center gap-2.5 border-t border-white/10 pt-4">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-blue-400/15">
              <FolderKanban className="size-4 text-blue-300" />
            </div>
            <div className="leading-tight">
              <p className="text-xl font-bold tabular-nums text-white">{total}</p>
              <p className="text-[11px] font-medium text-slate-400">
                {total === 1 ? "projeto" : "projetos"}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface ProjectCardProps {
  project: Project;
  onOpen: () => void;
}

/** Mesmo tratamento do `WorkspaceCard` (cor determinística por id, glow no
 * hover, seta que desliza) — grade de projetos ganha a mesma vida que a
 * grade de workspaces. */
function ProjectCard({ project, onOpen }: ProjectCardProps) {
  const accent = pickAccentColor(project.id);
  const createdLabel = new Date(project.created_at).toLocaleDateString("pt-BR");

  return (
    <button
      type="button"
      onClick={onOpen}
      className="group relative flex flex-col gap-4 overflow-hidden rounded-2xl border bg-card p-5 text-left shadow-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-lg"
    >
      <div
        className={cn(
          "pointer-events-none absolute -top-10 -right-10 size-28 rounded-full opacity-0 blur-2xl transition-opacity duration-300 group-hover:opacity-100",
          accent.glowClass,
        )}
      />

      <div className="relative">
        <div
          className={cn(
            "flex size-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br shadow-md transition-transform duration-200 group-hover:scale-105",
            accent.gradientClass,
            accent.shadowClass,
          )}
        >
          <FolderKanban className="size-5 text-white" strokeWidth={2.25} />
        </div>
      </div>

      <div className="relative flex-1">
        <p className="text-base font-semibold">{project.name}</p>
        <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
          {project.description ?? "Sem descrição."}
        </p>
      </div>

      <div className="relative flex items-center justify-between border-t pt-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <Calendar className="size-3" />
          Criado em {createdLabel}
        </span>
        <ArrowRight className="size-3.5 -translate-x-1 opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:opacity-100" />
      </div>
    </button>
  );
}

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

      <ProjectsHero
        workspaceId={workspaceId}
        workspaceName={workspace?.name ?? "..."}
        total={projects.length}
        canCreate={canCreate}
        onCreate={() => setFormOpen(true)}
      />

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-40 w-full rounded-2xl" />
          <Skeleton className="h-40 w-full rounded-2xl" />
          <Skeleton className="h-40 w-full rounded-2xl" />
        </div>
      )}

      {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

      {!isLoading && !error && projects.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed py-16 text-center">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-blue-500/10">
            <FolderKanban className="size-7 text-blue-500/60" strokeWidth={1.5} />
          </div>
          <p className="max-w-xs text-sm text-muted-foreground">
            {canCreate
              ? 'Nenhum projeto ainda. Crie o primeiro clicando em "Novo projeto".'
              : "Nenhum projeto neste workspace ainda."}
          </p>
        </div>
      )}

      {!isLoading && !error && projects.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onOpen={() => navigate(`/workspaces/${workspaceId}/projects/${project.id}`)}
            />
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
