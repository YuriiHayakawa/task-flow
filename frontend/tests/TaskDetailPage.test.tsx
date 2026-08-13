import { render, screen, waitFor } from "@testing-library/react";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AuthProvider } from "@/contexts/AuthContext";
import { TaskDetailPage } from "@/pages/TaskDetailPage";
import httpClient, { setStoredToken } from "@/services/httpClient";
import type { Task } from "@/types/task";
import type { User } from "@/types/user";
import type { Workspace, WorkspaceMember, WorkspaceRole } from "@/types/workspace";

const TASK_ID = "33333333-3333-3333-3333-333333333333";
const WORKSPACE_ID = "22222222-2222-2222-2222-222222222222";
const CURRENT_USER_ID = "11111111-1111-1111-1111-111111111111";
const CREATOR_ID = "44444444-4444-4444-4444-444444444444";
const ASSIGNEE_ID = "55555555-5555-5555-5555-555555555555";

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

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: TASK_ID,
    title: "Tarefa de teste",
    description: "Descrição",
    status: "PENDING",
    priority: "MEDIUM",
    due_date: null,
    assignee_id: ASSIGNEE_ID,
    creator_id: CREATOR_ID,
    workspace_id: WORKSPACE_ID,
    project_id: null,
    completed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function makeWorkspace(myRole: WorkspaceRole): Workspace {
  return {
    id: WORKSPACE_ID,
    name: "Time de Teste",
    description: null,
    my_role: myRole,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function makeMembers(): WorkspaceMember[] {
  return [
    { user_id: CURRENT_USER_ID, name: "Usuário Atual", email: "atual@example.com", role: "MEMBER", joined_at: "2026-01-01T00:00:00Z" },
    { user_id: CREATOR_ID, name: "Criador", email: "criador@example.com", role: "OWNER", joined_at: "2026-01-01T00:00:00Z" },
    { user_id: ASSIGNEE_ID, name: "Bea Responsável", email: "responsavel@example.com", role: "MEMBER", joined_at: "2026-01-01T00:00:00Z" },
  ];
}

function ok(data: unknown, config: InternalAxiosRequestConfig): AxiosResponse {
  return { data, status: 200, statusText: "OK", headers: {}, config } as AxiosResponse;
}

function fakeAdapter(task: Task, myRole: WorkspaceRole): AxiosAdapter {
  return (config) => {
    const method = config.method?.toLowerCase();
    const url = config.url ?? "";

    if (method === "get" && url === "/users/me") return Promise.resolve(ok(makeUser(), config));
    if (method === "get" && url === `/tasks/${TASK_ID}`) return Promise.resolve(ok(task, config));
    if (method === "get" && url === `/workspaces/${WORKSPACE_ID}`) {
      return Promise.resolve(ok(makeWorkspace(myRole), config));
    }
    if (method === "get" && url === `/workspaces/${WORKSPACE_ID}/members`) {
      const items = makeMembers();
      return Promise.resolve(ok({ items, page: 1, page_size: 20, total: items.length }, config));
    }
    if (method === "get" && url === `/tasks/${TASK_ID}/members`) {
      // Só o responsável como participante implícito (added_at: null) —
      // suficiente para estes testes, que focam em visibilidade de ação
      // sobre a tarefa em si, não na lista de participantes.
      const assignee = makeMembers().find((member) => member.user_id === task.assignee_id);
      return Promise.resolve(
        ok(
          assignee ? [{ user_id: assignee.user_id, name: assignee.name, email: assignee.email, added_at: null }] : [],
          config,
        ),
      );
    }
    if (method === "get" && url === `/tasks/${TASK_ID}/comments`) {
      const items = [
        {
          id: "66666666-6666-6666-6666-666666666666",
          author_id: task.creator_id,
          author_name: "Criador",
          author_email: "criador@example.com",
          content: "Primeiro comentário.",
          created_at: "2026-01-02T10:00:00Z",
        },
      ];
      return Promise.resolve(ok({ items, page: 1, page_size: 20, total: items.length }, config));
    }
    return Promise.reject(new Error(`requisição inesperada: ${method} ${url}`));
  };
}

function renderPage(task: Task, myRole: WorkspaceRole) {
  setStoredToken("fake-token");
  httpClient.defaults.adapter = fakeAdapter(task, myRole);

  return render(
    <MemoryRouter initialEntries={[`/tasks/${TASK_ID}`]}>
      <AuthProvider>
        <Routes>
          <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("TaskDetailPage — visibilidade de ações por posição do usuário", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("criador e Owner do workspace: vê marcar concluída, editar e excluir", async () => {
    const task = makeTask({ creator_id: CURRENT_USER_ID, assignee_id: ASSIGNEE_ID });
    renderPage(task, "OWNER");

    await waitFor(() => expect(screen.getByText("Tarefa de teste")).toBeInTheDocument());

    expect(screen.getByRole("button", { name: "Marcar como concluída" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Editar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Excluir" })).toBeInTheDocument();
  });

  it("responsável (não criador, Member comum): edita mas não exclui", async () => {
    const task = makeTask({ creator_id: CREATOR_ID, assignee_id: CURRENT_USER_ID });
    renderPage(task, "MEMBER");

    await waitFor(() => expect(screen.getByText("Tarefa de teste")).toBeInTheDocument());

    expect(screen.getByRole("button", { name: "Editar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Marcar como concluída" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Excluir" })).not.toBeInTheDocument();
  });

  it("Member comum sem ser criador nem responsável: não vê nenhuma ação", async () => {
    const task = makeTask({ creator_id: CREATOR_ID, assignee_id: ASSIGNEE_ID });
    renderPage(task, "MEMBER");

    await waitFor(() => expect(screen.getByText("Tarefa de teste")).toBeInTheDocument());

    expect(screen.queryByRole("button", { name: "Editar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Excluir" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Marcar como concluída" })).not.toBeInTheDocument();
  });

  it("Admin do workspace, sem ser criador nem responsável: edita e exclui mesmo assim", async () => {
    const task = makeTask({ creator_id: CREATOR_ID, assignee_id: ASSIGNEE_ID });
    renderPage(task, "ADMIN");

    // A permissão de Owner/Admin depende de `useWorkspace`, buscado só depois
    // que a própria tarefa carrega (encadeamento assíncrono) — espera o botão
    // em si, não só o título, para não checar antes dessa segunda busca.
    expect(await screen.findByRole("button", { name: "Editar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Excluir" })).toBeInTheDocument();
  });
});

describe("TaskDetailPage — seção de participantes (US5)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("lista o responsável como participante implícito, com a badge Responsável", async () => {
    const task = makeTask({ creator_id: CURRENT_USER_ID, assignee_id: ASSIGNEE_ID });
    renderPage(task, "OWNER");

    await waitFor(() => expect(screen.getByText("Responsável")).toBeInTheDocument());
    expect(screen.getAllByText("Responsável").length).toBeGreaterThan(0);
  });

  it("criador/Owner (pode editar): vê o botão de adicionar participante", async () => {
    const task = makeTask({ creator_id: CURRENT_USER_ID, assignee_id: ASSIGNEE_ID });
    renderPage(task, "OWNER");

    await waitFor(() => expect(screen.getByText("Tarefa de teste")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Adicionar" })).toBeInTheDocument();
  });

  it("Member comum sem ser criador nem responsável: não vê botão de adicionar participante", async () => {
    const task = makeTask({ creator_id: CREATOR_ID, assignee_id: ASSIGNEE_ID });
    renderPage(task, "MEMBER");

    await waitFor(() => expect(screen.getByText("Tarefa de teste")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Adicionar" })).not.toBeInTheDocument();
  });

  it("tarefa pessoal (sem workspace): não exibe a seção de participantes", async () => {
    const task = makeTask({
      creator_id: CURRENT_USER_ID,
      assignee_id: CURRENT_USER_ID,
      workspace_id: null,
      project_id: null,
    });
    renderPage(task, "OWNER");

    await waitFor(() => expect(screen.getByText("Tarefa de teste")).toBeInTheDocument());
    expect(screen.queryByText("Participantes")).not.toBeInTheDocument();
  });
});

describe("TaskDetailPage — seção de comentários (US6)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("lista os comentários existentes, com autor e conteúdo", async () => {
    const task = makeTask({ creator_id: CREATOR_ID, assignee_id: ASSIGNEE_ID });
    renderPage(task, "MEMBER");

    expect(await screen.findByText("Primeiro comentário.")).toBeInTheDocument();
    // "Criador" também aparece em "Criada por:" — checa só que o autor do
    // comentário está presente em algum lugar da página, sem exigir
    // unicidade do nome.
    expect(screen.getAllByText("Criador").length).toBeGreaterThan(0);
  });

  it("responsável (participante implícito): formulário de comentário habilitado", async () => {
    const task = makeTask({ creator_id: CREATOR_ID, assignee_id: CURRENT_USER_ID });
    renderPage(task, "MEMBER");

    const textarea = await screen.findByPlaceholderText("Escreva um comentário...");
    expect(textarea).not.toBeDisabled();
  });

  it("Member comum sem ser participante: formulário de comentário desabilitado", async () => {
    const task = makeTask({ creator_id: CREATOR_ID, assignee_id: ASSIGNEE_ID });
    renderPage(task, "MEMBER");

    const textarea = await screen.findByPlaceholderText(
      "Você precisa ser participante desta tarefa para comentar.",
    );
    expect(textarea).toBeDisabled();
  });

  it("tarefa pessoal (sem workspace): seção de comentários continua visível e habilitada para o criador", async () => {
    const task = makeTask({
      creator_id: CURRENT_USER_ID,
      assignee_id: CURRENT_USER_ID,
      workspace_id: null,
      project_id: null,
    });
    renderPage(task, "OWNER");

    expect(await screen.findByText("Comentários")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Escreva um comentário...")).not.toBeDisabled();
  });
});
