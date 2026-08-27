import { SidebarMenuBadge } from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";

interface NotificationBadgeProps {
  count: number;
  className?: string;
}

/** Contador de não lidas no item "Notificações" da sidebar
 * (`AuthenticatedLayout`) — wrapper fino sobre `SidebarMenuBadge` (já
 * existe no kit de sidebar do projeto, cuida do posicionamento absoluto
 * relativo ao `SidebarMenuButton` irmão e de sumir sozinho quando a
 * sidebar colapsa para ícones — Constitution V, reusar antes de criar).
 * Este componente só adiciona a cor de alerta e a regra de negócio da UI:
 * nada com `count <= 0`, satura em "99+". Deve ser renderizado como irmão
 * do `SidebarMenuButton`, dentro do mesmo `SidebarMenuItem` — nunca dentro
 * do próprio botão (é a peça que ancora o `position: absolute`). */
export function NotificationBadge({ count, className }: NotificationBadgeProps) {
  if (count <= 0) return null;

  return (
    <SidebarMenuBadge className={cn("bg-red-500 text-white", className)}>
      {count > 99 ? "99+" : count}
    </SidebarMenuBadge>
  );
}
