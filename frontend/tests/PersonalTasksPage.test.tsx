import { fireEvent, render, screen, within } from "@testing-library/react";
import type {
  AxiosAdapter,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import { MemoryRouter, Route, Routes } from "react-router-dom";
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

/** Objeto mínimo compatível com a API `DataTransfer` usada pelo drag-and-drop
 * nativo — jsdom não implementa `DataTransfer`, então simulamos só os dois
 * métodos que o componente realmente usa (`setData`/`getData`). */
function makeDataTransfer() {
  const store = new Map<string, string>();
  return {
    setData: (format: string, data: string) => store.set(format, data),
    getData: (format: string) => store.get(format) ?? "",
    effectAllowed: "",
  };
}

function getColumn(label: string): HTMLElement {
  return screen.getByLabelText(`Coluna ${label}`);
}

/** `/tasks/:taskId` é um stub (só confirma que a navegação aconteceu) — a
 * própria `TaskDetailPage` tem sua suíte de testes dedicada. */
function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/tasks"]}>
      <Routes>
        <Route path="/tasks" element={<PersonalTasksPage />} />
        <Route path="/tasks/:taskId" element={<p>Detalhes da tarefa</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PersonalTasksPage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("exibe o estado vazio quando não há tarefas pessoais", async () => {
    httpClient.defaults.adapter = fakeTaskBackend([]);

    renderPage();

    expect(
      await screen.findByText(/ainda não tem tarefas pessoais/),
    ).toBeInTheDocument();
  });

  it("distribui as tarefas nas colunas corretas com prioridade e prazo", async () => {
    httpClient.defaults.adapter = fakeTaskBackend([
      makeTask({
        title: "Comprar mantimentos",
        status: "PENDING",
        priority: "HIGH",
        due_date: "2026-08-01",
      }),
      makeTask({ title: "Revisar relatório", status: "IN_PROGRESS" }),
      makeTask({ title: "Tarefa finalizada", status: "DONE" }),
    ]);

    renderPage();

    await screen.findByText("Comprar mantimentos");

    expect(within(getColumn("Pendente")).getByText("Comprar mantimentos")).toBeInTheDocument();
    expect(within(getColumn("Em andamento")).getByText("Revisar relatório")).toBeInTheDocument();
    expect(within(getColumn("Concluída")).getByText("Tarefa finalizada")).toBeInTheDocument();

    expect(within(getColumn("Pendente")).getByText("Alta")).toBeInTheDocument();
    expect(within(getColumn("Pendente")).getByText(/01\/08\/2026/)).toBeInTheDocument();
  });

  it("filtra tarefas de workspace, mostrando apenas as pessoais", async () => {
    httpClient.defaults.adapter = fakeTaskBackend([
      makeTask({ title: "Tarefa pessoal", workspace_id: null }),
      makeTask({ title: "Tarefa de workspace", workspace_id: "11111111-1111-1111-1111-111111111111" }),
    ]);

    renderPage();

    await screen.findByText("Tarefa pessoal");
    expect(screen.queryByText("Tarefa de workspace")).not.toBeInTheDocument();
  });

  it("cria uma nova tarefa pessoal (entra na coluna Pendente)", async () => {
    httpClient.defaults.adapter = fakeTaskBackend([]);

    renderPage();

    await screen.findByText(/ainda não tem tarefas pessoais/);

    fireEvent.click(screen.getByRole("button", { name: /Nova tarefa/ }));
    fireEvent.change(screen.getByLabelText("Título"), {
      target: { value: "Estudar para a prova" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Criar tarefa" }));

    await screen.findByText("Estudar para a prova");
    expect(
      within(getColumn("Pendente")).getByText("Estudar para a prova"),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Título")).not.toBeInTheDocument();
  });

  it("marca uma tarefa como concluída pelo checkbox (move para Concluída)", async () => {
    httpClient.defaults.adapter = fakeTaskBackend([
      makeTask({ title: "Lavar o carro", status: "PENDING" }),
    ]);

    renderPage();

    await screen.findByText("Lavar o carro");

    fireEvent.click(screen.getByRole("checkbox", { name: "Marcar como concluída" }));

    await within(getColumn("Concluída")).findByText("Lavar o carro");
    expect(within(getColumn("Pendente")).queryByText("Lavar o carro")).not.toBeInTheDocument();
  });

  it("clicar no cartão abre a página de detalhes da tarefa (edição acontece lá)", async () => {
    const task = makeTask({ title: "Título antigo" });
    httpClient.defaults.adapter = fakeTaskBackend([task]);

    renderPage();

    await screen.findByText("Título antigo");
    fireEvent.click(screen.getByText("Título antigo"));

    expect(await screen.findByText("Detalhes da tarefa")).toBeInTheDocument();
  });

  it("clicar no checkbox alterna concluída sem navegar para os detalhes", async () => {
    httpClient.defaults.adapter = fakeTaskBackend([
      makeTask({ title: "Lavar o carro", status: "PENDING" }),
    ]);

    renderPage();

    await screen.findByText("Lavar o carro");
    fireEvent.click(screen.getByRole("checkbox", { name: "Marcar como concluída" }));

    await within(getColumn("Concluída")).findByText("Lavar o carro");
    expect(screen.queryByText("Detalhes da tarefa")).not.toBeInTheDocument();
  });

  it("move uma tarefa entre colunas ao arrastar e soltar", async () => {
    httpClient.defaults.adapter = fakeTaskBackend([
      makeTask({ title: "Preparar apresentação", status: "PENDING" }),
    ]);

    renderPage();

    await screen.findByText("Preparar apresentação");

    const card = screen.getByText("Preparar apresentação").closest("[draggable]");
    expect(card).not.toBeNull();

    const dataTransfer = makeDataTransfer();
    const targetColumn = getColumn("Em andamento");

    fireEvent.dragStart(card as HTMLElement, { dataTransfer });
    fireEvent.dragOver(targetColumn, { dataTransfer });
    fireEvent.drop(targetColumn, { dataTransfer });

    await within(getColumn("Em andamento")).findByText("Preparar apresentação");
    expect(
      within(getColumn("Pendente")).queryByText("Preparar apresentação"),
    ).not.toBeInTheDocument();
  });
});
