import { render, screen, waitFor } from "@testing-library/react";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AuthProvider } from "@/contexts/AuthContext";
import { WorkspaceMembersPage } from "@/pages/WorkspaceMembersPage";
import httpClient, { setStoredToken } from "@/services/httpClient";
import type { User } from "@/types/user";
import type { Workspace, WorkspaceMember, WorkspaceRole } from "@/types/workspace";

const WORKSPACE_ID = "22222222-2222-2222-2222-222222222222";
const CURRENT_USER_ID = "11111111-1111-1111-1111-111111111111";

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: CURRENT_USER_ID,
    name: "Usuário Atual",
    email: "atual@example.com",
    is_active: true,
    is_system_admin: false,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function makeWorkspace(myRole: WorkspaceRole): Workspace {
  return {
    id: WORKSPACE_ID,
    name: "Time de Produto",
    description: "Workspace de exemplo",
    my_role: myRole,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function makeMembers(myRole: WorkspaceRole): WorkspaceMember[] {
  return [
    { user_id: CURRENT_USER_ID, name: "Usuário Atual", email: "atual@example.com", role: myRole, joined_at: "2026-01-01T00:00:00Z" },
    { user_id: "member-1", name: "Bea Member", email: "bea@example.com", role: "MEMBER", joined_at: "2026-01-02T00:00:00Z" },
    { user_id: "admin-1", name: "Caio Admin", email: "caio@example.com", role: "ADMIN", joined_at: "2026-01-03T00:00:00Z" },
  ];
}

function ok(data: unknown, config: InternalAxiosRequestConfig): AxiosResponse {
  return { data, status: 200, statusText: "OK", headers: {}, config } as AxiosResponse;
}

function fakeAdapter(myRole: WorkspaceRole): AxiosAdapter {
  return (config) => {
    const method = config.method?.toLowerCase();
    const url = config.url ?? "";

    if (method === "get" && url === "/users/me") {
      return Promise.resolve(ok(makeUser(), config));
    }
    if (method === "get" && url === `/workspaces/${WORKSPACE_ID}`) {
      return Promise.resolve(ok(makeWorkspace(myRole), config));
    }
    if (method === "get" && url === `/workspaces/${WORKSPACE_ID}/members`) {
      const items = makeMembers(myRole);
      return Promise.resolve(ok({ items, page: 1, page_size: 20, total: items.length }, config));
    }
    return Promise.reject(new Error(`requisição inesperada: ${method} ${url}`));
  };
}

function renderPage(myRole: WorkspaceRole) {
  setStoredToken("fake-token");
  httpClient.defaults.adapter = fakeAdapter(myRole);

  return render(
    <MemoryRouter initialEntries={[`/workspaces/${WORKSPACE_ID}/members`]}>
      <AuthProvider>
        <Routes>
          <Route path="/workspaces/:workspaceId/members" element={<WorkspaceMembersPage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("WorkspaceMembersPage — visibilidade de ações por role", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("Owner: vê adicionar membro, promover/rebaixar, remover e transferir titularidade", async () => {
    renderPage("OWNER");

    await waitFor(() => expect(screen.getByText("Bea Member")).toBeInTheDocument());

    expect(screen.getByRole("button", { name: "Adicionar membro" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Promover Bea Member a Admin" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rebaixar Caio Admin a Member" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remover Bea Member" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remover Caio Admin" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Transferir titularidade para Bea Member" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Transferir titularidade para Caio Admin" }),
    ).toBeInTheDocument();
  });

  it("Admin: vê adicionar membro e remover Member, mas não promove/rebaixa, não remove Admin nem transfere titularidade", async () => {
    renderPage("ADMIN");

    await waitFor(() => expect(screen.getByText("Bea Member")).toBeInTheDocument());

    expect(screen.getByRole("button", { name: "Adicionar membro" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remover Bea Member" })).toBeInTheDocument();

    expect(screen.queryByRole("button", { name: /Promover .* a Admin/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Rebaixar .* a Member/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remover Caio Admin" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Transferir titularidade/ })).not.toBeInTheDocument();
  });

  it("Member: não vê nenhuma ação de gestão — apenas a lista", async () => {
    renderPage("MEMBER");

    await waitFor(() => expect(screen.getByText("Bea Member")).toBeInTheDocument());
    expect(screen.getByText("Caio Admin")).toBeInTheDocument();

    expect(screen.queryByRole("button", { name: "Adicionar membro" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Promover .* a Admin/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Rebaixar .* a Member/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remover Bea Member" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remover Caio Admin" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Transferir titularidade/ })).not.toBeInTheDocument();
  });

  it("ninguém vê ação de gestão sobre a própria linha do Owner", async () => {
    renderPage("OWNER");

    await waitFor(() => expect(screen.getByText("Usuário Atual")).toBeInTheDocument());

    expect(screen.queryByRole("button", { name: /Remover Usuário Atual/ })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Transferir titularidade para Usuário Atual/ }),
    ).not.toBeInTheDocument();
  });
});
