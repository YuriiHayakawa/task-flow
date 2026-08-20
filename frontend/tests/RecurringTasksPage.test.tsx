import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { RecurringTasksPage } from "@/pages/RecurringTasksPage";
import httpClient from "@/services/httpClient";
import type { RecurringTask } from "@/types/recurringTask";

function makeRecurringTask(overrides: Partial<RecurringTask> = {}): RecurringTask {
  return {
    id: crypto.randomUUID(),
    title: "Beber água",
    recurrence_type: "DAILY",
    weekdays: [],
    month_day: null,
    is_due_today: true,
    completed_today: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function ok(data: unknown, config: InternalAxiosRequestConfig): AxiosResponse {
  return { data, status: 200, statusText: "OK", headers: {}, config } as AxiosResponse;
}

/** Simula o backend real o suficiente para GET refletir efeitos de
 * POST/PATCH/DELETE — mesmo padrão de `PersonalTasksPage.test.tsx`. */
function fakeBackend(initial: RecurringTask[] = []): AxiosAdapter {
  let items = [...initial];
  return (config) => {
    const method = config.method?.toLowerCase();
    const url = config.url ?? "";

    if (method === "get" && url === "/recurring-tasks") {
      return Promise.resolve(ok(items, config));
    }
    if (method === "post" && url === "/recurring-tasks") {
      const body = JSON.parse(config.data as string) as Partial<RecurringTask>;
      const created = makeRecurringTask({
        ...body,
        id: crypto.randomUUID(),
        is_due_today: true,
        completed_today: false,
      });
      items = [...items, created];
      return Promise.resolve(ok(created, config));
    }
    const completeMatch = method === "post" ? url.match(/^\/recurring-tasks\/(.+)\/completions$/) : null;
    if (completeMatch) {
      const id = completeMatch[1];
      items = items.map((item) => (item.id === id ? { ...item, completed_today: true } : item));
      return Promise.resolve(ok(items.find((item) => item.id === id), config));
    }
    const uncompleteMatch = method === "delete" ? url.match(/^\/recurring-tasks\/(.+)\/completions$/) : null;
    if (uncompleteMatch) {
      const id = uncompleteMatch[1];
      items = items.map((item) => (item.id === id ? { ...item, completed_today: false } : item));
      return Promise.resolve(ok(items.find((item) => item.id === id), config));
    }
    const patchMatch = method === "patch" ? url.match(/^\/recurring-tasks\/([^/]+)$/) : null;
    if (patchMatch) {
      const id = patchMatch[1];
      const body = JSON.parse(config.data as string) as Partial<RecurringTask>;
      items = items.map((item) => (item.id === id ? { ...item, ...body } : item));
      return Promise.resolve(ok(items.find((item) => item.id === id), config));
    }
    const deleteMatch = method === "delete" ? url.match(/^\/recurring-tasks\/([^/]+)$/) : null;
    if (deleteMatch) {
      const id = deleteMatch[1];
      items = items.filter((item) => item.id !== id);
      return Promise.resolve(ok(undefined, config));
    }
    return Promise.reject(new Error(`requisição inesperada: ${method} ${url}`));
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/tasks/recurring"]}>
      <Routes>
        <Route path="/tasks" element={<p>Quadro</p>} />
        <Route path="/tasks/recurring" element={<RecurringTasksPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RecurringTasksPage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("exibe o estado vazio quando não há tarefas fixas", async () => {
    httpClient.defaults.adapter = fakeBackend([]);

    renderPage();

    expect(await screen.findByText(/ainda não tem tarefas fixas/)).toBeInTheDocument();
  });

  it("cria uma tarefa fixa diária", async () => {
    httpClient.defaults.adapter = fakeBackend([]);

    renderPage();
    await screen.findByText(/ainda não tem tarefas fixas/);

    fireEvent.click(screen.getByRole("button", { name: /Nova tarefa fixa/ }));
    fireEvent.change(screen.getByLabelText("Título"), { target: { value: "Beber água" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar tarefa fixa" }));

    expect(await screen.findByText("Beber água")).toBeInTheDocument();
    expect(screen.getByText("Diária")).toBeInTheDocument();
  });

  it("criar semanal exige selecionar ao menos um dia (botão desabilitado até então)", async () => {
    httpClient.defaults.adapter = fakeBackend([]);

    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /Nova tarefa fixa/ }));
    fireEvent.change(screen.getByLabelText("Título"), { target: { value: "Revisar e-mails" } });
    fireEvent.click(screen.getByRole("button", { name: "Semanal" }));

    expect(screen.getByRole("button", { name: "Criar tarefa fixa" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Seg" }));
    expect(screen.getByRole("button", { name: "Criar tarefa fixa" })).not.toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Criar tarefa fixa" }));
    expect(await screen.findByText("Revisar e-mails")).toBeInTheDocument();
    expect(screen.getByText("Semanal")).toBeInTheDocument();
    expect(screen.getByText("Seg")).toBeInTheDocument();
  });

  it("criar mensal exige um dia do mês válido", async () => {
    httpClient.defaults.adapter = fakeBackend([]);

    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /Nova tarefa fixa/ }));
    fireEvent.change(screen.getByLabelText("Título"), { target: { value: "Pagar boleto" } });
    fireEvent.click(screen.getByRole("button", { name: "Mensal" }));

    expect(screen.getByRole("button", { name: "Criar tarefa fixa" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Dia do mês"), { target: { value: "10" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar tarefa fixa" }));

    expect(await screen.findByText("Pagar boleto")).toBeInTheDocument();
    expect(screen.getByText("Mensal")).toBeInTheDocument();
    expect(screen.getByText("Dia 10")).toBeInTheDocument();
  });

  it("alterna concluída/pendente pelo toggle quando é ocorrência de hoje", async () => {
    const task = makeRecurringTask({ is_due_today: true, completed_today: false });
    httpClient.defaults.adapter = fakeBackend([task]);

    renderPage();
    const toggle = await screen.findByRole("button", { name: "Marcar como concluída" });
    expect(toggle).not.toBeDisabled();

    fireEvent.click(toggle);

    expect(await screen.findByRole("button", { name: "Marcar como pendente" })).toBeInTheDocument();
  });

  it("toggle fica desabilitado quando hoje não é ocorrência da tarefa", async () => {
    const task = makeRecurringTask({
      recurrence_type: "WEEKLY",
      weekdays: [0, 2, 4],
      is_due_today: false,
      completed_today: false,
    });
    httpClient.defaults.adapter = fakeBackend([task]);

    renderPage();
    await screen.findByText("Beber água");
    expect(screen.getByText(/não é hoje/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Marcar como concluída" })).toBeDisabled();
  });

  it("edita o título de uma tarefa fixa", async () => {
    const task = makeRecurringTask({ title: "Título antigo" });
    httpClient.defaults.adapter = fakeBackend([task]);

    renderPage();
    await screen.findByText("Título antigo");

    fireEvent.click(screen.getByRole("button", { name: "Editar Título antigo" }));
    const titleInput = await screen.findByLabelText("Título");
    expect(titleInput).toHaveValue("Título antigo");

    fireEvent.change(titleInput, { target: { value: "Título novo" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(screen.getByText("Título novo")).toBeInTheDocument());
  });

  it("exclui uma tarefa fixa após confirmação", async () => {
    const task = makeRecurringTask({ title: "Vai sumir" });
    httpClient.defaults.adapter = fakeBackend([task]);

    renderPage();
    await screen.findByText("Vai sumir");

    fireEvent.click(screen.getByRole("button", { name: "Excluir Vai sumir" }));
    fireEvent.click(await screen.findByRole("button", { name: "Excluir" }));

    await waitFor(() => expect(screen.queryByText("Vai sumir")).not.toBeInTheDocument());
    expect(await screen.findByText(/ainda não tem tarefas fixas/)).toBeInTheDocument();
  });
});
