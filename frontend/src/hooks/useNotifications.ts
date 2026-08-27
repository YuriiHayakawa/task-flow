import { useCallback, useEffect, useMemo, useState } from "react";

import * as notificationService from "@/services/notificationService";
import type { Notification } from "@/types/notification";

export interface UseNotificationsResult {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;
  error: string | null;
  markAsRead: (notificationId: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  refetch: () => Promise<void>;
}

/** Notificações do usuário autenticado (US11) — instanciado uma única vez em
 * `AuthenticatedLayout` (não em cada página) e compartilhado com as rotas
 * filhas via `Outlet context` do React Router: o badge da sidebar e a
 * `NotificationsPage` precisam enxergar exatamente o mesmo estado, senão
 * marcar como lida na página não atualizaria o contador da sidebar até uma
 * navegação forçar um remount. Mesmo padrão de "mutate then refetch" já
 * usado em `useChecklist`/`useComments`, sem patch otimista local. */
export function useNotifications(): UseNotificationsResult {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await notificationService.list();
      setNotifications(response.items);
    } catch {
      setError("Não foi possível carregar as notificações.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchNotifications();
  }, [fetchNotifications]);

  const markAsRead = useCallback(
    async (notificationId: string) => {
      await notificationService.markAsRead(notificationId);
      await fetchNotifications();
    },
    [fetchNotifications],
  );

  const markAllAsRead = useCallback(async () => {
    await notificationService.markAllAsRead();
    await fetchNotifications();
  }, [fetchNotifications]);

  const unreadCount = useMemo(
    () => notifications.filter((notification) => !notification.is_read).length,
    [notifications],
  );

  return {
    notifications,
    unreadCount,
    isLoading,
    error,
    markAsRead,
    markAllAsRead,
    refetch: fetchNotifications,
  };
}
