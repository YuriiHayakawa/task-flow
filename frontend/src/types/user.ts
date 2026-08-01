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
