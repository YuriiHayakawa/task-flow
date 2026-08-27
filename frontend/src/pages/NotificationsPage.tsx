import {
  AlarmClock,
  Bell,
  Check,
  CheckCheck,
  MessageSquare,
  RefreshCcw,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { UseNotificationsResult } from "@/hooks/useNotifications";
import { cn } from "@/lib/utils";
import type { Notification, NotificationType } from "@/types/notification";

/** Reformulação (a pedido do usuário, depois de duas rodadas de listas
 * descartadas): em vez de uma lista única, um board de 3 colunas — mesma
 * identidade visual do board kanban de "Minhas tarefas" (`PersonalTasksPage`,
 * o elemento mais reconhecível do produto), só que organizando por TIPO de
 * evento em vez de status de tarefa. `contracts/dashboard-and-notifications.md`
 * — DUE_SOON/NEW_COMMENT/TASK_CHANGED são os únicos 3 tipos do MVP. */
const COLUMNS: {
  type: NotificationType;
  label: string;
  icon: LucideIcon;
  iconWrapperClass: string;
  columnTintClass: string;
  accentClass: string;
  countBadgeClass: string;
}[] = [
  {
    type: "DUE_SOON",
    label: "Prazos",
    icon: AlarmClock,
    iconWrapperClass: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
    columnTintClass: "bg-amber-50/50 dark:bg-amber-950/10",
    accentClass: "bg-amber-400",
    countBadgeClass: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  },
  {
    type: "NEW_COMMENT",
    label: "Comentários",
    icon: MessageSquare,
    iconWrapperClass: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
    columnTintClass: "bg-blue-50/50 dark:bg-blue-950/10",
    accentClass: "bg-blue-500",
    countBadgeClass: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  },
  {
    type: "TASK_CHANGED",
    label: "Alterações",
    icon: RefreshCcw,
    iconWrapperClass: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
    columnTintClass: "bg-violet-50/50 dark:bg-violet-950/10",
    accentClass: "bg-violet-500",
    countBadgeClass: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  },
];

/** Rótulo relativo simples ("há 5 min", "ontem"...) sem depender de
 * biblioteca de datas nova (Constitution V) — mesmo espírito de
 * `describeDueDate` em `taskStyle.ts`, só que para "quando aconteceu" em
 * vez de "quando vence". */
function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const diffMinutes = Math.floor((Date.now() - date.getTime()) / 60_000);

  if (diffMinutes < 1) return "agora mesmo";
  if (diffMinutes < 60) return `há ${diffMinutes} min`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `há ${diffHours}h`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return "ontem";
  if (diffDays < 7) return `há ${diffDays} dias`;
  return date.toLocaleDateString("pt-BR");
}

interface NotificationsHeroProps {
  isLoading: boolean;
  unreadCount: number;
  isMarkingAll: boolean;
  onMarkAllRead: () => void;
}

/** Mesma identidade escura dos demais heróis do app — badge do lado direito
 * alterna entre "N não lidas" + CTA (mesmo botão branco de destaque de
 * `TasksHero`) e um estado positivo "Tudo em dia" quando não sobra nada
 * pendente, em vez de simplesmente esconder a área e deixar o cabeçalho
 * "manco" de um lado. */
function NotificationsHero({ isLoading, unreadCount, isMarkingAll, onMarkAllRead }: NotificationsHeroProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0b1220] via-[#0a0f1e] to-[#05070f] p-5 shadow-xl shadow-black/20 sm:p-6">
      <div className="blob-drift-a pointer-events-none absolute -top-20 -left-14 size-56 rounded-full bg-blue-600/25 blur-[80px]" />
      <div className="blob-drift-b pointer-events-none absolute -right-16 -bottom-20 size-64 rounded-full bg-indigo-500/20 blur-[90px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] bg-[size:32px_32px]" />
      <Bell
        className="pointer-events-none absolute -right-8 -bottom-10 size-44 -rotate-12 text-blue-500/[0.06]"
        strokeWidth={1}
      />

      <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="relative flex size-10 shrink-0 items-center justify-center">
            <div className="absolute inset-0 rounded-xl bg-blue-500/30 blur-md" />
            <div className="relative flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-400 to-blue-700 shadow-lg shadow-blue-900/40">
              <Bell className="size-5 text-white" strokeWidth={2.25} />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
              Notificações
            </h1>
            <p className="text-xs text-slate-400 sm:text-sm">
              Prazos, comentários e alterações organizados por tipo — igual à esteira das suas
              tarefas.
            </p>
          </div>
        </div>

        {!isLoading && (
          <div className="flex shrink-0 items-center gap-2.5">
            {unreadCount > 0 ? (
              <>
                <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-blue-400/15 px-3 py-1.5 text-xs font-semibold text-blue-300">
                  {unreadCount} {unreadCount === 1 ? "não lida" : "não lidas"}
                </span>
                <Button
                  onClick={onMarkAllRead}
                  disabled={isMarkingAll}
                  className="h-10 w-fit gap-1.5 rounded-xl bg-white px-4 text-sm font-semibold text-[#05070f] shadow-lg shadow-black/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-xl hover:shadow-blue-500/10"
                >
                  <CheckCheck className="size-4" />
                  {isMarkingAll ? "Marcando..." : "Marcar todas como lidas"}
                </Button>
              </>
            ) : (
              <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-emerald-400/15 px-3 py-1.5 text-xs font-semibold text-emerald-300">
                <Sparkles className="size-3.5" />
                Tudo em dia
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

interface NotificationCardProps {
  notification: Notification;
  index: number;
  onOpen: () => void;
  onMarkRead: () => void;
}

/** Cartão dentro de uma coluna — a cor do TIPO já vem da coluna (cabeçalho/
 * tinta de fundo), então o cartão em si só precisa comunicar lida/não lida
 * (tingimento sutil + ponto azul), sem repetir a cor do tipo por cima da
 * cor da coluna. Clicar marca como lida (se ainda não estiver) e navega até
 * a tarefa; "marcar como lida" individual só aparece no hover. */
function NotificationCard({ notification, index, onOpen, onMarkRead }: NotificationCardProps) {
  const isUnread = !notification.is_read;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen();
        }
      }}
      style={{ animationDelay: `${Math.min(index * 40, 200)}ms` }}
      className={cn(
        "group animate-in fade-in slide-in-from-bottom-1 flex cursor-pointer flex-col gap-1 rounded-xl border bg-card p-3 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
        isUnread && "border-blue-200/70 bg-blue-50/70 dark:border-blue-900/40 dark:bg-blue-950/20",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className={cn("text-xs font-medium", !isUnread && "text-muted-foreground")}>
          {notification.title}
        </p>
        {isUnread && <span className="mt-1 size-1.5 shrink-0 rounded-full bg-blue-500" />}
      </div>
      <p className="line-clamp-2 text-[11px] text-muted-foreground">{notification.message}</p>
      <div className="mt-1 flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground/70">
          {formatRelativeTime(notification.created_at)}
        </span>
        {isUnread && (
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onMarkRead();
            }}
            aria-label="Marcar como lida"
            title="Marcar como lida"
            className="rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-muted hover:text-foreground group-hover:opacity-100"
          >
            <Check className="size-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}

interface NotificationColumnProps {
  type: NotificationType;
  label: string;
  icon: LucideIcon;
  iconWrapperClass: string;
  columnTintClass: string;
  accentClass: string;
  countBadgeClass: string;
  notifications: Notification[];
  onOpenNotification: (notification: Notification) => void;
  onMarkRead: (notificationId: string) => void;
}

/** Mesma estrutura visual de `TaskColumn` (`PersonalTasksPage`) — friso de
 * cor no topo, tinta de fundo sutil, ícone+rótulo+contagem no cabeçalho —
 * reaplicada aqui a um tipo de evento em vez de um status de tarefa. */
function NotificationColumn({
  label,
  icon: Icon,
  iconWrapperClass,
  columnTintClass,
  accentClass,
  countBadgeClass,
  notifications,
  onOpenNotification,
  onMarkRead,
}: NotificationColumnProps) {
  return (
    <div
      aria-label={`Coluna ${label}`}
      className={cn(
        "relative flex min-h-64 flex-col gap-3 overflow-hidden rounded-2xl border border-border p-3 pt-4",
        columnTintClass,
      )}
    >
      <div className={cn("absolute inset-x-0 top-0 h-1", accentClass)} />

      <div className="flex items-center gap-2">
        <div className={cn("flex size-7 shrink-0 items-center justify-center rounded-lg", iconWrapperClass)}>
          <Icon className="size-4" />
        </div>
        <span className="text-sm font-semibold">{label}</span>
        <span
          className={cn(
            "ml-auto flex size-5 items-center justify-center rounded-full text-[11px] font-semibold tabular-nums",
            countBadgeClass,
          )}
        >
          {notifications.length}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-2">
        {notifications.length === 0 && (
          <div className="mt-6 flex flex-col items-center gap-1.5 text-center">
            <Icon className="size-6 text-muted-foreground/25" strokeWidth={1.5} />
            <p className="text-xs text-muted-foreground">Nada por aqui</p>
          </div>
        )}
        {notifications.map((notification, index) => (
          <NotificationCard
            key={notification.id}
            notification={notification}
            index={index}
            onOpen={() => onOpenNotification(notification)}
            onMarkRead={() => onMarkRead(notification.id)}
          />
        ))}
      </div>
    </div>
  );
}

/** US11 — central de notificações in-app (FR-039/FR-040). Não faz fetch
 * próprio: o estado (`notifications`/`unreadCount`/ações) vem de
 * `AuthenticatedLayout` via `Outlet context` — a MESMA instância que também
 * alimenta o badge da sidebar, então marcar como lida aqui atualiza os dois
 * lugares em uma só chamada (`useNotifications`, ver seu comentário). */
export function NotificationsPage() {
  const navigate = useNavigate();
  const { notifications, unreadCount, isLoading, error, markAsRead, markAllAsRead } =
    useOutletContext<UseNotificationsResult>();
  const [isMarkingAll, setIsMarkingAll] = useState(false);

  async function handleOpen(notification: Notification) {
    if (!notification.is_read) {
      await markAsRead(notification.id);
    }
    if (notification.task_id) {
      navigate(`/tasks/${notification.task_id}`);
    }
  }

  async function handleMarkAllRead() {
    setIsMarkingAll(true);
    try {
      await markAllAsRead();
    } finally {
      setIsMarkingAll(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <NotificationsHero
        isLoading={isLoading}
        unreadCount={unreadCount}
        isMarkingAll={isMarkingAll}
        onMarkAllRead={() => void handleMarkAllRead()}
      />

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Skeleton className="h-64 w-full rounded-2xl" />
          <Skeleton className="h-64 w-full rounded-2xl" />
          <Skeleton className="h-64 w-full rounded-2xl" />
        </div>
      )}

      {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

      {!isLoading && !error && notifications.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed py-16 text-center">
          <Bell className="size-8 text-muted-foreground/40" strokeWidth={1.5} />
          <p className="text-sm text-muted-foreground">Nenhuma notificação por aqui ainda.</p>
        </div>
      )}

      {!isLoading && !error && notifications.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {COLUMNS.map((column) => (
            <NotificationColumn
              key={column.type}
              type={column.type}
              label={column.label}
              icon={column.icon}
              iconWrapperClass={column.iconWrapperClass}
              columnTintClass={column.columnTintClass}
              accentClass={column.accentClass}
              countBadgeClass={column.countBadgeClass}
              notifications={notifications.filter((notification) => notification.type === column.type)}
              onOpenNotification={(notification) => void handleOpen(notification)}
              onMarkRead={(notificationId) => void markAsRead(notificationId)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
