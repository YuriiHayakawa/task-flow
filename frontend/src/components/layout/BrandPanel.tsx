import { CheckCircle2, Users, Workflow } from "lucide-react";

interface KanbanCard {
  width: string;
  highlight?: string;
}

interface KanbanColumn {
  label: string;
  dot: string;
  cards: KanbanCard[];
}

const COLUMNS: KanbanColumn[] = [
  {
    label: "Pendente",
    dot: "bg-slate-500",
    cards: [{ width: "w-4/5", highlight: "kanban-highlight-1" }, { width: "w-3/5" }],
  },
  {
    label: "Em andamento",
    dot: "bg-blue-500",
    cards: [{ width: "w-3/4", highlight: "kanban-highlight-2" }],
  },
  {
    label: "Concluída",
    dot: "bg-emerald-400",
    cards: [{ width: "w-2/3", highlight: "kanban-highlight-3" }],
  },
];

/** Mini board kanban representando o conceito central do produto: uma
 * tarefa fluindo por seus estados (pendente → em andamento → concluída).
 * Identidade própria do TaskFlow, não um mockup literal de UI real — um
 * ponto luminoso percorre as colunas e cada uma acende em sequência,
 * dando a impressão de um quadro "vivo" e em atividade contínua. */
function KanbanGraphic() {
  return (
    <div className="relative w-full rounded-2xl border border-white/10 bg-white/[0.04] p-4 shadow-2xl shadow-black/40 backdrop-blur-sm">
      <div className="grid grid-cols-3 gap-3">
        {COLUMNS.map((column) => (
          <div key={column.label} className="flex flex-col gap-2">
            <span className="px-0.5 text-[9px] font-medium tracking-wide text-slate-500 uppercase">
              {column.label}
            </span>
            <div className="flex flex-col gap-1.5">
              {column.cards.map((card, index) => (
                <div
                  key={index}
                  className={`rounded-lg border border-white/5 bg-white/[0.03] p-2 transition-colors ${card.highlight ?? ""}`}
                >
                  <div className="mb-1.5 flex items-center gap-1.5">
                    <span className={`size-1.5 shrink-0 rounded-full ${column.dot}`} />
                    <div className={`h-1.5 rounded-full bg-white/15 ${card.width}`} />
                  </div>
                  <div className="h-1 w-1/2 rounded-full bg-white/5" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <span className="kanban-token pointer-events-none absolute top-[34px] size-2.5 -translate-x-1/2 rounded-full bg-blue-400 shadow-[0_0_14px_3px_rgba(96,165,250,0.55)]" />
    </div>
  );
}

/** Painel de identidade visual exibido ao lado das telas públicas
 * (login/cadastro) em telas largas — identidade própria (azul/preto),
 * independente do tema neutro usado no restante do app autenticado. */
export function BrandPanel() {
  return (
    <div className="relative hidden overflow-hidden bg-[#05070f] lg:flex lg:w-[40%] lg:flex-col lg:justify-between">
      <div className="blob-drift-a pointer-events-none absolute -top-40 -left-32 size-96 rounded-full bg-blue-600/30 blur-[100px]" />
      <div className="blob-drift-b pointer-events-none absolute -right-24 -bottom-40 size-[28rem] rounded-full bg-blue-500/20 blur-[110px]" />
      <div className="blob-drift-c pointer-events-none absolute top-1/3 left-1/2 size-72 rounded-full bg-indigo-500/10 blur-[90px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] bg-[size:36px_36px]" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-black/20" />
      <div className="shine-sweep pointer-events-none absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />

      {/* Marca d'água gigante do ícone da marca — textura de fundo discreta */}
      <Workflow
        className="pointer-events-none absolute -right-16 -bottom-20 size-80 rotate-12 text-blue-500/[0.06]"
        strokeWidth={1}
      />

      {/* Pontos de destaque espalhados nos espaços vazios, preenchendo o
          painel sem competir com o board kanban (foco principal) */}
      <span className="absolute top-48 left-44 size-1 rounded-full bg-blue-400/40" />
      <span className="absolute top-72 right-28 size-1.5 rounded-full bg-blue-300/30" />
      <span className="absolute bottom-64 left-24 size-1 rounded-full bg-white/20" />
      <span className="absolute right-20 bottom-48 size-1 rounded-full bg-blue-400/30" />

      <div className="relative z-10 flex items-center gap-3 p-10">
        <div className="relative flex size-14 items-center justify-center">
          <div className="absolute inset-0 rounded-2xl bg-blue-500/40 blur-lg" />
          <div className="orbit-ring absolute -inset-2.5 rounded-full border border-dashed border-blue-400/30" />
          <div className="relative flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-400 to-blue-700 shadow-lg shadow-blue-900/50">
            <Workflow className="size-7 text-white" strokeWidth={2.25} />
          </div>
        </div>
        <span className="text-3xl font-bold tracking-tight text-white">TaskFlow</span>
      </div>

      <div className="animate-in fade-in slide-in-from-bottom-2 relative z-10 flex flex-col gap-9 p-10 duration-700">
        <div className="relative w-full max-w-sm">
          <KanbanGraphic />
          <div
            className="float-bob absolute -top-4 -right-3 flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.06] px-3 py-2 text-xs font-medium text-slate-200 shadow-lg shadow-black/30 backdrop-blur-sm [--float-rotate:-3deg]"
            style={{ animationDelay: "0.3s" }}
          >
            <CheckCircle2 className="size-3.5 text-emerald-400" />
            Tarefa concluída
          </div>
          <div
            className="float-bob absolute -bottom-4 -left-3 flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.06] px-3 py-2 text-xs font-medium text-slate-200 shadow-lg shadow-black/30 backdrop-blur-sm [--float-rotate:2deg]"
            style={{ animationDelay: "1.6s" }}
          >
            <Users className="size-3.5 text-blue-400" />
            Equipe conectada
          </div>
        </div>

        <div className="flex items-start gap-4">
          <div className="mt-2 h-16 w-1 shrink-0 rounded-full bg-gradient-to-b from-blue-400 to-transparent" />
          <div className="relative">
            <div className="absolute top-9 -left-2 h-16 w-64 rounded-full bg-blue-500/20 blur-3xl" />
            <h2 className="relative text-5xl leading-[1.08] font-bold tracking-tight text-white">
              Suas tarefas,
              <br />
              <span className="bg-gradient-to-r from-blue-300 via-blue-400 to-sky-200 bg-clip-text text-transparent">
                em movimento.
              </span>
            </h2>
          </div>
        </div>
      </div>

      <div className="relative z-10 p-10 text-xs text-slate-600">© {new Date().getFullYear()} TaskFlow</div>
    </div>
  );
}
