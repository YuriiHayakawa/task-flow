import {
  AlertCircle,
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Circle,
  CircleDot,
  LayoutDashboard,
  type LucideIcon,
} from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useDashboard } from "@/hooks/useDashboard";
import { cn } from "@/lib/utils";
import type { DashboardCounts } from "@/types/dashboard";

type Tone = "default" | "warning" | "danger";

const TONE_ICON_WRAPPER: Record<Tone, string> = {
  default: "bg-muted text-muted-foreground",
  warning: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  danger: "bg-destructive/10 text-destructive",
};

interface StatDefinition {
  key: keyof DashboardCounts;
  label: string;
  icon: LucideIcon;
  tone: Tone;
}

const STATS: StatDefinition[] = [
  { key: "pending", label: "Pendentes", icon: Circle, tone: "default" },
  { key: "in_progress", label: "Em andamento", icon: CircleDot, tone: "default" },
  { key: "done", label: "Concluídas", icon: CheckCircle2, tone: "default" },
  { key: "overdue", label: "Atrasadas", icon: AlertTriangle, tone: "danger" },
  { key: "due_today", label: "Vencendo hoje", icon: CalendarClock, tone: "warning" },
];

function StatCard({ label, value, icon: Icon, tone }: { label: string; value: number; icon: LucideIcon; tone: Tone }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3">
        <div className={cn("flex size-10 shrink-0 items-center justify-center rounded-lg", TONE_ICON_WRAPPER[tone])}>
          <Icon className="size-5" />
        </div>
        <div>
          <p className="text-2xl font-bold tabular-nums">{value}</p>
          <p className="text-sm text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const { counts, isLoading, error } = useDashboard();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon={LayoutDashboard}
        title="Dashboard"
        description="Resumo das suas tarefas pessoais e dos workspaces dos quais você participa."
      />

      {isLoading && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {STATS.map((stat) => (
            <Skeleton key={stat.key} className="h-[74px] w-full" />
          ))}
        </div>
      )}

      {!isLoading && error && (
        <div className="flex items-center gap-2 rounded-xl border border-destructive/20 bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive">
          <AlertCircle className="size-4 shrink-0" />
          {error}
        </div>
      )}

      {!isLoading && !error && counts && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {STATS.map((stat) => (
            <StatCard
              key={stat.key}
              label={stat.label}
              value={counts[stat.key]}
              icon={stat.icon}
              tone={stat.tone}
            />
          ))}
        </div>
      )}
    </div>
  );
}
