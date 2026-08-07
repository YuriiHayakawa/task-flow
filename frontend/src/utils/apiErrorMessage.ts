import axios from "axios";

import type { ApiError } from "@/types/apiError";

/** Extrai o `code` de erro retornado pela API (`{ error: { code, message } }`),
 * quando o erro for um `AxiosError` com corpo nesse formato. */
export function getApiErrorCode(error: unknown): string | undefined {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as ApiError | undefined)?.error?.code;
  }
  return undefined;
}

/** Extrai a `message` de erro retornada pela API — usada quando a mensagem do
 * backend já é acionável o suficiente para mostrar diretamente ao usuário
 * (ex.: "Este membro é responsável por tarefas ativas..."), em vez de uma
 * mensagem genérica fixa no frontend. Cai no `fallback` para erros de rede/
 * formato inesperado, nunca deixando a UI sem mensagem nenhuma. */
export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const message = (error.response?.data as ApiError | undefined)?.error?.message;
    if (message) return message;
  }
  return fallback;
}
