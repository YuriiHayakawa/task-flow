import { AlertCircle, Mail, User } from "lucide-react";
import { useState, type SubmitEvent } from "react";
import { useNavigate } from "react-router-dom";

import { PasswordInput } from "@/components/forms/PasswordInput";
import { AuthHighlights } from "@/components/layout/AuthHighlights";
import { AuthTabs } from "@/components/layout/AuthTabs";
import { MobileBrandMark } from "@/components/layout/MobileBrandMark";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import * as authService from "@/services/authService";
import { getApiErrorCode } from "@/utils/apiErrorMessage";

function registerErrorMessage(code: string | undefined): string {
  if (code === "CONFLICT") {
    return "Este e-mail já está cadastrado.";
  }
  return "Não foi possível criar a conta. Verifique os dados e tente novamente.";
}

const fieldClassName =
  "h-11 rounded-xl focus-visible:border-blue-500 focus-visible:ring-blue-500/30";

export function RegisterPage() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await authService.register({ name, email, password });
      void navigate("/login", { state: { registered: true } });
    } catch (err) {
      setError(registerErrorMessage(getApiErrorCode(err)));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-7">
      <MobileBrandMark />
      <AuthTabs />

      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold tracking-tight">Crie sua conta</h1>
        <p className="text-sm text-muted-foreground">
          Cadastre-se para começar a organizar suas tarefas.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <Label htmlFor="name">Nome</Label>
          <div className="relative">
            <User className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="name"
              type="text"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              autoComplete="name"
              className={cn(fieldClassName, "pl-9")}
              placeholder="Seu nome"
            />
          </div>
        </div>
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
            autoComplete="new-password"
            className={fieldClassName}
            placeholder="••••••••"
          />
          <p className="text-xs text-muted-foreground">Mínimo de 8 caracteres.</p>
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
          {isSubmitting ? "Criando conta..." : "Criar conta"}
        </Button>
      </form>

      <AuthHighlights />
    </div>
  );
}
