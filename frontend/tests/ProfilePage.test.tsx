import { fireEvent, render, screen } from "@testing-library/react";
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AuthProvider } from "@/contexts/AuthContext";
import { ProfilePage } from "@/pages/ProfilePage";
import httpClient, { setStoredToken } from "@/services/httpClient";
import type { User } from "@/types/user";

const CURRENT_USER_ID = "11111111-1111-1111-1111-111111111111";

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

function ok(data: unknown, config: InternalAxiosRequestConfig): AxiosResponse {
  return { data, status: 200, statusText: "OK", headers: {}, config } as AxiosResponse;
}

/** 001-taskflow-mvp/US7 — perfil do usuário. `user` começa fixo em
 * `makeUser()`; um PATCH bem-sucedido atualiza esse estado em memória, então
 * um GET seguinte (ex.: o remount implícito de `AuthProvider`) já reflete a
 * mudança — mesmo padrão dos demais fakes deste projeto. */
function fakeAdapter(): AxiosAdapter {
  let user = makeUser();

  return (config) => {
    const method = config.method?.toLowerCase();
    const url = config.url ?? "";

    if (method === "get" && url === "/users/me") {
      return Promise.resolve(ok(user, config));
    }
    if (method === "patch" && url === "/users/me") {
      const body = JSON.parse(config.data as string) as { name?: string; email?: string };
      if (body.email === "ocupado@example.com") {
        return Promise.reject({
          isAxiosError: true,
          response: {
            status: 409,
            data: { error: { code: "CONFLICT", message: "Este e-mail já está em uso." } },
          },
        });
      }
      user = { ...user, ...body };
      return Promise.resolve(ok(user, config));
    }
    return Promise.reject(new Error(`requisição inesperada: ${method} ${url}`));
  };
}

function renderPage() {
  setStoredToken("fake-token");
  httpClient.defaults.adapter = fakeAdapter();

  return render(
    <MemoryRouter initialEntries={["/profile"]}>
      <AuthProvider>
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("ProfilePage — 001-taskflow-mvp/US7: perfil do usuário", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("exibe nome, e-mail e status da conta atuais, com os campos travados", async () => {
    renderPage();

    const nameInput = await screen.findByDisplayValue("Usuário Atual");
    expect(nameInput).toBeDisabled();
    expect(screen.getByDisplayValue("atual@example.com")).toBeDisabled();
    expect(screen.getByText("Conta ativa")).toBeInTheDocument();
    // Sem clicar em "Editar", não há como salvar (nem o campo permite digitar).
    expect(screen.queryByRole("button", { name: "Salvar alterações" })).not.toBeInTheDocument();
  });

  it("libera os campos só depois de clicar em Editar perfil, e atualiza o nome com sucesso", async () => {
    renderPage();

    await screen.findByDisplayValue("Usuário Atual");
    fireEvent.click(screen.getByRole("button", { name: "Editar" }));

    const nameInput = screen.getByDisplayValue("Usuário Atual");
    expect(nameInput).toBeEnabled();
    fireEvent.change(nameInput, { target: { value: "Novo Nome" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(await screen.findByText("Perfil atualizado com sucesso.")).toBeInTheDocument();
    // Depois de salvar, volta ao modo travado (campo some, botão de editar reaparece).
    expect(screen.getByDisplayValue("Novo Nome")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Editar" })).toBeInTheDocument();
  });

  it("cancelar a edição reverte o que foi digitado e trava os campos de novo", async () => {
    renderPage();

    await screen.findByDisplayValue("Usuário Atual");
    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    fireEvent.change(screen.getByDisplayValue("Usuário Atual"), { target: { value: "Rascunho" } });
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(screen.getByDisplayValue("Usuário Atual")).toBeDisabled();
    expect(screen.queryByDisplayValue("Rascunho")).not.toBeInTheDocument();
  });

  it("e-mail já usado por outra conta é rejeitado com a mensagem do backend", async () => {
    renderPage();

    await screen.findByDisplayValue("Usuário Atual");
    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    fireEvent.change(screen.getByDisplayValue("atual@example.com"), {
      target: { value: "ocupado@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(await screen.findByText("Este e-mail já está em uso.")).toBeInTheDocument();
    // Continua em edição (não some o botão Cancelar) — nada foi confirmado como sucesso.
    expect(screen.getByRole("button", { name: "Cancelar" })).toBeInTheDocument();
    expect(screen.queryByText("Perfil atualizado com sucesso.")).not.toBeInTheDocument();
  });

  it("botão de salvar fica desabilitado em edição sem nenhuma alteração", async () => {
    renderPage();

    await screen.findByDisplayValue("Usuário Atual");
    fireEvent.click(screen.getByRole("button", { name: "Editar" }));

    expect(screen.getByRole("button", { name: "Salvar alterações" })).toBeDisabled();
  });
});
