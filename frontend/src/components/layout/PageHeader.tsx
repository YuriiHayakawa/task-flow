import { Workflow, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface PageHeaderProps {
  icon: LucideIcon;
  title: string;
  description: string;
  /** Conteúdo extra específico da tela (ex.: barra de progresso). */
  children?: ReactNode;
}

/** Cabeçalho padrão de tela — usado por todas as páginas autenticadas,
 * cada uma com seu próprio ícone/título/descrição e conteúdo extra
 * opcional. Base neutra e minimalista, com as mesmas camadas sutis de
 * identidade visual usadas no restante da marca (glow, marca d'água,
 * friso de gradiente) — sem virar um banner chamativo. */
export function PageHeader({ icon: Icon, title, description, children }: PageHeaderProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-sky-200 bg-sky-100 p-6 shadow-sm dark:border-sky-900/40 dark:bg-sky-950/25">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-400 via-blue-500 to-blue-600" />
      <div className="pointer-events-none absolute -top-10 -right-10 size-40 rounded-full bg-sky-300/25 blur-2xl" />
      <Workflow
        className="pointer-events-none absolute -right-6 -bottom-10 size-36 rotate-12 text-sky-500/[0.08]"
        strokeWidth={1}
      />

      <div className="relative flex items-center gap-4">
        <div className="relative flex size-12 shrink-0 items-center justify-center">
          <div className="absolute inset-0 rounded-xl bg-blue-500/25 blur-md" />
          <div className="relative flex size-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-400 to-blue-700 shadow-lg shadow-blue-900/20">
            <Icon className="size-6 text-white" strokeWidth={2.25} />
          </div>
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
      {children && <div className="relative mt-5">{children}</div>}
    </div>
  );
}
