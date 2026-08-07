export interface User {
  id: string;
  name: string;
  email: string;
  is_active: boolean;
  is_system_admin: boolean;
  created_at: string;
}

export interface UserCreate {
  name: string;
  email: string;
  password: string;
}

export interface UserUpdate {
  name?: string;
  email?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserStatusUpdate {
  is_active: boolean;
}

/** Projeção mínima de `GET /users/lookup` (contracts/auth-and-users.md) —
 * usada só para resolver um e-mail em `id` no fluxo de "adicionar membro"
 * de um workspace; nunca inclui `is_active`/`is_system_admin`. */
export interface UserLookup {
  id: string;
  name: string;
  email: string;
}
