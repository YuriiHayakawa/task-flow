import axios, { type AxiosError } from "axios";

import type { ApiError } from "@/types/apiError";

const TOKEN_STORAGE_KEY = "taskflow_token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

const httpClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

httpClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

httpClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    const code = error.response?.data?.error?.code;
    // O próprio POST /auth/login pode retornar ACCOUNT_DISABLED (credenciais
    // corretas, conta desativada) — nesse caso não há sessão para encerrar;
    // quem trata essa mensagem específica é o formulário de login, não este
    // interceptor. O logout automático (research.md #1/#15) é só para uma
    // conta desativada DURANTE uma sessão já autenticada.
    const isLoginRequest = error.config?.url?.includes("/auth/login");

    if (code === "ACCOUNT_DISABLED" && !isLoginRequest) {
      clearStoredToken();
      window.location.href = "/login?reason=account_disabled";
    }

    return Promise.reject(error);
  },
);

export default httpClient;
