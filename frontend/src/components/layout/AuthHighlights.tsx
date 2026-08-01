import { Fragment } from "react";
import { CalendarClock, ListChecks, Users } from "lucide-react";

const HIGHLIGHTS = [
  { icon: ListChecks, label: "Tarefas & projetos" },
  { icon: Users, label: "Workspaces em equipe" },
  { icon: CalendarClock, label: "Prazos & prioridades" },
] as const;

/** Rodapé minimalista abaixo do botão de submit, nas telas de login e
 * cadastro — reforça pilares reais do produto (todos correspondentes a
 * funcionalidades existentes), sem inventar recursos que não existem. */
export function AuthHighlights() {
  return (
    <div className="flex items-center justify-center gap-4 text-xs text-muted-foreground">
      {HIGHLIGHTS.map((item, index) => (
        <Fragment key={item.label}>
          {index > 0 && <span aria-hidden="true" className="h-3 w-px bg-border" />}
          <span className="flex items-center gap-1.5">
            <item.icon className="size-3.5" />
            {item.label}
          </span>
        </Fragment>
      ))}
    </div>
  );
}
