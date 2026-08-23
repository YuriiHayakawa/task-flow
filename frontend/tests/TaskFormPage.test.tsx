import { fireEvent, render, screen } from "@testing-library/react";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AuthProvider } from "@/contexts/AuthContext";
import { TaskFormPage } from "@/pages/TaskFormPage";
import httpClient, { setStoredToken } from "@/services/httpClient";
import type { Task } from "@/types/task";
import type { User } from "@/types/user";

const TASK_ID = "33333333-3333-3333-3333-333333333333";
const WORKSPACE_ID = "22222222-2222-2222-2222-222222222222";
const PROJECT_ID = "44444444-4444-4444-4444-444444444444";
const CURRENT_USER_ID = "11111111-1111-1111-1111-111111111111";
const PROJECT_MEMBER_ID = "55555555-5555-5555-5555-555555555555";
const WORKSPACE_ONLY_MEMBER_ID = "66666666-6666-6666-6666-666666666666";

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

function makePersonalTask(): Task {
  return {
    id: TASK_ID,
    title: "Tarefa pessoal",
    description: null,
    status: "PENDING",
    priority: "MEDIUM",
    due_date: null,
    assignee_id: CURRENT_USER_ID,
    creator_id: CURRENT_USER_ID,
    workspace_id: null,
    project_id: null,
    completed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function makeWorkspaceTask(): Task {
  return { ...makePersonalTask(), workspace_id: WORKSPACE_ID };
}

function ok(data: unknown, config: InternalAxiosRequestConfig): AxiosResponse {
  return { data, status: 200, statusText: "OK", headers: {}, config } as AxiosResponse;
}

/** `PATCH` reflete a mudança na próxima `GET` — `useTask.updateTask` refaz o
 * fetch depois de atualizar (mesmo padrão de `TaskDetailPage.test.tsx`). */
function fakeAdapter(initialTask: Task): AxiosAdapter {
  let task = initialTask;
  return (config) => {
    const method = config.method?.toLowerCase();
    const url = config.url ?? "";

    if (method === "get" && url === "/users/me") return Promise.resolve(ok(makeUser(), config));
    if (method === "get" && url === `/tasks/${TASK_ID}`) return Promise.resolve(ok(task, config));
    if (method === "patch" && url === `/tasks/${TASK_ID}`) {
      const body = JSON.parse(config.data as string) as Partial<Task>;
      task = { ...task, ...body };
      return Promise.resolve(ok(task, config));
    }
    if (method === "get" && url === `/workspaces/${WORKSPACE_ID}/members`) {
      const items = [
        { user_id: CURRENT_USER_ID, name: "Usuário Atual", email: "atual@example.com", role: "OWNER", joined_at: "2026-01-01T00:00:00Z" },
      ];
      return Promise.resolve(ok({ items, page: 1, page_size: 20, total: items.length }, config));
    }
    if (method === "get" && url === `/workspaces/${WORKSPACE_ID}/projects`) {
      return Promise.resolve(ok({ items: [], page: 1, page_size: 20, total: 0 }, config));
    }
    return Promise.reject(new Error(`requisição inesperada: ${method} ${url}`));
  };
}

function renderEdit(task: Task) {
  setStoredToken("fake-token");
  httpClient.defaults.adapter = fakeAdapter(task);

  return render(
    <MemoryRouter initialEntries={[`/tasks/${TASK_ID}/edit`]}>
      <AuthProvider>
        <Routes>
          <Route path="/tasks/:taskId/edit" element={<TaskFormPage />} />
          <Route path="/tasks/:taskId" element={<p>Detalhes da tarefa</p>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

/** 003-membros-projeto/FR-009 — o seletor de responsável precisa listar só
 * membros do PROJETO (não todo o workspace) quando um projeto já está
 * selecionado na criação. */
function fakeCreateWithProjectAdapter(): AxiosAdapter {
  return (config) => {
    const method = config.method?.toLowerCase();
    const url = config.url ?? "";

    if (method === "get" && url === "/users/me") return Promise.resolve(ok(makeUser(), config));
    if (method === "get" && url === `/workspaces/${WORKSPACE_ID}/members`) {
      const items = [
        { user_id: CURRENT_USER_ID, name: "Usuário Atual", email: "atual@example.com", role: "OWNER", joined_at: "2026-01-01T00:00:00Z" },
        { user_id: PROJECT_MEMBER_ID, name: "Membro do Projeto", email: "projeto@example.com", role: "MEMBER", joined_at: "2026-01-01T00:00:00Z" },
        { user_id: WORKSPACE_ONLY_MEMBER_ID, name: "Só do Workspace", email: "workspace@example.com", role: "MEMBER", joined_at: "2026-01-01T00:00:00Z" },
      ];
      return Promise.resolve(ok({ items, page: 1, page_size: 20, total: items.length }, config));
    }
    if (method === "get" && url === `/workspaces/${WORKSPACE_ID}/projects`) {
      const items = [
        {
          id: PROJECT_ID,
          workspace_id: WORKSPACE_ID,
          name: "Projeto Alpha",
          description: null,
          is_member: true,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ];
      return Promise.resolve(ok({ items, page: 1, page_size: 20, total: items.length }, config));
    }
    if (method === "get" && url === `/projects/${PROJECT_ID}/members`) {
      const items = [
        { user_id: CURRENT_USER_ID, name: "Usuário Atual", email: "atual@example.com", joined_at: "2026-01-01T00:00:00Z" },
        { user_id: PROJECT_MEMBER_ID, name: "Membro do Projeto", email: "projeto@example.com", joined_at: "2026-01-01T00:00:00Z" },
      ];
      return Promise.resolve(ok({ items, page: 1, page_size: 20, total: items.length }, config));
    }
    return Promise.reject(new Error(`requisição inesperada: ${method} ${url}`));
  };
}

function renderCreateWithProject() {
  setStoredToken("fake-token");
  httpClient.defaults.adapter = fakeCreateWithProjectAdapter();

  return render(
    <MemoryRouter initialEntries={[`/tasks/new?workspace_id=${WORKSPACE_ID}&project_id=${PROJECT_ID}`]}>
      <AuthProvider>
        <Routes>
          <Route path="/tasks/new" element={<TaskFormPage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("TaskFormPage — edição de tarefa pessoal x de workspace", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("tarefa pessoal: oculta Responsável/Projeto (não existem nesse caso) e salva normalmente", async () => {
    renderEdit(makePersonalTask());

    // `findByDisplayValue` (não `findByLabelText` + `toHaveValue`) porque o
    // valor chega por um `useEffect` separado do que monta o input — este
    // último resolve assim que o campo aparece, ainda vazio, sem esperar o
    // valor ser sincronizado da tarefa.
    const titleInput = await screen.findByDisplayValue("Tarefa pessoal");

    expect(screen.queryByText("Responsável")).not.toBeInTheDocument();
    expect(screen.queryByText("Projeto")).not.toBeInTheDocument();

    fireEvent.change(titleInput, { target: { value: "Tarefa pessoal revisada" } });
    // Regressão do bug que este teste protege: se o Select de Responsável
    // fosse renderizado sem `members` para popular seus `SelectItem`s, o
    // Radix Select zeraria `assigneeId` sozinho e este botão ficaria
    // desabilitado para sempre.
    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));

    expect(await screen.findByText("Detalhes da tarefa")).toBeInTheDocument();
  });

  it("tarefa de workspace: continua exibindo Responsável e Projeto", async () => {
    renderEdit(makeWorkspaceTask());

    await screen.findByLabelText("Título");

    expect(screen.getByText("Responsável")).toBeInTheDocument();
    expect(screen.getByText("Projeto")).toBeInTheDocument();
  });
});

describe("TaskFormPage — 003-membros-projeto: responsável restrito a membros do projeto", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("com um projeto selecionado, o seletor de responsável lista só membros do projeto", async () => {
    renderCreateWithProject();

    await screen.findByLabelText("Título");
    fireEvent.click(screen.getByRole("combobox", { name: "Responsável" }));

    expect(await screen.findByRole("option", { name: "Usuário Atual" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Membro do Projeto" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Só do Workspace" })).not.toBeInTheDocument();
  });
});
