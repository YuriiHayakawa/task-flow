import {
  AlertCircle,
  AlertTriangle,
  Building2,
  CalendarClock,
  ClipboardList,
  FolderKanban,
  LayoutDashboard,
  PlusIcon,
  ShieldCheck,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

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
import type { Project } from "@/types/project";
import type { TaskStatus } from "@/types/task";
import type { Workspace } from "@/types/workspace";
import {
  STATUS_ACCENT_CLASS,
  STATUS_ICON,
  STATUS_ICON_COLOR_CLASS,
  STATUS_LABEL,
  STATUS_STROKE_CLASS,
} from "@/utils/taskStyle";

type ScopeMode = "combined" | "personal" | "workspace" | "project";

const SCOPE_TABS: { mode: ScopeMode; label: string; icon: LucideIcon }[] = [
  { mode: "combined", label: "Geral", icon: LayoutDashboard },
  { mode: "personal", label: "Pessoal", icon: UserRound },
  { mode: "workspace", label: "Workspace", icon: Building2 },
  { mode: "project", label: "Projeto", icon: FolderKanban },
];

type StatTone = "slate" | "blue" | "emerald" | "red" | "amber";

/** Paleta por "tom" dos cards de KPI — mesmas cores de status já usadas em
 * todo o app (`taskStyle.ts`), estendida com vermelho/âmbar para os dois
 * indicadores de atenção (atrasadas/vencendo hoje), que não são status. */
const TONE_STYLES: Record<StatTone, { bar: string; badge: string; glow: string; wash: string; dot: string }> = {
  slate: {
    bar: "bg-gradient-to-r from-slate-400 to-slate-500",
    badge: "bg-gradient-to-br from-slate-400 to-slate-600",
    glow: "bg-slate-400/40",
    wash: "",
    dot: "bg-slate-400",
  },
  blue: {
    bar: "bg-gradient-to-r from-blue-400 to-blue-600",
    badge: "bg-gradient-to-br from-blue-400 to-blue-600",
    glow: "bg-blue-500/40",
    wash: "",
    dot: "bg-blue-400",
  },
  emerald: {
    bar: "bg-gradient-to-r from-emerald-400 to-emerald-600",
    badge: "bg-gradient-to-br from-emerald-400 to-emerald-600",
    glow: "bg-emerald-500/40",
    wash: "",
    dot: "bg-emerald-400",
  },
  red: {
    bar: "bg-gradient-to-r from-red-400 to-red-600",
    badge: "bg-gradient-to-br from-red-400 to-red-600",
    glow: "bg-red-500/40",
    wash: "bg-red-50/50 dark:bg-red-950/10",
    dot: "bg-red-400",
  },
  amber: {
    bar: "bg-gradient-to-r from-amber-400 to-amber-600",
    badge: "bg-gradient-to-br from-amber-400 to-amber-600",
    glow: "bg-amber-500/40",
    wash: "bg-amber-50/50 dark:bg-amber-950/10",
    dot: "bg-amber-400",
  },
};

interface StatCardProps {
  icon: LucideIcon;
  value: number;
  label: string;
  tone: StatTone;
  /** Cards de atenção (Atrasadas/Vencendo hoje): tom neutro e sem pulso
   * quando o valor é zero — nada de errado para chamar atenção. */
  alert?: boolean;
}

function StatCard({ icon: Icon, value, label, tone, alert = false }: StatCardProps) {
  const isQuiet = alert && value === 0;
  const style = TONE_STYLES[isQuiet ? "slate" : tone];

  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-2xl border bg-card p-4 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
        !isQuiet && style.wash,
      )}
    >
      <div className={cn("absolute inset-x-0 top-0 h-1", style.bar)} />
      {alert && !isQuiet && (
        <span className="absolute top-3 right-3 flex size-2">
          <span className={cn("absolute inline-flex size-full animate-ping rounded-full opacity-75", style.dot)} />
          <span className={cn("relative inline-flex size-2 rounded-full", style.dot)} />
        </span>
      )}
      <div className="relative flex size-9 items-center justify-center">
        <div className={cn("absolute inset-0 rounded-full opacity-70 blur-md", style.glow)} />
        <div
          className={cn(
            "relative flex size-9 items-center justify-center rounded-full text-white shadow-sm",
            style.badge,
          )}
        >
          <Icon className="size-4.5" />
        </div>
      </div>
      <p className="relative mt-3 text-2xl font-bold tabular-nums text-foreground">{value}</p>
      <p className="relative text-xs font-medium text-muted-foreground">{label}</p>
    </div>
  );
}

const DISTRIBUTION_KEYS: TaskStatus[] = ["PENDING", "IN_PROGRESS", "DONE"];
const DISTRIBUTION_COUNT_KEY: Record<TaskStatus, keyof DashboardCounts> = {
  PENDING: "pending",
  IN_PROGRESS: "in_progress",
  DONE: "done",
};

/** Donut de distribuição por status — três arcos (pendente/em andamento/
 * concluída) com um pequeno vão entre eles, mesma paleta do board kanban.
 * Construído à mão em SVG (não há biblioteca de gráficos no projeto). */
function StatusDonut({ counts, total }: { counts: DashboardCounts; total: number }) {
  const size = 176;
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
    <div className="relative flex size-[176px] shrink-0 items-center justify-center">
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

interface HeroSummary {
  total: number;
  done: number;
  donePercent: number;
  overdue: number;
  dueToday: number;
}

interface DashboardHeroProps {
  greeting: string;
  scopeMode: ScopeMode;
  onScopeModeChange: (mode: ScopeMode) => void;
  workspaces: Workspace[];
  selectedWorkspaceId: string;
  onWorkspaceChange: (id: string) => void;
  projects: Project[];
  selectedProjectId: string;
  onProjectChange: (id: string) => void;
  onCreateTask: () => void;
  /** `null` enquanto não há um resumo do escopo atual pra mostrar (aguardando
   * seleção, carregando ou erro) — a trilha de progresso e o selo de atenção
   * só aparecem com dados reais em mãos. */
  summary: HeroSummary | null;
}

/** Cabeçalho próprio do Dashboard — mesma identidade escura dos demais
 * heróis do app (`TasksHero`, `NotificationsHero`): fundo azul-marinho,
 * malha de pontos, blobs à deriva. O anel pontilhado girando ao redor do
 * ícone (`orbit-ring`) é o mesmo selo usado hoje só na tela pública de
 * login (`BrandPanel`) — reaproveitado aqui de propósito: o Dashboard é a
 * "porta de entrada" pós-login, o equivalente autenticado daquela tela.
 * Concentra também o alternador de escopo (antes um controle solto e claro
 * flutuando sobre o fundo neutro da página) e, quando há dados, uma trilha
 * de progresso + o selo de atenção (atrasadas/vencendo hoje/tudo em dia) —
 * o resumo mais urgente do dashboard já no primeiro olhar. */
function DashboardHero({
  greeting,
  scopeMode,
  onScopeModeChange,
  workspaces,
  selectedWorkspaceId,
  onWorkspaceChange,
  projects,
  selectedProjectId,
  onProjectChange,
  onCreateTask,
  summary,
}: DashboardHeroProps) {
  const hasAttention = summary !== null && (summary.overdue > 0 || summary.dueToday > 0);

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0b1220] via-[#0a0f1e] to-[#05070f] p-5 shadow-xl shadow-black/20 sm:p-6">
      <div className="blob-drift-a pointer-events-none absolute -top-20 -left-14 size-56 rounded-full bg-blue-600/25 blur-[80px]" />
      <div className="blob-drift-b pointer-events-none absolute -right-16 -bottom-20 size-64 rounded-full bg-indigo-500/20 blur-[90px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] bg-[size:32px_32px]" />
      <LayoutDashboard
        className="pointer-events-none absolute -right-8 -bottom-10 size-44 -rotate-12 text-blue-500/[0.06]"
        strokeWidth={1}
      />

      <div className="relative flex flex-col gap-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="relative flex size-12 shrink-0 items-center justify-center">
              <div className="absolute inset-0 rounded-2xl bg-blue-500/30 blur-md" />
              <div className="orbit-ring absolute -inset-2 rounded-full border border-dashed border-blue-400/30" />
              <div className="relative flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-400 to-blue-700 shadow-lg shadow-blue-900/40">
                <LayoutDashboard className="size-6 text-white" strokeWidth={2.25} />
              </div>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">{greeting}</h1>
              <p className="text-xs text-slate-400 sm:text-sm">
                Resumo das suas tarefas pessoais e dos workspaces dos quais você participa.
              </p>
            </div>
          </div>
          <Button
            onClick={onCreateTask}
            className="h-10 w-fit gap-1.5 rounded-xl bg-white px-4 text-sm font-semibold text-[#05070f] shadow-lg shadow-black/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-xl hover:shadow-blue-500/10"
          >
            <PlusIcon className="size-4" />
            Nova tarefa
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-white/10 pt-4">
          <div className="flex flex-wrap gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
            {SCOPE_TABS.map(({ mode, label, icon: Icon }) => (
              <button
                key={mode}
                type="button"
                onClick={() => onScopeModeChange(mode)}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                  scopeMode === mode ? "bg-white/15 text-white shadow-sm" : "text-slate-400 hover:text-slate-200",
                )}
              >
                <Icon className="size-3.5" />
                {label}
              </button>
            ))}
          </div>

          {scopeMode === "workspace" && (
            <Select value={selectedWorkspaceId} onValueChange={onWorkspaceChange}>
              <SelectTrigger className="h-8 rounded-lg border-white/15 bg-white/5 text-slate-100 hover:bg-white/10">
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
              <Select value={selectedWorkspaceId} onValueChange={onWorkspaceChange}>
                <SelectTrigger className="h-8 rounded-lg border-white/15 bg-white/5 text-slate-100 hover:bg-white/10">
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
              <Select value={selectedProjectId} onValueChange={onProjectChange}>
                <SelectTrigger className="h-8 rounded-lg border-white/15 bg-white/5 text-slate-100 hover:bg-white/10">
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

        {summary && summary.total > 0 && (
          <div className="flex flex-col gap-3 border-t border-white/10 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-1 items-center gap-3">
              <div className="h-1.5 w-full max-w-56 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-blue-400 to-emerald-400 transition-[width] duration-700 ease-out"
                  style={{ width: `${summary.donePercent}%` }}
                />
              </div>
              <span className="shrink-0 text-xs font-medium text-slate-400">
                <span className="text-sm font-bold text-white">{summary.donePercent}%</span> concluído ·{" "}
                {summary.done} de {summary.total}
              </span>
            </div>

            <div className="flex shrink-0 flex-wrap items-center gap-2">
              {hasAttention ? (
                <>
                  {summary.overdue > 0 && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-red-400/15 px-3 py-1.5 text-xs font-semibold text-red-300">
                      <AlertTriangle className="size-3.5" />
                      {summary.overdue} {summary.overdue === 1 ? "tarefa atrasada" : "tarefas atrasadas"}
                    </span>
                  )}
                  {summary.dueToday > 0 && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-400/15 px-3 py-1.5 text-xs font-semibold text-amber-300">
                      <CalendarClock className="size-3.5" />
                      {summary.dueToday} vencendo hoje
                    </span>
                  )}
                </>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-400/15 px-3 py-1.5 text-xs font-semibold text-emerald-300">
                  <ShieldCheck className="size-3.5" />
                  Tudo em dia
                </span>
              )}
            </div>
          </div>
        )}
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
  const greetingWord = hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";
  const firstName = user?.name.trim().split(/\s+/)[0] ?? "";
  const greeting = firstName ? `${greetingWord}, ${firstName}` : "Dashboard";

  const total = counts ? counts.pending + counts.in_progress + counts.done : 0;
  const donePercent = counts && total > 0 ? Math.round((counts.done / total) * 100) : 0;
  const showSummary = !awaitingSelection && !isLoading && !error && counts !== null;

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
      <DashboardHero
        greeting={greeting}
        scopeMode={scopeMode}
        onScopeModeChange={setScopeMode}
        workspaces={workspaces}
        selectedWorkspaceId={selectedWorkspaceId}
        onWorkspaceChange={setSelectedWorkspaceId}
        projects={projects}
        selectedProjectId={selectedProjectId}
        onProjectChange={setSelectedProjectId}
        onCreateTask={() => navigate(newTaskHref)}
        summary={
          showSummary && counts
            ? { total, done: counts.done, donePercent, overdue: counts.overdue, dueToday: counts.due_today }
            : null
        }
      />

      {awaitingSelection && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-3xl border border-dashed py-16 text-center">
          <div className="flex size-14 items-center justify-center rounded-full bg-muted">
            <FolderKanban className="size-6 text-muted-foreground/60" strokeWidth={1.5} />
          </div>
          <p className="text-sm text-muted-foreground">
            {scopeMode === "workspace"
              ? "Escolha um workspace para ver o resumo."
              : scopeMode === "project" && !selectedWorkspaceId
                ? "Escolha um workspace e um projeto para ver o resumo."
                : "Escolha um projeto para ver o resumo."}
          </p>
        </div>
      )}

      {!awaitingSelection && isLoading && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-[112px] w-full rounded-2xl" />
            ))}
          </div>
          <Skeleton className="h-[240px] w-full rounded-3xl" />
        </div>
      )}

      {!awaitingSelection && !isLoading && error && (
        <div className="flex items-center gap-2 rounded-xl border border-destructive/20 bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive">
          <AlertCircle className="size-4 shrink-0" />
          {error}
        </div>
      )}

      {!awaitingSelection && !isLoading && !error && counts && total === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-3xl border border-dashed py-16 text-center">
          <div className="flex size-14 items-center justify-center rounded-full bg-muted">
            <ClipboardList className="size-6 text-muted-foreground/60" strokeWidth={1.5} />
          </div>
          <div>
            <p className="text-sm font-medium">{emptyMessage}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Use o botão &quot;Nova tarefa&quot; acima para começar a acompanhar o progresso.
            </p>
          </div>
        </div>
      )}

      {!awaitingSelection && !isLoading && !error && counts && total > 0 && (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <StatCard icon={STATUS_ICON.PENDING} value={counts.pending} label="Pendentes" tone="slate" />
            <StatCard icon={STATUS_ICON.IN_PROGRESS} value={counts.in_progress} label="Em andamento" tone="blue" />
            <StatCard icon={STATUS_ICON.DONE} value={counts.done} label="Concluídas" tone="emerald" />
            <StatCard icon={AlertTriangle} value={counts.overdue} label="Atrasadas" tone="red" alert />
            <StatCard icon={CalendarClock} value={counts.due_today} label="Vencendo hoje" tone="amber" alert />
          </div>

          <div className="flex flex-col gap-6 rounded-3xl border bg-card p-6 shadow-sm sm:flex-row sm:items-center">
            <StatusDonut counts={counts} total={total} />

            <div className="flex flex-1 flex-col gap-4">
              <div>
                <h2 className="text-sm font-semibold text-foreground">Distribuição por status</h2>
                <p className="text-xs text-muted-foreground">Como suas tarefas visíveis estão distribuídas agora.</p>
              </div>

              <div className="flex flex-col gap-3">
                {DISTRIBUTION_KEYS.map((status) => {
                  const Icon = STATUS_ICON[status];
                  const value = counts[DISTRIBUTION_COUNT_KEY[status]];
                  const percent = total > 0 ? Math.round((value / total) * 100) : 0;
                  return (
                    <div key={status} className="flex items-center gap-2.5 text-sm">
                      <Icon className={cn("size-3.5 shrink-0", STATUS_ICON_COLOR_CLASS[status])} />
                      <span className="w-24 shrink-0 text-muted-foreground">{STATUS_LABEL[status]}</span>
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                        <div
                          className={cn(
                            "h-full rounded-full transition-[width] duration-700 ease-out",
                            STATUS_ACCENT_CLASS[status],
                          )}
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                      <span className="w-7 shrink-0 text-right font-semibold text-foreground">{value}</span>
                      <span className="w-10 shrink-0 text-right text-xs text-muted-foreground">{percent}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
