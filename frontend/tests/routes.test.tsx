import { render, screen, waitFor } from "@testing-library/react";
import type { AxiosAdapter, AxiosResponse } from "axios";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AuthProvider } from "@/contexts/AuthContext";
import { AppRoutes } from "@/routes";
import httpClient, { getStoredToken, setStoredToken } from "@/services/httpClient";
import type { User } from "@/types/user";

function mockMeAdapter(user: User | null): AxiosAdapter {
  return (config) => {
    if (config.url?.includes("/users/me")) {
      if (user) {
        return Promise.resolve({
          data: user,
          status: 200,
          statusText: "OK",
          headers: {},
          config,
        } as AxiosResponse);
      }
      const error = Object.assign(new Error("Não autenticado"), {
        isAxiosError: true,
        config,
        response: { status: 401, data: {}, statusText: "", headers: {}, config },
      });
      return Promise.reject(error);
    }
    return Promise.reject(new Error(`requisição inesperada em ${config.url}`));
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

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("guardas de rota", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("redireciona um usuário não autenticado de uma rota protegida para /login", async () => {
    httpClient.defaults.adapter = mockMeAdapter(null);

    renderAt("/dashboard");

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Login" })).toBeInTheDocument(),
    );
  });

  it("redireciona um usuário autenticado de /login para /dashboard", async () => {
    setStoredToken("fake-token");
    httpClient.defaults.adapter = mockMeAdapter(makeUser());

    renderAt("/login");

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument(),
    );
  });

  it("redireciona um usuário comum de /admin para /dashboard", async () => {
    setStoredToken("fake-token");
    httpClient.defaults.adapter = mockMeAdapter(makeUser({ is_system_admin: false }));

    renderAt("/admin");

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument(),
    );
  });

  it("permite que um system admin acesse /admin", async () => {
    setStoredToken("fake-token");
    httpClient.defaults.adapter = mockMeAdapter(makeUser({ is_system_admin: true }));

    renderAt("/admin");

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Administração" })).toBeInTheDocument(),
    );
  });

  it("exibe o link de Administração na sidebar apenas para system admin", async () => {
    setStoredToken("fake-token");
    httpClient.defaults.adapter = mockMeAdapter(makeUser({ is_system_admin: true }));

    renderAt("/dashboard");

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: /Administração/ })).toBeInTheDocument();
  });

  it("não exibe o link de Administração na sidebar para um usuário comum", async () => {
    setStoredToken("fake-token");
    httpClient.defaults.adapter = mockMeAdapter(makeUser({ is_system_admin: false }));

    renderAt("/dashboard");

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument(),
    );
    expect(screen.queryByRole("link", { name: /Administração/ })).not.toBeInTheDocument();
  });

  it("token inválido/expirado limpa a sessão e redireciona para /login", async () => {
    setStoredToken("token-expirado");
    httpClient.defaults.adapter = mockMeAdapter(null);

    renderAt("/dashboard");

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Login" })).toBeInTheDocument(),
    );
    expect(getStoredToken()).toBeNull();
  });
});
