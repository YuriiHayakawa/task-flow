import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AuthProvider } from "@/contexts/AuthContext";
import { AppRoutes } from "@/routes";
import httpClient, { setStoredToken } from "@/services/httpClient";
import type { User } from "@/types/user";

const ADMIN_ID = "11111111-1111-1111-1111-111111111111";

function makeUser(overrides: Partial<User> & Pick<User, "id" | "name" | "email">): User {
  return {
    is_active: true,
    is_system_admin: false,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function ok(data: unknown, config: InternalAxiosRequestConfig): AxiosResponse {
  return { data, status: 200, statusText: "OK", headers: {}, config } as AxiosResponse;
}

/** 001-taskflow-mvp/US13 — administração de usuários da plataforma. Fake
 * reimplementa em memória o filtro `is_active` e a mutação de status, mesmo
 * padrão dos demais fakes do projeto (ex.: `ProfilePage.test.tsx`). */
function fakeAdapter(currentUser: User, initialUsers: User[]): AxiosAdapter {
  let users = initialUsers;

  return (config) => {
    const method = config.method?.toLowerCase();
    const url = config.url ?? "";

    if (method === "get" && url === "/users/me") return Promise.resolve(ok(currentUser, config));
    if (method === "get" && url === "/admin/users") {
      const params = (config.params ?? {}) as { is_active?: boolean };
      const filtered =
        params.is_active === undefined ? users : users.filter((user) => user.is_active === params.is_active);
      return Promise.resolve(
        ok({ items: filtered, page: 1, page_size: 20, total: filtered.length }, config),
      );
    }
    const statusMatch = /^\/admin\/users\/([^/]+)\/status$/.exec(url);
    if (method === "patch" && statusMatch) {
      const id = statusMatch[1];
      const body = JSON.parse(config.data as string) as { is_active: boolean };
      users = users.map((user) => (user.id === id ? { ...user, is_active: body.is_active } : user));
      return Promise.resolve(ok(users.find((user) => user.id === id), config));
    }
    return Promise.reject(new Error(`requisição inesperada: ${method} ${url}`));
  };
}

function renderAt(path: string, currentUser: User, users: User[] = []) {
  setStoredToken("fake-token");
  httpClient.defaults.adapter = fakeAdapter(currentUser, users);

  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("AdminUsersPage — 001-taskflow-mvp/US13: administração de usuários da plataforma", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("bloqueia o acesso para quem não é System Admin, redirecionando para /dashboard", async () => {
    const regularUser = makeUser({
      id: "22222222-2222-2222-2222-222222222222",
      name: "Usuário Comum",
      email: "comum@example.com",
      is_system_admin: false,
    });
    renderAt("/admin", regularUser);

    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Usuários" })).not.toBeInTheDocument();
    });
  });

  it("System Admin acessa, lista contas e desativa (com confirmação) e reativa", async () => {
    const admin = makeUser({
      id: ADMIN_ID,
      name: "Admin Exemplo",
      email: "admin@example.com",
      is_system_admin: true,
    });
    const targetActive = makeUser({
      id: "33333333-3333-3333-3333-333333333333",
      name: "Conta Ativa",
      email: "ativa@example.com",
      is_active: true,
    });
    const targetInactive = makeUser({
      id: "44444444-4444-4444-4444-444444444444",
      name: "Conta Desativada",
      email: "desativada@example.com",
      is_active: false,
    });
    renderAt("/admin", admin, [admin, targetActive, targetInactive]);

    // A lista depende de uma requisição própria (`GET /admin/users`),
    // separada da que resolve o hero (`/users/me`) — esperar pelo conteúdo
    // da lista em si, não só pelo hero, evita corrida entre as duas.
    await screen.findByText("Conta Ativa");
    expect(screen.getByText("Conta Desativada")).toBeInTheDocument();

    // Desativar exige confirmação — o botão da linha só ABRE o diálogo (nomes
    // com o da pessoa, pra não colidir com o "Desativar" do próprio diálogo).
    fireEvent.click(screen.getByRole("button", { name: "Desativar Conta Ativa" }));
    fireEvent.click(await screen.findByRole("button", { name: "Desativar" }));

    await waitFor(() => {
      expect(screen.getAllByText("Desativada")).toHaveLength(2);
    });

    // Reativar não pede confirmação.
    fireEvent.click(screen.getByRole("button", { name: "Reativar Conta Desativada" }));
    await waitFor(() => {
      expect(screen.getAllByText("Ativa")).toHaveLength(1);
    });
  });

  it("não mostra ação de desativar/reativar para a própria conta do admin logado", async () => {
    const admin = makeUser({
      id: ADMIN_ID,
      name: "Admin Exemplo",
      email: "admin@example.com",
      is_system_admin: true,
    });
    renderAt("/admin", admin, [admin]);

    // `findByText` sozinho não basta aqui: o mesmo nome também aparece no
    // rodapé da sidebar (`AuthenticatedLayout`), então espera-se especificamente
    // pela marca "(você)" da linha da lista, exclusiva do cartão de usuário.
    await screen.findByText("(você)");
    expect(screen.queryByRole("button", { name: "Desativar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reativar" })).not.toBeInTheDocument();
  });

  it("filtro 'Ativas'/'Desativadas' restringe a lista exibida", async () => {
    const admin = makeUser({
      id: ADMIN_ID,
      name: "Admin Exemplo",
      email: "admin@example.com",
      is_system_admin: true,
    });
    const targetActive = makeUser({
      id: "33333333-3333-3333-3333-333333333333",
      name: "Conta Ativa",
      email: "ativa@example.com",
      is_active: true,
    });
    const targetInactive = makeUser({
      id: "44444444-4444-4444-4444-444444444444",
      name: "Conta Desativada",
      email: "desativada@example.com",
      is_active: false,
    });
    renderAt("/admin", admin, [admin, targetActive, targetInactive]);

    await screen.findByText("Conta Ativa");
    fireEvent.click(screen.getByRole("button", { name: "Desativadas" }));

    await waitFor(() => {
      expect(screen.queryByText("Conta Ativa")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Conta Desativada")).toBeInTheDocument();
  });
});
