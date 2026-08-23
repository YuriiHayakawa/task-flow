import { ArrowRight, Building2, Calendar, PlusIcon } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { WorkspaceForm, type WorkspaceFormValues } from "@/components/forms/WorkspaceForm";
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
import type { Workspace, WorkspaceCreate, WorkspaceRole } from "@/types/workspace";
import { pickAccentColor } from "@/utils/accentColor";
import {
  ROLE_BADGE_CLASS,
  ROLE_HERO_CHIP_CLASS,
  ROLE_ICON,
  ROLE_LABEL,
} from "@/utils/workspaceRole";

interface RoleCountChipProps {
  role: WorkspaceRole;
  count: number;
}

function RoleCountChip({ role, count }: RoleCountChipProps) {
  const Icon = ROLE_ICON[role];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold tabular-nums",
        ROLE_HERO_CHIP_CLASS[role],
      )}
    >
      <Icon className="size-2.5" />
      {count} {ROLE_LABEL[role]}
      {count > 1 ? "s" : ""}
    </span>
  );
}

interface WorkspacesHeroProps {
  total: number;
  ownerCount: number;
  adminCount: number;
  memberCount: number;
  onCreate: () => void;
}

/** Cabeçalho próprio de "Workspaces" — mesma identidade visual dos heróis
 * de "Minhas tarefas"/"Tarefas Fixas" (fundo azul-marinho, malha de pontos,
 * blobs), com um resumo honesto aos dados que já temos: total de
 * workspaces e a composição por role (Owner/Admin/Member), sem inventar
 * contagem de projetos/membros que a API de listagem não retorna. */
function WorkspacesHero({ total, ownerCount, adminCount, memberCount, onCreate }: WorkspacesHeroProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0b1220] via-[#0a0f1e] to-[#05070f] p-5 shadow-xl shadow-black/20 sm:p-6">
      <div className="blob-drift-a pointer-events-none absolute -top-20 -left-14 size-56 rounded-full bg-blue-600/25 blur-[80px]" />
      <div className="blob-drift-b pointer-events-none absolute -right-16 -bottom-20 size-64 rounded-full bg-violet-500/20 blur-[90px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] bg-[size:32px_32px]" />
      <Building2
        className="pointer-events-none absolute -right-8 -bottom-10 size-44 -rotate-12 text-blue-500/[0.06]"
        strokeWidth={1}
      />

      <div className="relative flex flex-col gap-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="relative flex size-10 shrink-0 items-center justify-center">
              <div className="absolute inset-0 rounded-xl bg-blue-500/30 blur-md" />
              <div className="relative flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-400 to-blue-700 shadow-lg shadow-blue-900/40">
                <Building2 className="size-5 text-white" strokeWidth={2.25} />
              </div>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
                Workspaces
              </h1>
              <p className="text-xs text-slate-400 sm:text-sm">
                Espaços colaborativos para organizar projetos e tarefas com sua equipe.
              </p>
            </div>
          </div>
          <Button
            onClick={onCreate}
            className="h-10 w-fit gap-1.5 rounded-xl bg-white px-4 text-sm font-semibold text-[#05070f] shadow-lg shadow-black/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-xl hover:shadow-blue-500/10"
          >
            <PlusIcon className="size-4" />
            Novo workspace
          </Button>
        </div>

        {total > 0 && (
          <div className="flex flex-col gap-3 border-t border-white/10 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2.5">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-blue-400/15">
                <Building2 className="size-4 text-blue-300" />
              </div>
              <div className="leading-tight">
                <p className="text-xl font-bold tabular-nums text-white">{total}</p>
                <p className="text-[11px] font-medium text-slate-400">
                  {total === 1 ? "workspace" : "workspaces"}
                </p>
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-1.5">
              {ownerCount > 0 && <RoleCountChip role="OWNER" count={ownerCount} />}
              {adminCount > 0 && <RoleCountChip role="ADMIN" count={adminCount} />}
              {memberCount > 0 && <RoleCountChip role="MEMBER" count={memberCount} />}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface WorkspaceCardProps {
  workspace: Workspace;
  onOpen: () => void;
}

/** Cartão com identidade própria por workspace: a cor do badge de ícone é
 * determinística a partir do `id` (`pickAccentColor`), não fixa e azul em
 * todo lugar — dá "vida" à grade sem inventar nenhum dado. O resto do
 * cartão só mostra campos reais (`name`/`description`/`created_at`/
 * `my_role`), nada fabricado (contagem de membros/projetos não existe na
 * listagem hoje). */
function WorkspaceCard({ workspace, onOpen }: WorkspaceCardProps) {
  const RoleIcon = ROLE_ICON[workspace.my_role];
  const accent = pickAccentColor(workspace.id);
  const createdLabel = new Date(workspace.created_at).toLocaleDateString("pt-BR");

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

      <div className="relative flex items-start justify-between gap-2">
        <div
          className={cn(
            "flex size-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br shadow-md transition-transform duration-200 group-hover:scale-105",
            accent.gradientClass,
            accent.shadowClass,
          )}
        >
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

      <div className="relative flex-1">
        <p className="text-base font-semibold">{workspace.name}</p>
        <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
          {workspace.description ?? "Sem descrição."}
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

  const total = workspaces.length;
  const ownerCount = workspaces.filter((workspace) => workspace.my_role === "OWNER").length;
  const adminCount = workspaces.filter((workspace) => workspace.my_role === "ADMIN").length;
  const memberCount = workspaces.filter((workspace) => workspace.my_role === "MEMBER").length;

  return (
    <div className="flex flex-col gap-5">
      <WorkspacesHero
        total={total}
        ownerCount={ownerCount}
        adminCount={adminCount}
        memberCount={memberCount}
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

      {!isLoading && !error && workspaces.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed py-16 text-center">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-blue-500/10">
            <Building2 className="size-7 text-blue-500/60" strokeWidth={1.5} />
          </div>
          <p className="max-w-xs text-sm text-muted-foreground">
            Você ainda não participa de nenhum workspace. Crie o primeiro clicando em
            &quot;Novo workspace&quot;.
          </p>
        </div>
      )}

      {!isLoading && !error && workspaces.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {workspaces.map((workspace) => (
            <WorkspaceCard
              key={workspace.id}
              workspace={workspace}
              onOpen={() => navigate(`/workspaces/${workspace.id}`)}
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
