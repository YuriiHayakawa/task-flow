import { render, screen, waitFor } from "@testing-library/react";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { beforeEach, describe, expect, it } from "vitest";

import { DashboardPage } from "@/pages/DashboardPage";
import httpClient from "@/services/httpClient";
import type { DashboardCounts } from "@/types/dashboard";

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

function dashboardAdapter(counts: DashboardCounts): AxiosAdapter {
  return (config) => {
    if (config.url === "/dashboard") {
      return Promise.resolve(ok({ counts }, config));
    }
    return Promise.reject(new Error(`requisição inesperada: ${config.url}`));
  };
}

describe("DashboardPage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("exibe todos os contadores zerados quando o usuário não tem tarefas", async () => {
    httpClient.defaults.adapter = dashboardAdapter(makeCounts());

    render(<DashboardPage />);

    await waitFor(() => expect(screen.getByText("Pendentes")).toBeInTheDocument());
    const zeros = screen.getAllByText("0");
    expect(zeros).toHaveLength(5);
  });

  it("exibe as contagens corretas quando há tarefas em diferentes status e prazos", async () => {
    httpClient.defaults.adapter = dashboardAdapter(
      makeCounts({ pending: 3, in_progress: 1, done: 1, overdue: 1, due_today: 1 }),
    );

    render(<DashboardPage />);

    await waitFor(() => expect(screen.getByText("Pendentes")).toBeInTheDocument());

    const pendingCard = screen.getByText("Pendentes").closest("div");
    expect(pendingCard).toHaveTextContent("3");

    const overdueCard = screen.getByText("Atrasadas").closest("div");
    expect(overdueCard).toHaveTextContent("1");

    const dueTodayCard = screen.getByText("Vencendo hoje").closest("div");
    expect(dueTodayCard).toHaveTextContent("1");
  });

  it("exibe mensagem de erro quando o resumo não pode ser carregado", async () => {
    httpClient.defaults.adapter = (config) => fail(500, config);

    render(<DashboardPage />);

    await waitFor(() =>
      expect(
        screen.getByText("Não foi possível carregar o resumo do dashboard."),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByText("Pendentes")).not.toBeInTheDocument();
  });
});
