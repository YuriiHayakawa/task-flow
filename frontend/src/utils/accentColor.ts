export interface AccentColor {
  gradientClass: string;
  shadowClass: string;
  glowClass: string;
}

/** Paleta de acentos com gradiente + sombra + brilho já combinando (mesmo
 * par `from-{cor}-400 to-{cor}-700` usado nos badges de ícone do app) —
 * classes completas e literais (não interpoladas) para o scanner do
 * Tailwind conseguir gerá-las. */
const ACCENT_PALETTE: AccentColor[] = [
  { gradientClass: "from-blue-400 to-blue-700", shadowClass: "shadow-blue-900/20", glowClass: "bg-blue-500/20" },
  { gradientClass: "from-violet-400 to-violet-700", shadowClass: "shadow-violet-900/20", glowClass: "bg-violet-500/20" },
  { gradientClass: "from-emerald-400 to-emerald-700", shadowClass: "shadow-emerald-900/20", glowClass: "bg-emerald-500/20" },
  { gradientClass: "from-amber-400 to-amber-700", shadowClass: "shadow-amber-900/20", glowClass: "bg-amber-500/20" },
  { gradientClass: "from-rose-400 to-rose-700", shadowClass: "shadow-rose-900/20", glowClass: "bg-rose-500/20" },
  { gradientClass: "from-cyan-400 to-cyan-700", shadowClass: "shadow-cyan-900/20", glowClass: "bg-cyan-500/20" },
  { gradientClass: "from-indigo-400 to-indigo-700", shadowClass: "shadow-indigo-900/20", glowClass: "bg-indigo-500/20" },
  { gradientClass: "from-pink-400 to-pink-700", shadowClass: "shadow-pink-900/20", glowClass: "bg-pink-500/20" },
];

/** Cor determinística a partir de uma string estável (ex.: um id) — a
 * mesma entrada sempre resulta na mesma cor, sem precisar guardar nada a
 * mais no banco. Usado para dar identidade visual variada a grades de
 * cards (ex.: `WorkspacesPage`) sem inventar campo nenhum no modelo. */
export function pickAccentColor(seed: string): AccentColor {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return ACCENT_PALETTE[hash % ACCENT_PALETTE.length]!;
}
