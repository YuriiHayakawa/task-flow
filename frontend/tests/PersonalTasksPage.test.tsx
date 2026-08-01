import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type {
  AxiosAdapter,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import { beforeEach, describe, expect, it } from "vitest";

import { PersonalTasksPage } from "@/pages/PersonalTasksPage";
import httpClient from "@/services/httpClient";
import type { Task } from "@/types/task";

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: crypto.randomUUID(),
    title: "Tarefa de exemplo",
    description: null,
    status: "PENDING",
    priority: "MEDIUM",
    due_date: null,
    assignee_id: "user-1",
    creator_id: "user-1",
    workspace_id: null,
    project_id: null,
    completed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function ok(data: unknown, config: InternalAxiosRequestConfig): AxiosResponse {
  return { data, status: 200, statusText: "OK", headers: {}, config } as AxiosResponse;
}

/** Simula o backend real o suficiente para GET refletir os efeitos de
 * POST/PATCH — necessário porque `usePersonalTasks` recarrega a lista
 * (`GET /tasks`) após cada criação/edição. */
function fakeTaskBackend(initialTasks: Task[] = []): AxiosAdapter {
  let tasks = [...initialTasks];
  return (config) => {
    const method = config.method?.toLowerCase();
    const url = config.url ?? "";

    if (method === "get" && url === "/tasks") {
      return Promise.resolve(
        ok({ items: tasks, page: 1, page_size: 20, total: tasks.length }, config),
      );
    }
    if (method === "post" && url === "/tasks") {
      const body = JSON.parse(config.data as string) as Partial<Task>;
      const created = makeTask({ ...body, id: crypto.randomUUID() });
      tasks = [...tasks, created];
      return Promise.resolve(ok(created, config));
    }
    const patchMatch = method === "patch" ? url.match(/^\/tasks\/(.+)$/) : null;
    if (patchMatch) {
      const id = patchMatch[1];
      const body = JSON.parse(config.data as string) as Partial<Task>;
      tasks = tasks.map((task) => (task.id === id ? { ...task, ...body } : task));
      return Promise.resolve(ok(tasks.find((task) => task.id === id), config));
    }
    return Promise.reject(new Error(`requisição inesperada: ${method} ${url}`));
  };
}

describe("PersonalTasksPage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("exibe o estado vazio quando não há tarefas pessoais", async () => {
    httpClient.defaults.adapter = fakeTaskBackend([]);

    render(<PersonalTasksPage />);

    await waitFor(() =>
      expect(screen.getByText(/ainda não tem tarefas pessoais/)).toBeInTheDocument(),
    );
  });

  it("lista as tarefas existentes com status, prioridade e prazo", async () => {
    httpClient.defaults.adapter = fakeTaskBackend([
      makeTask({
        title: "Comprar mantimentos",
        status: "PENDING",
        priority: "HIGH",
        due_date: "2026-08-01",
      }),
    ]);

    render(<PersonalTasksPage />);

    await waitFor(() => expect(screen.getByText("Comprar mantimentos")).toBeInTheDocument());
    expect(screen.getByText("Pendente")).toBeInTheDocument();
    expect(screen.getByText("Alta")).toBeInTheDocument();
    expect(screen.getByText(/01\/08\/2026/)).toBeInTheDocument();
  });

  it("filtra tarefas de workspace, mostrando apenas as pessoais", async () => {
    httpClient.defaults.adapter = fakeTaskBackend([
      makeTask({ title: "Tarefa pessoal", workspace_id: null }),
      makeTask({ title: "Tarefa de workspace", workspace_id: "11111111-1111-1111-1111-111111111111" }),
    ]);

    render(<PersonalTasksPage />);

    await waitFor(() => expect(screen.getByText("Tarefa pessoal")).toBeInTheDocument());
    expect(screen.queryByText("Tarefa de workspace")).not.toBeInTheDocument();
  });

  it("cria uma nova tarefa pessoal", async () => {
    httpClient.defaults.adapter = fakeTaskBackend([]);

    render(<PersonalTasksPage />);

    await waitFor(() =>
      expect(screen.getByText(/ainda não tem tarefas pessoais/)).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: /Nova tarefa/ }));
    fireEvent.change(screen.getByLabelText("Título"), {
      target: { value: "Estudar para a prova" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Criar tarefa" }));

    await waitFor(() =>
      expect(screen.getByText("Estudar para a prova")).toBeInTheDocument(),
    );
    expect(screen.queryByLabelText("Título")).not.toBeInTheDocument();
  });

  it("marca uma tarefa como concluída pelo checkbox", async () => {
    httpClient.defaults.adapter = fakeTaskBackend([
      makeTask({ title: "Lavar o carro", status: "PENDING" }),
    ]);

    render(<PersonalTasksPage />);

    await waitFor(() => expect(screen.getByText("Lavar o carro")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("checkbox", { name: "Marcar como concluída" }));

    await waitFor(() => expect(screen.getByText("Concluída")).toBeInTheDocument());
  });

  it("edita uma tarefa existente", async () => {
    httpClient.defaults.adapter = fakeTaskBackend([
      makeTask({ title: "Título antigo", description: "Descrição antiga" }),
    ]);

    render(<PersonalTasksPage />);

    await waitFor(() => expect(screen.getByText("Título antigo")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Editar tarefa" }));

    const titleInput = await screen.findByLabelText("Título");
    expect(titleInput).toHaveValue("Título antigo");

    fireEvent.change(titleInput, { target: { value: "Título revisado" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(screen.getByText("Título revisado")).toBeInTheDocument());
  });
});
