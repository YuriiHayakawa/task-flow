import { Crown, ShieldCheck, User, type LucideIcon } from "lucide-react";

import type { WorkspaceRole } from "@/types/workspace";

/** Rótulo, ícone e cor de cada role de workspace — reutilizado em
 * `WorkspacesPage`, `WorkspaceDetailPage` e `WorkspaceMembersPage` para que
 * a mesma role sempre pareça a mesma coisa em qualquer tela (evita
 * duplicar essa paleta em cada página — Constitution V). */
export const ROLE_LABEL: Record<WorkspaceRole, string> = {
  OWNER: "Owner",
  ADMIN: "Admin",
  MEMBER: "Member",
};

export const ROLE_ICON: Record<WorkspaceRole, LucideIcon> = {
  OWNER: Crown,
  ADMIN: ShieldCheck,
  MEMBER: User,
};

export const ROLE_BADGE_CLASS: Record<WorkspaceRole, string> = {
  OWNER: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  ADMIN: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  MEMBER: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
};
