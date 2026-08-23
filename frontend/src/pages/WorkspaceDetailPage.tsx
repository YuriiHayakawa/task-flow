import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Calendar,
  FolderKanban,
  Lock,
  PencilIcon,
  Trash2,
  Users,
  type LucideIcon,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";

import { WorkspaceForm, type WorkspaceFormValues } from "@/components/forms/WorkspaceForm";
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
import { Avatar, AvatarFallback, AvatarGroup, AvatarGroupCount } from "@/components/ui/avatar";
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
import { useWorkspaceMembers } from "@/hooks/useWorkspaceMembers";
import { cn } from "@/lib/utils";
import type { Workspace, WorkspaceUpdate } from "@/types/workspace";
import { pickAccentColor } from "@/utils/accentColor";
import { getInitials } from "@/utils/initials";
import { ROLE_HERO_CHIP_CLASS, ROLE_ICON, ROLE_LABEL } from "@/utils/workspaceRole";

interface DeleteWorkspaceDialogProps {
  workspaceName: string;
  onConfirm: () => Promise<void>;
}

/** Mesmo padrão auto-contido dos diálogos de exclusão do resto do app
 * (`RemoveMemberDialog`, `RemoveRecurringTaskDialog`): estado de erro e de
 * "excluindo..." vivem aqui dentro, não na página. */
function DeleteWorkspaceDialog({ workspaceName, onConfirm }: DeleteWorkspaceDialogProps) {
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirm() {
    setError(null);
    setIsDeleting(true);
    try {
      await onConfirm();
    } catch {
      setError("Não foi possível excluir este workspace. Tente novamente.");
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
          <AlertDialogTitle>Excluir "{workspaceName}"?</AlertDialogTitle>
          <AlertDialogDescription>
            Esta ação remove permanentemente o workspace, seus projetos, tarefas e todos os dados
            relacionados (comentários, checklists, anexos, histórico). Não é possível desfazer.
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

interface WorkspaceHeroProps {
  workspace: Workspace;
  canManage: boolean;
  onEdit: () => void;
  onDelete: () => Promise<void>;
}

/** Cabeçalho próprio, mesma identidade escura dos outros heróis do app —
 * com um fio visual a mais: a cor do badge de ícone é a MESMA cor
 * determinística do cartão desse workspace na listagem (`pickAccentColor`),
 * então abrir um workspace "continua" a cor de onde o usuário clicou. */
function WorkspaceHero({ workspace, canManage, onEdit, onDelete }: WorkspaceHeroProps) {
  const accent = pickAccentColor(workspace.id);
  const RoleIcon = ROLE_ICON[workspace.my_role];
  const createdLabel = new Date(workspace.created_at).toLocaleDateString("pt-BR");

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0b1220] via-[#0a0f1e] to-[#05070f] p-5 shadow-xl shadow-black/20 sm:p-6">
      <div className="blob-drift-a pointer-events-none absolute -top-20 -left-14 size-56 rounded-full bg-blue-600/25 blur-[80px]" />
      <div className="blob-drift-b pointer-events-none absolute -right-16 -bottom-20 size-64 rounded-full bg-violet-500/20 blur-[90px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] bg-[size:32px_32px]" />
      <Building2
        className="pointer-events-none absolute -right-8 -bottom-10 size-44 -rotate-12 text-blue-500/[0.06]"
        strokeWidth={1}
      />

      <div className="relative flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="relative flex size-12 shrink-0 items-center justify-center">
            <div className={cn("absolute inset-0 rounded-xl opacity-70 blur-md", accent.glowClass)} />
            <div
              className={cn(
                "relative flex size-12 items-center justify-center rounded-xl bg-gradient-to-br shadow-lg",
                accent.gradientClass,
                accent.shadowClass,
              )}
            >
              <Building2 className="size-6 text-white" strokeWidth={2.25} />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
              {workspace.name}
            </h1>
            <p className="text-xs text-slate-400 sm:text-sm">
              {workspace.description ?? "Sem descrição."}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold",
                  ROLE_HERO_CHIP_CLASS[workspace.my_role],
                )}
              >
                <RoleIcon className="size-3" />
                Você é {ROLE_LABEL[workspace.my_role]}
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
                <Calendar className="size-3" />
                Criado em {createdLabel}
              </span>
            </div>
          </div>
        </div>

        {canManage && (
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={onEdit}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 text-xs font-semibold text-slate-200 transition-colors hover:bg-white/10"
            >
              <PencilIcon className="size-3.5" />
              Editar
            </button>
            <DeleteWorkspaceDialog workspaceName={workspace.name} onConfirm={onDelete} />
          </div>
        )}
      </div>
    </div>
  );
}

interface OverviewSectionProps {
  icon: LucideIcon;
  iconWrapperClass: string;
  title: string;
  count: number;
  onViewAll: () => void;
  children: ReactNode;
}

/** Casca compartilhada pelas duas seções de visão geral (Projetos/Membros)
 * — mesmo cabeçalho (ícone + título + contagem real + "Ver todos"), só o
 * conteúdo muda. */
function OverviewSection({
  icon: Icon,
  iconWrapperClass,
  title,
  count,
  onViewAll,
  children,
}: OverviewSectionProps) {
  return (
    <div className="rounded-2xl border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg", iconWrapperClass)}>
            <Icon className="size-4" />
          </div>
          <div className="flex items-center gap-2">
            <p className="font-semibold">{title}</p>
            <span className="flex size-5 items-center justify-center rounded-full bg-muted text-[11px] font-semibold tabular-nums text-muted-foreground">
              {count}
            </span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onViewAll}
          className="gap-1 text-muted-foreground hover:text-foreground"
        >
          Ver todos
          <ArrowRight className="size-3.5" />
        </Button>
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

export function WorkspaceDetailPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const { workspace, isLoading, error, updateWorkspace, deleteWorkspace } = useWorkspace(
    workspaceId ?? "",
  );
  const { projects, isLoading: isLoadingProjects } = useProjects(workspaceId ?? "");
  const { members, isLoading: isLoadingMembers } = useWorkspaceMembers(workspaceId ?? "");
  const [editOpen, setEditOpen] = useState(false);

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
    await deleteWorkspace();
    navigate("/workspaces");
  }

  const canManage = workspace?.my_role === "OWNER";
  const previewProjects = projects.slice(0, 4);
  const remainingProjects = projects.length - previewProjects.length;
  const previewMembers = members.slice(0, 8);
  const remainingMembers = members.length - previewMembers.length;

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

      {isLoading && <Skeleton className="h-40 w-full rounded-2xl" />}

      {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

      {!isLoading && !error && workspace && (
        <>
          <WorkspaceHero
            workspace={workspace}
            canManage={canManage}
            onEdit={() => setEditOpen(true)}
            onDelete={handleDelete}
          />

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <OverviewSection
              icon={FolderKanban}
              iconWrapperClass="bg-blue-500/10 text-blue-600 dark:text-blue-400"
              title="Projetos"
              count={projects.length}
              onViewAll={() => navigate(`/workspaces/${workspace.id}/projects`)}
            >
              {isLoadingProjects && (
                <div className="flex flex-col gap-2">
                  <Skeleton className="h-14 w-full rounded-xl" />
                  <Skeleton className="h-14 w-full rounded-xl" />
                </div>
              )}

              {!isLoadingProjects && projects.length === 0 && (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  Nenhum projeto ainda.
                </p>
              )}

              {!isLoadingProjects && previewProjects.length > 0 && (
                <div className="flex flex-col gap-2">
                  {previewProjects.map((project) =>
                    project.is_member ? (
                      <button
                        key={project.id}
                        type="button"
                        onClick={() => navigate(`/workspaces/${workspace.id}/projects/${project.id}`)}
                        className="group flex items-center gap-3 rounded-xl border p-3 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-sm"
                      >
                        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-sm shadow-blue-900/20">
                          <FolderKanban className="size-4 text-white" strokeWidth={2.25} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{project.name}</p>
                          <p className="truncate text-xs text-muted-foreground">
                            {project.description ?? "Sem descrição."}
                          </p>
                        </div>
                      </button>
                    ) : (
                      // 003-membros-projeto/FR-006: só ocorre para Admin (vê
                      // a listagem completa mas não participa de todos) —
                      // sem navegação, mesmo tratamento de ProjectsPage.tsx.
                      <div
                        key={project.id}
                        aria-label={`${project.name} — sem acesso`}
                        className="flex cursor-not-allowed items-center gap-3 rounded-xl border bg-muted/40 p-3 opacity-75"
                      >
                        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-sm shadow-blue-900/20 grayscale">
                          <FolderKanban className="size-4 text-white" strokeWidth={2.25} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{project.name}</p>
                          <p className="truncate text-xs text-muted-foreground">
                            {project.description ?? "Sem descrição."}
                          </p>
                        </div>
                        <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                          <Lock className="size-2.5" />
                          Sem acesso
                        </span>
                      </div>
                    ),
                  )}
                  {remainingProjects > 0 && (
                    <p className="pt-1 text-center text-xs text-muted-foreground">
                      +{remainingProjects} {remainingProjects === 1 ? "outro projeto" : "outros projetos"}
                    </p>
                  )}
                </div>
              )}
            </OverviewSection>

            <OverviewSection
              icon={Users}
              iconWrapperClass="bg-violet-500/10 text-violet-600 dark:text-violet-400"
              title="Membros"
              count={members.length}
              onViewAll={() => navigate(`/workspaces/${workspace.id}/members`)}
            >
              {isLoadingMembers && <Skeleton className="h-10 w-48 rounded-full" />}

              {!isLoadingMembers && members.length === 0 && (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  Nenhum membro ainda.
                </p>
              )}

              {!isLoadingMembers && previewMembers.length > 0 && (
                <div className="flex flex-col gap-3">
                  <AvatarGroup>
                    {previewMembers.map((member) => (
                      <Avatar key={member.user_id} title={member.name}>
                        <AvatarFallback className="bg-gradient-to-br from-blue-400 to-blue-700 text-xs font-semibold text-white">
                          {getInitials(member.name)}
                        </AvatarFallback>
                      </Avatar>
                    ))}
                    {remainingMembers > 0 && <AvatarGroupCount>+{remainingMembers}</AvatarGroupCount>}
                  </AvatarGroup>
                  <p className="text-xs text-muted-foreground">
                    {members.length === 1
                      ? "1 pessoa participa deste workspace."
                      : `${members.length} pessoas participam deste workspace.`}
                  </p>
                </div>
              )}
            </OverviewSection>
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
