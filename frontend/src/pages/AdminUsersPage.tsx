import {
  Ban,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  ShieldCheck,
  ShieldUser,
} from "lucide-react";
import { useState } from "react";

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
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/contexts/AuthContext";
import { useAdminUsers } from "@/hooks/useAdminUsers";
import { cn } from "@/lib/utils";
import type { User } from "@/types/user";
import { getApiErrorMessage } from "@/utils/apiErrorMessage";
import { getInitials } from "@/utils/initials";

const PAGE_SIZE = 20;

type StatusFilter = "ALL" | "ACTIVE" | "INACTIVE";

const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "ALL", label: "Todas" },
  { value: "ACTIVE", label: "Ativas" },
  { value: "INACTIVE", label: "Desativadas" },
];

interface DeactivateUserDialogProps {
  user: User;
  onConfirm: () => Promise<void>;
}

/** Mesmo padrão auto-contido dos diálogos de exclusão do resto do app
 * (`RemoveMemberDialog`, `DeleteWorkspaceDialog`) — desativar bloqueia login
 * imediatamente (FR-004), então é a única das duas ações que pede
 * confirmação; reativar é uma ação simples e sem risco. */
function DeactivateUserDialog({ user, onConfirm }: DeactivateUserDialogProps) {
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleConfirm() {
    setError(null);
    setIsSubmitting(true);
    try {
      await onConfirm();
    } catch (err) {
      setError(getApiErrorMessage(err, "Não foi possível desativar esta conta."));
      setIsSubmitting(false);
    }
  }

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          aria-label={`Desativar ${user.name}`}
          className="h-8 gap-1.5 rounded-lg text-xs text-destructive hover:bg-destructive/10"
        >
          <Ban className="size-3.5" />
          Desativar
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Desativar a conta de {user.name}?</AlertDialogTitle>
          <AlertDialogDescription>
            A pessoa deixa de conseguir fazer login imediatamente, até que a conta seja reativada.
            Nenhum dado é apagado.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isSubmitting}>Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} disabled={isSubmitting} variant="destructive">
            {isSubmitting ? "Desativando..." : "Desativar"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

interface AdminHeroProps {
  total: number;
  isLoading: boolean;
}

/** Mesma identidade escura dos demais heróis — ícone `ShieldCheck`, o mesmo
 * usado no item "Administração" da sidebar, pra reforçar visualmente que é
 * a mesma seção. Sem CTA de criação (contas nascem via cadastro, não aqui). */
function AdminHero({ total, isLoading }: AdminHeroProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0b1220] via-[#0a0f1e] to-[#05070f] p-5 shadow-xl shadow-black/20 sm:p-6">
      <div className="blob-drift-a pointer-events-none absolute -top-20 -left-14 size-56 rounded-full bg-blue-600/25 blur-[80px]" />
      <div className="blob-drift-b pointer-events-none absolute -right-16 -bottom-20 size-64 rounded-full bg-violet-500/20 blur-[90px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] bg-[size:32px_32px]" />
      <ShieldCheck
        className="pointer-events-none absolute -right-8 -bottom-10 size-44 -rotate-12 text-blue-500/[0.06]"
        strokeWidth={1}
      />

      <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="relative flex size-10 shrink-0 items-center justify-center">
            <div className="absolute inset-0 rounded-xl bg-blue-500/30 blur-md" />
            <div className="relative flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-400 to-blue-700 shadow-lg shadow-blue-900/40">
              <ShieldCheck className="size-5 text-white" strokeWidth={2.25} />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
              Usuários
            </h1>
            <p className="text-xs text-slate-400 sm:text-sm">Ative ou desative contas da plataforma</p>
          </div>
        </div>
        {!isLoading && (
          <span className="inline-flex w-fit shrink-0 items-center gap-1.5 rounded-full bg-blue-400/15 px-3 py-1.5 text-xs font-semibold text-blue-300">
            {total} {total === 1 ? "conta" : "contas"}
          </span>
        )}
      </div>
    </div>
  );
}

/** US13 — administração de usuários da plataforma (System Admin), FR-043 a
 * FR-046. A rota já é protegida por `AdminRoute` (frontend, UX) e pelo
 * dependency `require_system_admin` do backend (a barreira real de
 * segurança — Constitution IV: frontend nunca é a única validação). */
export function AdminUsersPage() {
  const { user: currentUser } = useAuth();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [page, setPage] = useState(1);

  const { users, total, isLoading, error, setUserActive } = useAdminUsers({
    is_active: statusFilter === "ALL" ? undefined : statusFilter === "ACTIVE",
    page,
    page_size: PAGE_SIZE,
  });

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const rangeStart = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const rangeEnd = Math.min(page * PAGE_SIZE, total);

  function handleFilterChange(next: StatusFilter) {
    setStatusFilter(next);
    setPage(1);
  }

  return (
    <div className="flex flex-col gap-5">
      <AdminHero total={total} isLoading={isLoading} />

      <div className="flex w-fit gap-1 rounded-xl border bg-card p-1 shadow-sm">
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter.value}
            type="button"
            onClick={() => handleFilterChange(filter.value)}
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
              statusFilter === filter.value
                ? "bg-blue-600 text-white"
                : "text-muted-foreground hover:bg-muted",
            )}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
        </div>
      )}

      {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

      {!isLoading && !error && users.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed py-16 text-center">
          <p className="text-sm text-muted-foreground">Nenhuma conta encontrada com esse filtro.</p>
        </div>
      )}

      {!isLoading && !error && users.length > 0 && (
        <div className="flex flex-col gap-2">
          {users.map((user) => {
            const isSelf = user.id === currentUser?.id;

            return (
              <div
                key={user.id}
                className={cn(
                  "flex flex-wrap items-center gap-3 rounded-xl border border-l-4 bg-card p-3 shadow-sm",
                  user.is_active ? "border-l-emerald-400" : "border-l-slate-300",
                )}
              >
                <Avatar className="rounded-lg">
                  <AvatarFallback className="rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 text-xs font-semibold text-white">
                    {getInitials(user.name)}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {user.name}
                    {isSelf && <span className="ml-1.5 text-xs text-muted-foreground">(você)</span>}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                </div>

                {user.is_system_admin && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                    <ShieldUser className="size-3" />
                    System Admin
                  </span>
                )}

                <Badge
                  variant="outline"
                  className={cn(
                    "border-transparent",
                    user.is_active
                      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                      : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
                  )}
                >
                  {user.is_active ? "Ativa" : "Desativada"}
                </Badge>

                {/* Sem ação para a própria conta — evita o usuário se
                    trancar fora da plataforma por engano; o backend
                    permitiria (nenhuma regra de negócio impede), mas isso
                    aqui é só uma salvaguarda de UX, não uma regra
                    duplicada (Constitution IV). */}
                {!isSelf && (
                  <div className="ml-auto">
                    {user.is_active ? (
                      <DeactivateUserDialog
                        user={user}
                        onConfirm={() => setUserActive(user.id, false)}
                      />
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        aria-label={`Reativar ${user.name}`}
                        onClick={() => void setUserActive(user.id, true)}
                        className="h-8 gap-1.5 rounded-lg text-xs"
                      >
                        <RotateCcw className="size-3.5" />
                        Reativar
                      </Button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!isLoading && !error && total > PAGE_SIZE && (
        <div className="flex items-center justify-between border-t border-border/70 pt-4 text-xs text-muted-foreground">
          <span>
            Mostrando {rangeStart}–{rangeEnd} de {total}
          </span>
          <div className="flex items-center gap-1.5">
            <Button
              type="button"
              variant="outline"
              size="icon"
              disabled={page <= 1}
              onClick={() => setPage((current) => current - 1)}
              className="h-8 w-8 rounded-lg"
              aria-label="Página anterior"
            >
              <ChevronLeft className="size-4" />
            </Button>
            <span className="px-1 tabular-nums">
              Página {page} de {totalPages}
            </span>
            <Button
              type="button"
              variant="outline"
              size="icon"
              disabled={page >= totalPages}
              onClick={() => setPage((current) => current + 1)}
              className="h-8 w-8 rounded-lg"
              aria-label="Próxima página"
            >
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
