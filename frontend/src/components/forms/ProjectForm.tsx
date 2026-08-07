import { AlignLeft, Check, FolderKanban, X } from "lucide-react";
import { useState, type SubmitEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { Project } from "@/types/project";

export interface ProjectFormValues {
  name: string;
  description: string;
}

interface ProjectFormProps {
  /** Presente em modo de edição; ausente em modo de criação. */
  project?: Project;
  onSubmit: (values: ProjectFormValues) => Promise<void>;
  onCancel: () => void;
}

export function ProjectForm({ project, onSubmit, onCancel }: ProjectFormProps) {
  const [name, setName] = useState(project?.name ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({ name, description });
    } catch {
      setError("Não foi possível salvar o projeto. Tente novamente.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <Label htmlFor="project-name">Nome</Label>
        <div className="relative">
          <FolderKanban className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="project-name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="h-11 rounded-xl pl-9"
            placeholder="Ex.: Redesign do site"
          />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="project-description">Descrição</Label>
        <div className="relative">
          <AlignLeft className="pointer-events-none absolute top-3 left-3 size-4 text-muted-foreground" />
          <Textarea
            id="project-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="min-h-24 rounded-xl pl-9"
            placeholder="Do que se trata este projeto? (opcional)"
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
          {isSubmitting ? "Salvando..." : project ? "Salvar" : "Criar projeto"}
        </Button>
      </div>
    </form>
  );
}
