import { render, screen } from "@testing-library/react";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AuthProvider } from "@/contexts/AuthContext";
import { ProjectsPage } from "@/pages/ProjectsPage";
import httpClient, { setStoredToken } from "@/services/httpClient";
import type { User } from "@/types/user";

const WORKSPACE_ID = "22222222-2222-2222-2222-222222222222";
const CURRENT_USER_ID = "11111111-1111-1111-1111-111111111111";

function makeUser(): User {
  return {
    id: CURRENT_USER_ID,
    name: "Usuário Atual",
    email: "atual@example.com",
    is_active: true,
    is_system_admin: false,
    created_at: "2026-01-01T00:00:00Z",
  };
}

function ok(data: unknown, config: InternalAxiosRequestConfig): AxiosResponse {
  return { data, status: 200, statusText: "OK", headers: {}, config } as AxiosResponse;
}

/** 003-membros-projeto/US3 — Admin vê a listagem completa do workspace,
 * incluindo um projeto do qual não é membro (`is_member: false`). */
function fakeAdapter(): AxiosAdapter {
  return (config) => {
    const method = config.method?.toLowerCase();
    const url = config.url ?? "";

    if (method === "get" && url === "/users/me") return Promise.resolve(ok(makeUser(), config));
    if (method === "get" && url === `/workspaces/${WORKSPACE_ID}`) {
      return Promise.resolve(
        ok(
          {
            id: WORKSPACE_ID,
            name: "Time de Produto",
            description: null,
            my_role: "ADMIN",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
          config,
        ),
      );
    }
    if (method === "get" && url === `/workspaces/${WORKSPACE_ID}/projects`) {
      const items = [
        {
          id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
          workspace_id: WORKSPACE_ID,
          name: "Projeto Aberto",
          description: null,
          is_member: true,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
        {
          id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
          workspace_id: WORKSPACE_ID,
          name: "Projeto Restrito",
          description: null,
          is_member: false,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ];
      return Promise.resolve(ok({ items, page: 1, page_size: 20, total: items.length }, config));
    }
    return Promise.reject(new Error(`requisição inesperada: ${method} ${url}`));
  };
}

function renderPage() {
  setStoredToken("fake-token");
  httpClient.defaults.adapter = fakeAdapter();

  return render(
    <MemoryRouter initialEntries={[`/workspaces/${WORKSPACE_ID}/projects`]}>
      <AuthProvider>
        <Routes>
          <Route path="/workspaces/:workspaceId/projects" element={<ProjectsPage />} />
          <Route path="/workspaces/:workspaceId/projects/:projectId" element={<p>Detalhe do projeto</p>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("ProjectsPage — 003-membros-projeto: projeto sem acesso fica bloqueado", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("projeto com is_member: false aparece na lista, mas bloqueado (sem navegação)", async () => {
    renderPage();

    await screen.findByText("Projeto Aberto");
    expect(screen.getByText("Projeto Restrito")).toBeInTheDocument();
    expect(screen.getByText("Sem acesso")).toBeInTheDocument();

    // O card do projeto sem acesso não é um botão clicável (não navega).
    expect(screen.queryByRole("button", { name: /Projeto Restrito/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Projeto Aberto/ })).toBeInTheDocument();
  });
});
