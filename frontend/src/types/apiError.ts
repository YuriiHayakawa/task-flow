export type ApiErrorDetail = Record<string, unknown>;

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: ApiErrorDetail[];
  };
}
