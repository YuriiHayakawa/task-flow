import { Mail, UserPlus } from "lucide-react";
import { useState, type SubmitEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getApiErrorMessage } from "@/utils/apiErrorMessage";

interface AddMemberByEmailFormProps {
  onAdd: (email: string) => Promise<void>;
  onCancel: () => void;
  /** Texto de apoio abaixo do campo — cada tela usa (workspace vs.
   * participante de tarefa) explica algo diferente sobre o que acontece
   * ao adicionar, então fica a cargo de quem usa o formulário. */
  helperText?: string;
}

/** Formulário de um único campo (e-mail) — resolve o e-mail em `user_id`
 * via `userService.lookupByEmail` (feito por quem chama `onAdd`, não aqui)
 * antes de adicionar. Reaproveitado por `WorkspaceMembersPage` (adicionar
 * membro do workspace) e `TaskDetailPage` (adicionar participante da
 * tarefa) — mesmo fluxo de duas etapas nos dois casos. */
export function AddMemberByEmailForm({ onAdd, onCancel, helperText }: AddMemberByEmailFormProps) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onAdd(email);
    } catch (err) {
      setError(getApiErrorMessage(err, "Não foi possível adicionar esta pessoa."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <Label htmlFor="member-email">E-mail</Label>
        <div className="relative">
          <Mail className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="member-email"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="h-11 rounded-xl pl-9"
            placeholder="pessoa@empresa.com"
          />
        </div>
        {helperText && <p className="text-xs text-muted-foreground">{helperText}</p>}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="mt-2 flex justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={isSubmitting}
          className="rounded-xl"
        >
          Cancelar
        </Button>
        <Button
          type="submit"
          disabled={isSubmitting || email.trim() === ""}
          className="rounded-xl bg-blue-600 text-white hover:bg-blue-500"
        >
          <UserPlus className="size-4" />
          {isSubmitting ? "Adicionando..." : "Adicionar"}
        </Button>
      </div>
    </form>
  );
}
