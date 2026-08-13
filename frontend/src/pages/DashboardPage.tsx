import {
  AlertCircle,
  AlertTriangle,
  CalendarClock,
  Circle,
  CircleDot,
  CheckCircle2,
  ClipboardList,
  FolderKanban,
  LayoutDashboard,
  PlusIcon,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/contexts/AuthContext";
import { useDashboard } from "@/hooks/useDashboard";
import { useProjects } from "@/hooks/useProjects";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import { cn } from "@/lib/utils";
import type { DashboardCounts, DashboardScopeParams } from "@/types/dashboard";
import type { TaskStatus } from "@/types/task";
import { STATUS_LABEL, STATUS_STROKE_CLASS } from "@/utils/taskStyle";

type ScopeMode = "combined" | "personal" | "workspace" | "project";

const SCOPE_TABS: { mode: ScopeMode; label: string; icon: typeof LayoutDashboard }[] = [
  { mode: "combined", label: "Geral", icon: LayoutDashboard },
  { mode: "personal", label: "Pessoal", icon: UserRound },
  { mode: "workspace", label: "Workspace", icon: LayoutDashboard },
  { mode: "project", label: "Projeto", icon: FolderKanban },
];

interface GradientTileProps {
  icon: typeof AlertTriangle;
  value: number;
  label: string;
  gradientClass: string;
}

/** Card de KPI em gradiente vivo — identidade forte de "dashboard de
 * verdade", inspirada em referências de admin dashboard, mas com a
 * paleta e os dados reais do TaskFlow (sem inventar métrica nenhuma). */
function GradientTile({ icon: Icon, value, label, gradientClass }: GradientTileProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl p-4 text-white shadow-lg",
        gradientClass,
      )}
    >
      <div className="pointer-events-none absolute -top-6 -right-6 size-20 rounded-full bg-white/10 blur-2xl" />
      <div className="relative flex size-9 items-center justify-center rounded-full bg-white/20">
        <Icon className="size-4.5" />
      </div>
      <p className="relative mt-3 text-2xl font-bold">{value}</p>
      <p className="relative text-xs font-medium text-white/85">{label}</p>
    </div>
  );
}

const DISTRIBUTION_KEYS: TaskStatus[] = ["PENDING", "IN_PROGRESS", "DONE"];
const DISTRIBUTION_COUNT_KEY: Record<TaskStatus, keyof DashboardCounts> = {
  PENDING: "pending",
  IN_PROGRESS: "in_progress",
  DONE: "done",
};
const DISTRIBUTION_ICON: Record<TaskStatus, typeof Circle> = {
  PENDING: Circle,
  IN_PROGRESS: CircleDot,
  DONE: CheckCircle2,
};

/** Donut de distribuição por status — três arcos (pendente/em andamento/
 * concluída) com um pequeno vão entre eles, mesma paleta do board kanban.
 * Construído à mão em SVG (não há biblioteca de gráficos no projeto). */
function StatusDonut({ counts, total }: { counts: DashboardCounts; total: number }) {
  const size = 168;
  const strokeWidth = 20;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const gap = 6;

  const segments = DISTRIBUTION_KEYS.map((status) => ({
    status,
    value: counts[DISTRIBUTION_COUNT_KEY[status]],
  })).filter((segment) => segment.value > 0);

  let cumulative = 0;
  const arcs = segments.map((segment) => {
    const rawLength = (segment.value / total) * circumference;
    const length = Math.max(rawLength - gap, 0);
    const offset = cumulative;
    cumulative += rawLength;
    return { ...segment, length, offset };
  });

  const donePercent = total > 0 ? Math.round((counts.done / total) * 100) : 0;

  return (
    <div className="relative flex size-[168px] shrink-0 items-center justify-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={strokeWidth} className="stroke-muted" />
        {arcs.map((arc) => (
          <circle
            key={arc.status}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={`${arc.length} ${circumference - arc.length}`}
            strokeDashoffset={-arc.offset}
            className={cn(STATUS_STROKE_CLASS[arc.status], "transition-[stroke-dasharray] duration-700 ease-out")}
          />
        ))}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-semibold tracking-tight text-foreground">{donePercent}%</span>
        <span className="text-xs text-muted-foreground">concluído</span>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { workspaces } = useWorkspaces();

  const [scopeMode, setScopeMode] = useState<ScopeMode>("combined");
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const { projects } = useProjects(selectedWorkspaceId);

  // Assim que os workspaces carregam, pré-seleciona o primeiro — sem isso,
  // o alternador de Workspace/Projeto ficaria sem nada pra mostrar.
  useEffect(() => {
    if (!selectedWorkspaceId && workspaces.length > 0) {
      setSelectedWorkspaceId(workspaces[0]!.id);
    }
  }, [selectedWorkspaceId, workspaces]);

  useEffect(() => {
    setSelectedProjectId("");
  }, [selectedWorkspaceId]);

  const scopeParams: DashboardScopeParams =
    scopeMode === "personal"
      ? { personal_only: true }
      : scopeMode === "workspace" && selectedWorkspaceId
        ? { workspace_id: selectedWorkspaceId }
        : scopeMode === "project" && selectedProjectId
          ? { project_id: selectedProjectId }
          : {};

  const { counts, isLoading, error } = useDashboard(scopeParams);
  const awaitingSelection =
    (scopeMode === "workspace" && !selectedWorkspaceId) ||
    (scopeMode === "project" && !selectedProjectId);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";
  const firstName = user?.name.trim().split(/\s+/)[0] ?? "";

  const total = counts ? counts.pending + counts.in_progress + counts.done : 0;
  const hasAttention = (counts?.overdue ?? 0) > 0 || (counts?.due_today ?? 0) > 0;

  const newTaskHref =
    scopeMode === "workspace" && selectedWorkspaceId
      ? `/tasks/new?workspace_id=${selectedWorkspaceId}`
      : scopeMode === "project" && selectedProjectId
        ? `/tasks/new?workspace_id=${selectedWorkspaceId}&project_id=${selectedProjectId}`
        : "/tasks";

  const emptyMessage =
    scopeMode === "personal"
      ? "Nenhuma tarefa pessoal ainda."
      : scopeMode === "workspace"
        ? "Nenhuma tarefa neste workspace ainda."
        : scopeMode === "project"
          ? "Nenhuma tarefa neste projeto ainda."
          : "Nenhuma tarefa ainda.";

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={LayoutDashboard}
        title={firstName ? `${greeting}, ${firstName}` : "Dashboard"}
        description="Resumo das suas tarefas pessoais e dos workspaces dos quais você participa."
      />

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1 rounded-xl border bg-muted/40 p-1">
          {SCOPE_TABS.map(({ mode, label, icon: Icon }) => (
            <button
              key={mode}
              type="button"
              onClick={() => setScopeMode(mode)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                scopeMode === mode
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="size-3.5" />
              {label}
            </button>
          ))}
        </div>

        {scopeMode === "workspace" && (
          <Select value={selectedWorkspaceId} onValueChange={setSelectedWorkspaceId}>
            <SelectTrigger className="h-8 rounded-lg">
              <SelectValue placeholder="Escolha um workspace" />
            </SelectTrigger>
            <SelectContent>
              {workspaces.map((workspace) => (
                <SelectItem key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {scopeMode === "project" && (
          <>
            <Select value={selectedWorkspaceId} onValueChange={setSelectedWorkspaceId}>
              <SelectTrigger className="h-8 rounded-lg">
                <SelectValue placeholder="Workspace" />
              </SelectTrigger>
              <SelectContent>
                {workspaces.map((workspace) => (
                  <SelectItem key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={selectedProjectId} onValueChange={setSelectedProjectId}>
              <SelectTrigger className="h-8 rounded-lg">
                <SelectValue placeholder="Escolha um projeto" />
              </SelectTrigger>
              <SelectContent>
                {projects.map((project) => (
                  <SelectItem key={project.id} value={project.id}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </>
        )}
      </div>

      {awaitingSelection && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed py-16 text-center">
          <FolderKanban className="size-8 text-muted-foreground/30" strokeWidth={1.5} />
          <p className="text-sm text-muted-foreground">
            {scopeMode === "project" && !selectedWorkspaceId
              ? "Escolha um workspace e um projeto para ver o resumo."
              : "Escolha um projeto para ver o resumo."}
          </p>
        </div>
      )}

      {!awaitingSelection && isLoading && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-[104px] w-full rounded-2xl" />
            ))}
          </div>
          <Skeleton className="h-[220px] w-full rounded-2xl" />
        </div>
      )}

      {!awaitingSelection && !isLoading && error && (
        <div className="flex items-center gap-2 rounded-xl border border-destructive/20 bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive">
          <AlertCircle className="size-4 shrink-0" />
          {error}
        </div>
      )}

      {!awaitingSelection && !isLoading && !error && counts && total === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed py-16 text-center">
          <ClipboardList className="size-8 text-muted-foreground/30" strokeWidth={1.5} />
          <div>
            <p className="text-sm font-medium">{emptyMessage}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Crie uma tarefa para começar a acompanhar o progresso.
            </p>
          </div>
          <Button
            onClick={() => navigate(newTaskHref)}
            className="mt-1 h-9 gap-1.5 rounded-lg bg-blue-600 px-4 text-sm text-white shadow-sm shadow-blue-600/20 hover:bg-blue-500"
          >
            <PlusIcon className="size-4" />
            Nova tarefa
          </Button>
        </div>
      )}

      {!awaitingSelection && !isLoading && !error && counts && total > 0 && (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <GradientTile
              icon={Circle}
              value={counts.pending}
              label="Pendentes"
              gradientClass="bg-gradient-to-br from-slate-400 to-slate-600"
            />
            <GradientTile
              icon={CircleDot}
              value={counts.in_progress}
              label="Em andamento"
              gradientClass="bg-gradient-to-br from-blue-400 to-blue-600"
            />
            <GradientTile
              icon={CheckCircle2}
              value={counts.done}
              label="Concluídas"
              gradientClass="bg-gradient-to-br from-emerald-400 to-emerald-600"
            />
            <GradientTile
              icon={AlertTriangle}
              value={counts.overdue}
              label="Atrasadas"
              gradientClass={
                counts.overdue > 0
                  ? "bg-gradient-to-br from-red-400 to-red-600"
                  : "bg-gradient-to-br from-slate-300 to-slate-500"
              }
            />
            <GradientTile
              icon={CalendarClock}
              value={counts.due_today}
              label="Vencendo hoje"
              gradientClass={
                counts.due_today > 0
                  ? "bg-gradient-to-br from-amber-400 to-amber-600"
                  : "bg-gradient-to-br from-slate-300 to-slate-500"
              }
            />
          </div>

          <div className="flex flex-col gap-6 rounded-2xl border bg-card p-6 sm:flex-row sm:items-center">
            <StatusDonut counts={counts} total={total} />

            <div className="flex flex-1 flex-col gap-4">
              <div className="flex flex-col gap-2">
                {DISTRIBUTION_KEYS.map((status) => {
                  const Icon = DISTRIBUTION_ICON[status];
                  const value = counts[DISTRIBUTION_COUNT_KEY[status]];
                  const percent = total > 0 ? Math.round((value / total) * 100) : 0;
                  return (
                    <div key={status} className="flex items-center gap-2 text-sm">
                      <Icon
                        className={cn(
                          "size-3.5 shrink-0",
                          status === "PENDING"
                            ? "text-slate-500"
                            : status === "IN_PROGRESS"
                              ? "text-blue-500"
                              : "text-emerald-500",
                        )}
                      />
                      <span className="text-muted-foreground">{STATUS_LABEL[status]}</span>
                      <span className="ml-auto font-semibold text-foreground">{value}</span>
                      <span className="w-10 text-right text-xs text-muted-foreground">{percent}%</span>
                    </div>
                  );
                })}
              </div>

              <div className="border-t pt-4">
                {hasAttention ? (
                  <div className="flex flex-col gap-2 sm:flex-row">
                    {counts.overdue > 0 && (
                      <span className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs font-medium text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-400">
                        <AlertTriangle className="size-3.5" />
                        {counts.overdue} {counts.overdue === 1 ? "tarefa atrasada" : "tarefas atrasadas"}
                      </span>
                    )}
                    {counts.due_today > 0 && (
                      <span className="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs font-medium text-amber-700 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-400">
                        <CalendarClock className="size-3.5" />
                        {counts.due_today} vencendo hoje
                      </span>
                    )}
                  </div>
                ) : (
                  <span className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs font-medium text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/30 dark:text-emerald-400">
                    <ShieldCheck className="size-3.5" />
                    Tudo em dia
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
