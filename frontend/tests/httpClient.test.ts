import type { AxiosAdapter, AxiosResponse } from "axios";
import { beforeEach, describe, expect, it } from "vitest";

import httpClient, {
  clearStoredToken,
  getStoredToken,
  setStoredToken,
} from "@/services/httpClient";

function successAdapter(data: unknown = {}): AxiosAdapter {
  return (config) =>
    Promise.resolve({
      data,
      status: 200,
      statusText: "OK",
      headers: {},
      config,
    } as AxiosResponse);
}

function errorAdapter(status: number, code: string): AxiosAdapter {
  return (config) => {
    const error = Object.assign(new Error("Request failed"), {
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
  };
}

describe("httpClient", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("attaches the Authorization header when a token is stored", async () => {
    setStoredToken("fake-token");
    let capturedAuthHeader: unknown;
    httpClient.defaults.adapter = ((config) => {
      capturedAuthHeader = config.headers.Authorization;
      return successAdapter()(config);
    }) as AxiosAdapter;

    await httpClient.get("/dashboard");

    expect(capturedAuthHeader).toBe("Bearer fake-token");
  });

  it("does not attach the Authorization header when no token is stored", async () => {
    let capturedAuthHeader: unknown = "not-checked";
    httpClient.defaults.adapter = ((config) => {
      capturedAuthHeader = config.headers.Authorization;
      return successAdapter()(config);
    }) as AxiosAdapter;

    await httpClient.get("/dashboard");

    expect(capturedAuthHeader).toBeUndefined();
  });

  it("clears the stored token on ACCOUNT_DISABLED from an authenticated request", async () => {
    setStoredToken("fake-token");
    httpClient.defaults.adapter = errorAdapter(403, "ACCOUNT_DISABLED");

    await expect(httpClient.get("/tasks")).rejects.toBeTruthy();

    expect(getStoredToken()).toBeNull();
  });

  it("does not clear the token on ACCOUNT_DISABLED from the login endpoint itself", async () => {
    // Sem sessão para encerrar — quem trata essa mensagem é o formulário de
    // login (research.md #1/#15): "conta desativada" no login é distinto do
    // logout automático de uma sessão já autenticada.
    httpClient.defaults.adapter = errorAdapter(403, "ACCOUNT_DISABLED");

    await expect(httpClient.post("/auth/login", {})).rejects.toBeTruthy();
  });

  it("passes through other errors unchanged", async () => {
    setStoredToken("fake-token");
    httpClient.defaults.adapter = errorAdapter(422, "VALIDATION_ERROR");

    await expect(httpClient.post("/tasks", {})).rejects.toBeTruthy();

    // token permanece — VALIDATION_ERROR não é motivo de logout:
    expect(getStoredToken()).toBe("fake-token");
  });
});

describe("token storage helpers", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("setStoredToken/getStoredToken round-trip", () => {
    setStoredToken("abc123");
    expect(getStoredToken()).toBe("abc123");
  });

  it("clearStoredToken removes the token", () => {
    setStoredToken("abc123");
    clearStoredToken();
    expect(getStoredToken()).toBeNull();
  });

  it("getStoredToken returns null when nothing is stored", () => {
    expect(getStoredToken()).toBeNull();
  });
});
