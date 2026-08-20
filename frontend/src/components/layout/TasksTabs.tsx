import { Link, useLocation } from "react-router-dom";

const TABS = [
  { to: "/tasks", label: "Quadro" },
  { to: "/tasks/recurring", label: "Tarefas Fixas" },
] as const;

/** Alterna visualmente entre o quadro kanban e as Tarefas Fixas como abas —
 * mesmo padrão visual e mecanismo (rotas reais, não `useState` de aba
 * ativa) de `AuthTabs.tsx` (research.md #5, 002-tarefas-fixas). Não
 * reaproveita `AuthTabs` diretamente porque ele está fixado nas rotas de
 * autenticação, sem generalização de props. */
export function TasksTabs() {
  const location = useLocation();

  return (
    <div className="flex border-b border-border">
      {TABS.map((tab) => {
        const isActive = location.pathname === tab.to;
        return (
          <Link
            key={tab.to}
            to={tab.to}
            className={`relative px-4 pb-3 text-sm font-semibold transition-colors ${
              isActive ? "text-blue-600" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
            {isActive && (
              <span className="absolute right-0 -bottom-px left-0 h-0.5 rounded-full bg-blue-600" />
            )}
          </Link>
        );
      })}
    </div>
  );
}
