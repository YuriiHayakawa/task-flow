import { AlignLeft, Check, X, Building2 } from "lucide-react";
import { useState, type SubmitEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { Workspace } from "@/types/workspace";

export interface WorkspaceFormValues {
  name: string;
  description: string;
}

interface WorkspaceFormProps {
  /** Presente em modo de edição; ausente em modo de criação. */
  workspace?: Workspace;
  onSubmit: (values: WorkspaceFormValues) => Promise<void>;
  onCancel: () => void;
}

export function WorkspaceForm({ workspace, onSubmit, onCancel }: WorkspaceFormProps) {
  const [name, setName] = useState(workspace?.name ?? "");
  const [description, setDescription] = useState(workspace?.description ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({ name, description });
    } catch {
      setError("Não foi possível salvar o workspace. Tente novamente.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <Label htmlFor="workspace-name">Nome</Label>
        <div className="relative">
          <Building2 className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="workspace-name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="h-11 rounded-xl pl-9"
            placeholder="Ex.: Time de Produto"
          />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="workspace-description">Descrição</Label>
        <div className="relative">
          <AlignLeft className="pointer-events-none absolute top-3 left-3 size-4 text-muted-foreground" />
          <Textarea
            id="workspace-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="min-h-24 rounded-xl pl-9"
            placeholder="Para que serve este workspace? (opcional)"
          />
        </div>
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
          <X className="size-4" />
          Cancelar
        </Button>
        <Button
          type="submit"
          disabled={isSubmitting || name.trim() === ""}
          className="rounded-xl bg-blue-600 text-white hover:bg-blue-500"
        >
          <Check className="size-4" />
          {isSubmitting ? "Salvando..." : workspace ? "Salvar" : "Criar workspace"}
        </Button>
      </div>
    </form>
  );
}
