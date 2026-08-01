import httpClient from "@/services/httpClient";
import type { LoginRequest, TokenResponse, User, UserCreate } from "@/types/user";

export function register(payload: UserCreate): Promise<User> {
  return httpClient.post<User>("/auth/register", payload).then((response) => response.data);
}

export function login(payload: LoginRequest): Promise<TokenResponse> {
  return httpClient.post<TokenResponse>("/auth/login", payload).then((response) => response.data);
}
