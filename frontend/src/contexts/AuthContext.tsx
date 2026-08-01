import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import httpClient, {
  clearStoredToken,
  getStoredToken,
  setStoredToken,
} from "@/services/httpClient";
import type { TokenResponse, User } from "@/types/user";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isSystemAdmin: boolean;
  /** `true` enquanto a sessão armazenada (se houver) ainda está sendo
   * validada contra a API — evita redirecionar para /login precocemente
   * num recarregamento de página com um token válido. */
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = getStoredToken();
    if (!storedToken) {
      setIsLoading(false);
      return;
    }

    httpClient
      .get<User>("/users/me")
      .then((response) => {
        setToken(storedToken);
        setUser(response.data);
      })
      .catch(() => {
        // Token inválido/expirado, ou conta desativada — o interceptor de
        // ACCOUNT_DISABLED (httpClient.ts) já limpa o token nesse caso;
        // aqui cobrimos os demais motivos de falha (ex.: token expirado).
        clearStoredToken();
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokenResponse = await httpClient.post<TokenResponse>("/auth/login", {
      email,
      password,
    });
    setStoredToken(tokenResponse.data.access_token);

    const meResponse = await httpClient.get<User>("/users/me");
    setToken(tokenResponse.data.access_token);
    setUser(meResponse.data);
  }, []);

  const logout = useCallback(() => {
    clearStoredToken();
    setToken(null);
    setUser(null);
  }, []);

  const value: AuthContextValue = {
    user,
    token,
    isAuthenticated: user !== null,
    isSystemAdmin: user?.is_system_admin ?? false,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth deve ser usado dentro de um AuthProvider.");
  }
  return context;
}
