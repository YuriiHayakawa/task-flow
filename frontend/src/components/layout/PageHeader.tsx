import type { LucideIcon } from "lucide-react";
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
 * opcional. Base neutra (mesma superfície `card` usada no resto do app,
 * não um bloco de cor à parte) com identidade visual entregue por
 * textura, não por tinta: a mesma malha de pontos do `BrandPanel` (tela
 * de login), esmaecida da direita para a esquerda para não competir com
 * o título, mais o friso de gradiente e o badge do ícone já aprovados. */
export function PageHeader({ icon: Icon, title, description, children }: PageHeaderProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-400 via-blue-500 to-blue-600" />

      {/* Malha de pontos — mesma textura do BrandPanel, esmaecida em
       * direção ao título via máscara de gradiente. */}
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(37,99,235,0.14)_1px,transparent_0)] bg-[size:24px_24px] dark:bg-[radial-gradient(circle_at_1px_1px,rgba(96,165,250,0.16)_1px,transparent_0)]"
        style={{
          maskImage: "linear-gradient(to left, black, transparent 60%)",
          WebkitMaskImage: "linear-gradient(to left, black, transparent 60%)",
        }}
      />
      <div className="pointer-events-none absolute -top-12 -right-12 size-44 rounded-full bg-blue-400/15 blur-3xl" />

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
