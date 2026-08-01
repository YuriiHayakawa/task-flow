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
