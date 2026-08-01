import { AlertCircle, CheckCircle2, Mail } from "lucide-react";
import { useState, type SubmitEvent } from "react";
import { useLocation, useSearchParams } from "react-router-dom";

import { PasswordInput } from "@/components/forms/PasswordInput";
import { AuthHighlights } from "@/components/layout/AuthHighlights";
import { AuthTabs } from "@/components/layout/AuthTabs";
import { MobileBrandMark } from "@/components/layout/MobileBrandMark";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";
import { getApiErrorCode } from "@/utils/apiErrorMessage";

interface LocationState {
  registered?: boolean;
}

function loginErrorMessage(code: string | undefined): string {
  if (code === "ACCOUNT_DISABLED") {
    return "Esta conta está desativada.";
  }
  if (code === "INVALID_CREDENTIALS") {
    return "E-mail ou senha incorretos.";
  }
  return "Não foi possível fazer login. Tente novamente.";
}

const fieldClassName =
  "h-11 rounded-xl focus-visible:border-blue-500 focus-visible:ring-blue-500/30";

export function LoginPage() {
  const { login } = useAuth();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const registered = (location.state as LocationState | null)?.registered ?? false;
  const accountDisabled = searchParams.get("reason") === "account_disabled";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(loginErrorMessage(getApiErrorCode(err)));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-7">
      <MobileBrandMark />
      <AuthTabs />

      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold tracking-tight">Bem-vindo de volta</h1>
        <p className="text-sm text-muted-foreground">
          Entre com sua conta para acessar suas tarefas.
        </p>
      </div>

      {registered && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3.5 py-2.5 text-sm text-emerald-700 dark:text-emerald-400">
          <CheckCircle2 className="size-4 shrink-0" />
          Conta criada com sucesso. Faça login para continuar.
        </div>
      )}
      {accountDisabled && (
        <div className="flex items-center gap-2 rounded-xl border border-destructive/20 bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive">
          <AlertCircle className="size-4 shrink-0" />
          Esta conta está desativada.
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <Label htmlFor="email">E-mail</Label>
          <div className="relative">
            <Mail className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="email"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              className={cn(fieldClassName, "pl-9")}
              placeholder="seu@email.com"
            />
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="password">Senha</Label>
          <PasswordInput
            id="password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            className={fieldClassName}
            placeholder="••••••••"
          />
        </div>
        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-destructive/20 bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive">
            <AlertCircle className="size-4 shrink-0" />
            {error}
          </div>
        )}
        <Button
          type="submit"
          disabled={isSubmitting}
          className="h-12 rounded-xl bg-blue-600 text-sm font-bold tracking-wide text-white uppercase shadow-lg shadow-blue-600/25 hover:bg-blue-500"
        >
          {isSubmitting ? "Entrando..." : "Entrar"}
        </Button>
      </form>

      <AuthHighlights />
    </div>
  );
}
