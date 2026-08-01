import { Link, useLocation } from "react-router-dom";

const TABS = [
  { to: "/login", label: "Entrar" },
  { to: "/register", label: "Criar conta" },
] as const;

/** Alterna visualmente entre Login e Cadastro como abas — cada aba navega
 * para a rota correspondente (/login ou /register), mantendo-as como
 * páginas independentes (guards, testes e o redirect de conta desativada
 * continuam funcionando normalmente). */
export function AuthTabs() {
  const location = useLocation();

  return (
    <div className="flex border-b border-border">
      {TABS.map((tab) => {
        const isActive = location.pathname === tab.to;
        return (
          <Link
            key={tab.to}
            to={tab.to}
            className={`relative flex-1 pb-3 text-center text-sm font-semibold transition-colors ${
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
