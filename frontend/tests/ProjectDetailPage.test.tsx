import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AuthProvider } from "@/contexts/AuthContext";
import { ProjectDetailPage } from "@/pages/ProjectDetailPage";
import httpClient, { setStoredToken } from "@/services/httpClient";
import type { User } from "@/types/user";

const WORKSPACE_ID = "22222222-2222-2222-2222-222222222222";
const PROJECT_ID = "44444444-4444-4444-4444-444444444444";
const CURRENT_USER_ID = "11111111-1111-1111-1111-111111111111";
const NEW_MEMBER_ID = "77777777-7777-7777-7777-777777777777";

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

/** 003-membros-projeto/US1 — gestão de membros de um projeto a partir do
 * Sheet aberto pelo herói de `ProjectDetailPage`. Listas separadas: membros
 * do WORKSPACE (estático — quem já pode ser adicionado ao projeto) e
 * membros do PROJETO (começa só com o usuário atual, cresce ao adicionar). */
function fakeAdapter(): AxiosAdapter {
  const workspaceMembers = [
    { user_id: CURRENT_USER_ID, name: "Usuário Atual", email: "atual@example.com", role: "OWNER", joined_at: "2026-01-01T00:00:00Z" },
    { user_id: NEW_MEMBER_ID, name: "Novo Membro", email: "novo@example.com", role: "MEMBER", joined_at: "2026-01-01T00:00:00Z" },
  ];
  let projectMembers = [
    { user_id: CURRENT_USER_ID, name: "Usuário Atual", email: "atual@example.com", joined_at: "2026-01-01T00:00:00Z" },
  ];

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
            my_role: "OWNER",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
          config,
        ),
      );
    }
    if (method === "get" && url === `/workspaces/${WORKSPACE_ID}/members`) {
      return Promise.resolve(
        ok({ items: workspaceMembers, page: 1, page_size: 20, total: workspaceMembers.length }, config),
      );
    }
    if (method === "get" && url === `/projects/${PROJECT_ID}`) {
      return Promise.resolve(
        ok(
          {
            id: PROJECT_ID,
            workspace_id: WORKSPACE_ID,
            name: "Projeto Alpha",
            description: null,
            is_member: true,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
          config,
        ),
      );
    }
    if (method === "get" && url === "/tasks") {
      return Promise.resolve(ok({ items: [], page: 1, page_size: 20, total: 0 }, config));
    }
    if (method === "get" && url === `/projects/${PROJECT_ID}/members`) {
      return Promise.resolve(
        ok({ items: projectMembers, page: 1, page_size: 20, total: projectMembers.length }, config),
      );
    }
    if (method === "post" && url === `/projects/${PROJECT_ID}/members`) {
      const body = JSON.parse(config.data as string) as { user_id: string };
      const source = workspaceMembers.find((member) => member.user_id === body.user_id);
      if (!source) return Promise.reject(new Error("usuário não é membro do workspace"));
      const added = { user_id: source.user_id, name: source.name, email: source.email, joined_at: "2026-01-02T00:00:00Z" };
      projectMembers = [...projectMembers, added];
      return Promise.resolve(ok(added, config));
    }
    if (method === "delete" && url === `/projects/${PROJECT_ID}/members/${NEW_MEMBER_ID}`) {
      projectMembers = projectMembers.filter((member) => member.user_id !== NEW_MEMBER_ID);
      return Promise.resolve(ok(undefined, config));
    }
    return Promise.reject(new Error(`requisição inesperada: ${method} ${url}`));
  };
}

function renderPage() {
  setStoredToken("fake-token");
  httpClient.defaults.adapter = fakeAdapter();

  return render(
    <MemoryRouter initialEntries={[`/workspaces/${WORKSPACE_ID}/projects/${PROJECT_ID}`]}>
      <AuthProvider>
        <Routes>
          <Route
            path="/workspaces/:workspaceId/projects/:projectId"
            element={<ProjectDetailPage />}
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("ProjectDetailPage — 003-membros-projeto: gestão de membros do projeto", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("abre o Sheet de membros, lista, adiciona pelo dropdown (só membros do workspace) e remove", async () => {
    renderPage();

    await screen.findByText("Projeto Alpha");
    fireEvent.click(screen.getByRole("button", { name: "Membros" }));

    expect(await screen.findByText("Usuário Atual")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("combobox", { name: "Adicionar membro" }));
    fireEvent.click(await screen.findByRole("option", { name: /Novo Membro/ }));
    fireEvent.click(screen.getByRole("button", { name: "Adicionar" }));

    // `addMember` reconsulta a lista após o POST (mesmo padrão de
    // `useWorkspaceMembers`), o que alterna `isLoading` e pode desmontar/
    // remontar a linha entre a resolução de um `findByText` isolado e a
    // asserção seguinte. `waitFor` reconsulta o DOM a cada tentativa, então
    // absorve esse "flash" de loading em vez de prender uma referência que
    // pode ficar obsoleta.
    await waitFor(() => {
      expect(screen.getByText("Novo Membro")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Remover Novo Membro" }));
    fireEvent.click(await screen.findByRole("button", { name: "Remover" }));

    await waitFor(() => expect(screen.queryByText("Novo Membro")).not.toBeInTheDocument());
  });

  it("remoção bloqueada por tarefas ativas exibe a lista de tarefas pendentes (FR-010)", async () => {
    setStoredToken("fake-token");
    let members = [
      { user_id: CURRENT_USER_ID, name: "Usuário Atual", email: "atual@example.com", joined_at: "2026-01-01T00:00:00Z" },
      { user_id: NEW_MEMBER_ID, name: "Membro Ocupado", email: "ocupado@example.com", joined_at: "2026-01-01T00:00:00Z" },
    ];
    httpClient.defaults.adapter = ((config) => {
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
              my_role: "OWNER",
              created_at: "2026-01-01T00:00:00Z",
              updated_at: "2026-01-01T00:00:00Z",
            },
            config,
          ),
        );
      }
      if (method === "get" && url === `/workspaces/${WORKSPACE_ID}/members`) {
        return Promise.resolve(ok({ items: members, page: 1, page_size: 20, total: members.length }, config));
      }
      if (method === "get" && url === `/projects/${PROJECT_ID}`) {
        return Promise.resolve(
          ok(
            {
              id: PROJECT_ID,
              workspace_id: WORKSPACE_ID,
              name: "Projeto Alpha",
              description: null,
              is_member: true,
              created_at: "2026-01-01T00:00:00Z",
              updated_at: "2026-01-01T00:00:00Z",
            },
            config,
          ),
        );
      }
      if (method === "get" && url === "/tasks") {
        return Promise.resolve(ok({ items: [], page: 1, page_size: 20, total: 0 }, config));
      }
      if (method === "get" && url === `/projects/${PROJECT_ID}/members`) {
        return Promise.resolve(ok({ items: members, page: 1, page_size: 20, total: members.length }, config));
      }
      if (method === "delete" && url === `/projects/${PROJECT_ID}/members/${NEW_MEMBER_ID}`) {
        return Promise.reject({
          isAxiosError: true,
          response: {
            status: 409,
            data: {
              error: {
                code: "CONFLICT",
                message: "Este membro é responsável por tarefas ativas neste projeto.",
                details: [{ task_id: "99999999-9999-9999-9999-999999999999", title: "Tarefa em aberto" }],
              },
            },
          },
        });
      }
      return Promise.reject(new Error(`requisição inesperada: ${method} ${url}`));
    }) as AxiosAdapter;

    render(
      <MemoryRouter initialEntries={[`/workspaces/${WORKSPACE_ID}/projects/${PROJECT_ID}`]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/workspaces/:workspaceId/projects/:projectId"
              element={<ProjectDetailPage />}
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    await screen.findByText("Projeto Alpha");
    fireEvent.click(screen.getByRole("button", { name: "Membros" }));
    await screen.findByText("Membro Ocupado");

    fireEvent.click(screen.getByRole("button", { name: "Remover Membro Ocupado" }));
    fireEvent.click(await screen.findByRole("button", { name: "Remover" }));

    expect(await screen.findByText("Tarefa em aberto")).toBeInTheDocument();
    // A pessoa continua na lista — a remoção foi recusada.
    expect(screen.getByText("Membro Ocupado")).toBeInTheDocument();
  });
});
