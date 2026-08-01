import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type {
  AxiosAdapter,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import httpClient, { getStoredToken } from "@/services/httpClient";
import type { User } from "@/types/user";

function ok(data: unknown, config: InternalAxiosRequestConfig): Promise<AxiosResponse> {
  return Promise.resolve({
    data,
    status: 200,
    statusText: "OK",
    headers: {},
    config,
  } as AxiosResponse);
}

function fail(
  status: number,
  code: string,
  config: InternalAxiosRequestConfig,
): Promise<AxiosResponse> {
  const error = Object.assign(new Error("erro simulado"), {
    isAxiosError: true,
    config,
    response: {
      data: { error: { code, message: "erro simulado" } },
      status,
      statusText: "",
      headers: {},
      config,
    },
  });
  return Promise.reject(error);
}

function routedAdapter(
  routes: Record<string, (config: InternalAxiosRequestConfig) => Promise<AxiosResponse>>,
): AxiosAdapter {
  return (config) => {
    const url = config.url ?? "";
    const entry = Object.entries(routes).find(([path]) => url.includes(path));
    if (!entry) {
      return Promise.reject(new Error(`requisição inesperada em ${url}`));
    }
    return entry[1](config);
  };
}

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    name: "Ana Exemplo",
    email: "ana@example.com",
    is_active: true,
    is_system_admin: false,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function AuthStatus() {
  const { isAuthenticated, user } = useAuth();
  return (
    <p data-testid="auth-status">
      {isAuthenticated ? `logado:${user?.email}` : "deslogado"}
    </p>
  );
}

function renderAuthPages(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider>
        <AuthStatus />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renderiza os campos de e-mail e senha", () => {
    renderAuthPages("/login");

    expect(screen.getByLabelText("E-mail")).toBeInTheDocument();
    expect(screen.getByLabelText("Senha")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Entrar" })).toBeInTheDocument();
  });

  it("loga com sucesso e atualiza o estado de autenticação", async () => {
    httpClient.defaults.adapter = routedAdapter({
      "/auth/login": (config) =>
        ok({ access_token: "fake-token", token_type: "bearer", expires_in: 3600 }, config),
      "/users/me": (config) => ok(makeUser(), config),
    });

    renderAuthPages("/login");

    fireEvent.change(screen.getByLabelText("E-mail"), {
      target: { value: "ana@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "senhaSegura123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() =>
      expect(screen.getByTestId("auth-status")).toHaveTextContent("logado:ana@example.com"),
    );
    expect(getStoredToken()).toBe("fake-token");
  });

  it("exibe mensagem de erro para credenciais inválidas", async () => {
    httpClient.defaults.adapter = routedAdapter({
      "/auth/login": (config) => fail(401, "INVALID_CREDENTIALS", config),
    });

    renderAuthPages("/login");

    fireEvent.change(screen.getByLabelText("E-mail"), {
      target: { value: "ana@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "senhaErrada" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() =>
      expect(screen.getByText("E-mail ou senha incorretos.")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("auth-status")).toHaveTextContent("deslogado");
  });

  it("exibe mensagem de erro para conta desativada", async () => {
    httpClient.defaults.adapter = routedAdapter({
      "/auth/login": (config) => fail(403, "ACCOUNT_DISABLED", config),
    });

    renderAuthPages("/login");

    fireEvent.change(screen.getByLabelText("E-mail"), {
      target: { value: "desativado@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "senhaSegura123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() =>
      expect(screen.getByText("Esta conta está desativada.")).toBeInTheDocument(),
    );
  });

  it("exibe o banner de conta desativada quando redirecionado com ?reason=account_disabled", () => {
    renderAuthPages("/login?reason=account_disabled");

    expect(screen.getByText("Esta conta está desativada.")).toBeInTheDocument();
  });
});

describe("RegisterPage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renderiza os campos de nome, e-mail e senha", () => {
    renderAuthPages("/register");

    expect(screen.getByLabelText("Nome")).toBeInTheDocument();
    expect(screen.getByLabelText("E-mail")).toBeInTheDocument();
    expect(screen.getByLabelText("Senha")).toBeInTheDocument();
  });

  it("cria a conta com sucesso e redireciona para /login com mensagem de sucesso", async () => {
    httpClient.defaults.adapter = routedAdapter({
      "/auth/register": (config) => ok(makeUser(), config),
    });

    renderAuthPages("/register");

    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Ana Exemplo" } });
    fireEvent.change(screen.getByLabelText("E-mail"), {
      target: { value: "ana@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "senhaSegura123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Criar conta" }));

    await waitFor(() =>
      expect(
        screen.getByText("Conta criada com sucesso. Faça login para continuar."),
      ).toBeInTheDocument(),
    );
  });

  it("exibe mensagem de erro quando o e-mail já está cadastrado", async () => {
    httpClient.defaults.adapter = routedAdapter({
      "/auth/register": (config) => fail(409, "CONFLICT", config),
    });

    renderAuthPages("/register");

    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Ana Exemplo" } });
    fireEvent.change(screen.getByLabelText("E-mail"), {
      target: { value: "ana@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "senhaSegura123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Criar conta" }));

    await waitFor(() =>
      expect(screen.getByText("Este e-mail já está cadastrado.")).toBeInTheDocument(),
    );
  });
});
