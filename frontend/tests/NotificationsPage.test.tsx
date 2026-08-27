import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AuthProvider } from "@/contexts/AuthContext";
import { AppRoutes } from "@/routes";
import httpClient, { setStoredToken } from "@/services/httpClient";
import type { Notification } from "@/types/notification";
import type { User } from "@/types/user";

function makeUser(): User {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    name: "Usuário Atual",
    email: "atual@example.com",
    is_active: true,
    is_system_admin: false,
    created_at: "2026-01-01T00:00:00Z",
  };
}

function makeNotification(
  overrides: Partial<Notification> & Pick<Notification, "id">,
): Notification {
  return {
    type: "NEW_COMMENT",
    title: "Novo comentário",
    message: "Alguém comentou na sua tarefa.",
    task_id: null,
    is_read: false,
    created_at: "2026-01-01T10:00:00Z",
    ...overrides,
  };
}

function ok(data: unknown, config: InternalAxiosRequestConfig): AxiosResponse {
  return { data, status: 200, statusText: "OK", headers: {}, config } as AxiosResponse;
}

/** 001-taskflow-mvp/US11 — badge da sidebar e `NotificationsPage` compartilham
 * a mesma instância de `useNotifications` (`Outlet context`, ver
 * `AuthenticatedLayout`), então o fake precisa refletir mutações reais
 * (mesmo padrão de `ProfilePage.test.tsx`/`ProjectDetailPage.test.tsx`). */
function fakeAdapter(initialNotifications: Notification[]): AxiosAdapter {
  let notifications = initialNotifications;

  return (config) => {
    const method = config.method?.toLowerCase();
    const url = config.url ?? "";

    if (method === "get" && url === "/users/me") return Promise.resolve(ok(makeUser(), config));
    if (method === "get" && url === "/notifications") {
      return Promise.resolve(
        ok({ items: notifications, page: 1, page_size: 50, total: notifications.length }, config),
      );
    }
    const readMatch = /^\/notifications\/([^/]+)\/read$/.exec(url);
    if (method === "patch" && readMatch) {
      const id = readMatch[1];
      notifications = notifications.map((notification) =>
        notification.id === id ? { ...notification, is_read: true } : notification,
      );
      return Promise.resolve(ok(notifications.find((notification) => notification.id === id), config));
    }
    if (method === "patch" && url === "/notifications/read-all") {
      const updated = notifications.filter((notification) => !notification.is_read).length;
      notifications = notifications.map((notification) => ({ ...notification, is_read: true }));
      return Promise.resolve(ok({ updated }, config));
    }
    return Promise.reject(new Error(`requisição inesperada: ${method} ${url}`));
  };
}

function renderAt(notifications: Notification[]) {
  setStoredToken("fake-token");
  httpClient.defaults.adapter = fakeAdapter(notifications);

  return render(
    <MemoryRouter initialEntries={["/notifications"]}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("NotificationsPage — 001-taskflow-mvp/US11: notificações in-app", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("lista notificações e reflete a contagem de não lidas no hero e no badge da sidebar", async () => {
    renderAt([
      makeNotification({ id: "n1", title: "Prazo se aproximando", type: "DUE_SOON", is_read: false }),
      makeNotification({ id: "n2", title: "Novo comentário", type: "NEW_COMMENT", is_read: true }),
    ]);

    await screen.findByText("Prazo se aproximando");
    expect(screen.getByText("Novo comentário")).toBeInTheDocument();
    expect(screen.getByText(/1 não lida/)).toBeInTheDocument();
    // Badge da sidebar (`SidebarMenuBadge`) — mesma contagem, mesma instância
    // de `useNotifications` compartilhada via `Outlet context`. Escopado ao
    // <li> do item da sidebar (o badge é IRMÃO do link, não filho — exigência
    // de posicionamento do `SidebarMenuBadge`): agora cada coluna do board
    // também tem seu próprio contador, então "1" sozinho não é mais único.
    const sidebarLink = screen.getByRole("link", { name: /Notificações/ });
    const sidebarItem = sidebarLink.closest("li");
    expect(sidebarItem).not.toBeNull();
    expect(within(sidebarItem!).getByText("1")).toBeInTheDocument();
  });

  it("marcar uma notificação como lida atualiza ela e o contador, sem apagá-la da lista", async () => {
    renderAt([makeNotification({ id: "n1", title: "Prazo se aproximando", is_read: false })]);

    await screen.findByText("Prazo se aproximando");
    fireEvent.click(screen.getByRole("button", { name: "Marcar como lida" }));

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Marcar como lida" })).not.toBeInTheDocument();
    });
    expect(screen.getByText("Tudo em dia")).toBeInTheDocument();
    expect(screen.getByText("Prazo se aproximando")).toBeInTheDocument();
  });

  it("'Marcar todas como lidas' zera o contador sem remover nenhuma notificação da lista", async () => {
    renderAt([
      makeNotification({ id: "n1", title: "Prazo se aproximando", is_read: false }),
      makeNotification({ id: "n2", title: "Alteração na tarefa", type: "TASK_CHANGED", is_read: false }),
    ]);

    await screen.findByText("Prazo se aproximando");
    fireEvent.click(screen.getByRole("button", { name: "Marcar todas como lidas" }));

    await waitFor(() => {
      expect(screen.getByText("Tudo em dia")).toBeInTheDocument();
    });
    expect(screen.getByText("Prazo se aproximando")).toBeInTheDocument();
    expect(screen.getByText("Alteração na tarefa")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Marcar como lida" })).not.toBeInTheDocument();
  });

  it("sem notificações, mostra o estado vazio sem erro", async () => {
    renderAt([]);

    expect(await screen.findByText("Nenhuma notificação por aqui ainda.")).toBeInTheDocument();
  });
});
