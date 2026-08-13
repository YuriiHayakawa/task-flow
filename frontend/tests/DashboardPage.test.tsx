import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AuthProvider } from "@/contexts/AuthContext";
import { DashboardPage } from "@/pages/DashboardPage";
import httpClient, { setStoredToken } from "@/services/httpClient";
import type { DashboardCounts } from "@/types/dashboard";
import type { User } from "@/types/user";

function ok(data: unknown, config: InternalAxiosRequestConfig): AxiosResponse {
  return { data, status: 200, statusText: "OK", headers: {}, config } as AxiosResponse;
}

function fail(status: number, config: InternalAxiosRequestConfig): Promise<never> {
  const error = Object.assign(new Error("erro simulado"), {
    isAxiosError: true,
    config,
    response: {
      data: { error: { code: "INTERNAL_ERROR", message: "erro simulado" } },
      status,
      statusText: "",
      headers: {},
      config,
    },
  });
  return Promise.reject(error);
}

function makeUser(): User {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    name: "Ana Exemplo",
    email: "ana@example.com",
    is_active: true,
    is_system_admin: false,
    created_at: "2026-01-01T00:00:00Z",
  };
}

function makeCounts(overrides: Partial<DashboardCounts> = {}): DashboardCounts {
  return {
    pending: 0,
    in_progress: 0,
    done: 0,
    overdue: 0,
    due_today: 0,
    ...overrides,
  };
}

/** `onDashboardRequest` recebe os params de cada chamada a `/dashboard` —
 * usado para inspecionar o escopo enviado quando o teste troca de aba. */
function dashboardAdapter(
  counts: DashboardCounts,
  onDashboardRequest?: (params: Record<string, unknown> | undefined) => void,
): AxiosAdapter {
  return (config) => {
    if (config.url === "/users/me") return Promise.resolve(ok(makeUser(), config));
    if (config.url === "/workspaces") {
      return Promise.resolve(ok({ items: [], page: 1, page_size: 20, total: 0 }, config));
    }
    if (config.url === "/dashboard") {
      onDashboardRequest?.(config.params as Record<string, unknown> | undefined);
      return Promise.resolve(ok({ counts }, config));
    }
    return Promise.reject(new Error(`requisição inesperada: ${config.url}`));
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    localStorage.clear();
    setStoredToken("fake-token");
  });

  it("estado vazio: sem tarefas, mostra convite para criar a primeira", async () => {
    httpClient.defaults.adapter = dashboardAdapter(makeCounts());

    renderPage();

    await waitFor(() => expect(screen.getByText("Nenhuma tarefa ainda.")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /Nova tarefa/ })).toBeInTheDocument();
  });

  it("saudação personalizada usa o primeiro nome do usuário", async () => {
    httpClient.defaults.adapter = dashboardAdapter(makeCounts());

    renderPage();

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /^(Bom dia|Boa tarde|Boa noite), Ana$/ })).toBeInTheDocument(),
    );
  });

  it("mostra o percentual de conclusão e a distribuição por status corretos", async () => {
    httpClient.defaults.adapter = dashboardAdapter(
      makeCounts({ pending: 3, in_progress: 1, done: 4 }),
    );

    renderPage();

    // 4 concluídas de 8 no total = 50% — aparece duas vezes de propósito
    // (centro do donut + linha "Concluída" da legenda mostram o mesmo cálculo).
    await waitFor(() => expect(screen.getAllByText("50%").length).toBeGreaterThanOrEqual(1));
    expect(screen.getByText("Pendente")).toBeInTheDocument();
    expect(screen.getAllByText("Em andamento").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Concluída")).toBeInTheDocument();
    // Cards de KPI (rótulo no plural, distinto da legenda do donut)
    expect(screen.getByText("Pendentes")).toBeInTheDocument();
    expect(screen.getByText("Concluídas")).toBeInTheDocument();
  });

  it("mostra tarefas atrasadas e vencendo hoje quando existem", async () => {
    httpClient.defaults.adapter = dashboardAdapter(
      makeCounts({ pending: 2, in_progress: 1, done: 1, overdue: 2, due_today: 1 }),
    );

    renderPage();

    await waitFor(() => expect(screen.getByText("2 tarefas atrasadas")).toBeInTheDocument());
    expect(screen.getByText("1 vencendo hoje")).toBeInTheDocument();
    expect(screen.queryByText("Tudo em dia")).not.toBeInTheDocument();
  });

  it("mostra 'Tudo em dia' quando não há atrasadas nem vencendo hoje", async () => {
    httpClient.defaults.adapter = dashboardAdapter(
      makeCounts({ pending: 2, in_progress: 1, done: 1 }),
    );

    renderPage();

    await waitFor(() => expect(screen.getByText("Tudo em dia")).toBeInTheDocument());
  });

  it("exibe mensagem de erro quando o resumo não pode ser carregado", async () => {
    httpClient.defaults.adapter = (config) => {
      if (config.url === "/users/me") return Promise.resolve(ok(makeUser(), config));
      if (config.url === "/workspaces") {
        return Promise.resolve(ok({ items: [], page: 1, page_size: 20, total: 0 }, config));
      }
      return fail(500, config);
    };

    renderPage();

    await waitFor(() =>
      expect(
        screen.getByText("Não foi possível carregar o resumo do dashboard."),
      ).toBeInTheDocument(),
    );
  });

  it("alternador de escopo: clicar em 'Pessoal' refaz a busca com personal_only", async () => {
    const requests: (Record<string, unknown> | undefined)[] = [];
    httpClient.defaults.adapter = dashboardAdapter(makeCounts({ pending: 1 }), (params) => {
      requests.push(params);
    });

    renderPage();

    await waitFor(() => expect(requests.length).toBeGreaterThan(0));
    expect(requests[0]).toEqual({});

    fireEvent.click(screen.getByRole("button", { name: "Pessoal" }));

    await waitFor(() => expect(requests.at(-1)).toEqual({ personal_only: true }));
  });
});
