import { useEffect, useState } from "react";
import {
  Bell,
  Building2,
  ChevronRight,
  ChevronsLeft,
  Kanban,
  ListTodo,
  LayoutDashboard,
  LogOut,
  Repeat,
  ShieldCheck,
  User as UserIcon,
  Workflow,
} from "lucide-react";
import { Link, Outlet, useLocation } from "react-router-dom";

import { NotificationBadge } from "@/components/layout/NotificationBadge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarProvider,
  SidebarSeparator,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAuth } from "@/contexts/AuthContext";
import { useNotifications } from "@/hooks/useNotifications";

/** Substitui o `SidebarTrigger` padrão — mora ao lado do logo, no cabeçalho
 * da própria sidebar (não no cabeçalho do conteúdo, reservado para o título
 * de cada tela no futuro). Ícone discreto do mesmo tamanho do logo, com o
 * acento azul da marca no hover; a seta gira 180° conforme o estado. */
function SidebarCollapseButton() {
  const { toggleSidebar, state } = useSidebar();
  const label = state === "expanded" ? "Recolher menu" : "Expandir menu";

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={label}
          className="group flex size-7 shrink-0 items-center justify-center rounded-lg text-sidebar-foreground/60 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        >
          <ChevronsLeft
            className={`size-4 transition-transform duration-300 group-hover:scale-110 ${
              state === "collapsed" ? "rotate-180" : ""
            }`}
          />
        </button>
      </TooltipTrigger>
      <TooltipContent side="bottom">{label}</TooltipContent>
    </Tooltip>
  );
}

/** "Perfil" vem primeiro no menu — padrão comum em outros produtos (conta
 * do usuário no topo da navegação principal, não perdida no fim da lista). */
const NAV_ITEMS_BEFORE_TASKS = [
  { to: "/profile", label: "Perfil", icon: UserIcon },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/workspaces", label: "Workspaces", icon: Building2 },
] as const;

/** "Minhas tarefas" deixou de ser um link direto: agora é um grupo que
 * expande em duas rotas reais — o quadro kanban (`/tasks`) e as rotinas
 * recorrentes (`/tasks/recurring`), que antes viviam como abas dentro da
 * própria página (`TasksTabs`, removido). */
const TASKS_SUB_ITEMS = [
  { to: "/tasks", label: "Esteira de tarefas", icon: Kanban },
  { to: "/tasks/recurring", label: "Tarefas Fixas", icon: Repeat },
] as const;

const NAV_ITEMS_AFTER_TASKS = [
  { to: "/notifications", label: "Notificações", icon: Bell },
] as const;

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return (parts[0]![0] + parts[parts.length - 1]![0]).toUpperCase();
}

export function AuthenticatedLayout() {
  const { user, isSystemAdmin, logout } = useAuth();
  const location = useLocation();
  // Uma única instância para o app inteiro (não uma por página) — o badge
  // da sidebar logo abaixo e a `NotificationsPage` (via `Outlet context`)
  // compartilham exatamente este estado, então marcar como lida em
  // qualquer um dos dois lugares atualiza o outro na hora.
  const notifications = useNotifications();

  const isTasksSectionActive = TASKS_SUB_ITEMS.some(
    (item) => item.to === location.pathname,
  );
  const [tasksMenuOpen, setTasksMenuOpen] = useState(isTasksSectionActive);

  // Ao navegar direto para uma das duas rotas (link externo, "voltar" do
  // navegador etc.), o grupo abre sozinho — mas não fecha ao sair, pra não
  // "sumir" a opção embaixo do cursor enquanto o usuário ainda está com o
  // menu aberto.
  useEffect(() => {
    if (isTasksSectionActive) setTasksMenuOpen(true);
  }, [isTasksSectionActive]);

  return (
    <TooltipProvider delayDuration={0}>
      <SidebarProvider>
        {/* O wrapper (não o próprio <Sidebar>) precisa carregar a classe de
            tema: o componente já fixa `color` via `text-sidebar-foreground`
            no seu próprio elemento raiz, então a sobrescrita das variáveis
            precisa estar disponível ANTES dessa camada, não dentro dela. */}
        <div className="sidebar-brand contents">
          <Sidebar collapsible="icon">
            <SidebarHeader className="relative overflow-hidden">
              <div className="pointer-events-none absolute -top-6 -left-6 size-24 rounded-full bg-blue-600/25 blur-2xl" />
              <div className="relative z-10 flex items-center justify-between gap-2 px-1 py-1.5 group-data-[collapsible=icon]:flex-col group-data-[collapsible=icon]:gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/40">
                    <Workflow className="size-4 text-white" strokeWidth={2.25} />
                  </div>
                  <span className="truncate text-sm font-bold tracking-tight text-white group-data-[collapsible=icon]:hidden">
                    TaskFlow
                  </span>
                </div>
                <SidebarCollapseButton />
              </div>
            </SidebarHeader>
            <SidebarContent>
              <SidebarGroup>
                <SidebarGroupContent>
                  <SidebarMenu className="gap-1">
                    {NAV_ITEMS_BEFORE_TASKS.map(({ to, label, icon: Icon }) => {
                      const isActive = location.pathname === to;
                      return (
                        <SidebarMenuItem key={to}>
                          <SidebarMenuButton
                            asChild
                            isActive={isActive}
                            tooltip={label}
                            className="h-10 rounded-lg text-[0.925rem] [&_svg]:size-[1.125rem]"
                          >
                            <Link to={to}>
                              <Icon className="transition-transform duration-200 group-hover/menu-button:scale-110" />
                              <span>{label}</span>
                            </Link>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      );
                    })}

                    <Collapsible
                      open={tasksMenuOpen}
                      onOpenChange={setTasksMenuOpen}
                      className="group/tasks-collapsible"
                    >
                      <SidebarMenuItem>
                        <CollapsibleTrigger asChild>
                          <SidebarMenuButton
                            isActive={isTasksSectionActive}
                            tooltip="Minhas tarefas"
                            className="h-10 rounded-lg text-[0.925rem] [&_svg]:size-[1.125rem]"
                          >
                            <ListTodo className="transition-transform duration-200 group-hover/menu-button:scale-110" />
                            <span>Minhas tarefas</span>
                            <ChevronRight className="ml-auto size-4! shrink-0 transition-transform duration-200 group-data-[state=open]/tasks-collapsible:rotate-90" />
                          </SidebarMenuButton>
                        </CollapsibleTrigger>
                        <CollapsibleContent>
                          <SidebarMenuSub>
                            {TASKS_SUB_ITEMS.map(({ to, label, icon: Icon }) => {
                              const isActive = location.pathname === to;
                              return (
                                <SidebarMenuSubItem key={to}>
                                  <SidebarMenuSubButton asChild isActive={isActive}>
                                    <Link to={to}>
                                      <Icon />
                                      <span>{label}</span>
                                    </Link>
                                  </SidebarMenuSubButton>
                                </SidebarMenuSubItem>
                              );
                            })}
                          </SidebarMenuSub>
                        </CollapsibleContent>
                      </SidebarMenuItem>
                    </Collapsible>

                    {NAV_ITEMS_AFTER_TASKS.map(({ to, label, icon: Icon }) => {
                      const isActive = location.pathname === to;
                      return (
                        <SidebarMenuItem key={to}>
                          <SidebarMenuButton
                            asChild
                            isActive={isActive}
                            tooltip={label}
                            className="h-10 rounded-lg text-[0.925rem] [&_svg]:size-[1.125rem]"
                          >
                            <Link to={to}>
                              <Icon className="transition-transform duration-200 group-hover/menu-button:scale-110" />
                              <span>{label}</span>
                            </Link>
                          </SidebarMenuButton>
                          {/* Irmão do botão, não filho — `SidebarMenuBadge`
                              se posiciona de forma absoluta em relação ao
                              `SidebarMenuItem` (Constitution V). */}
                          {to === "/notifications" && (
                            <NotificationBadge count={notifications.unreadCount} />
                          )}
                        </SidebarMenuItem>
                      );
                    })}
                    {isSystemAdmin && (
                      <>
                        <SidebarSeparator className="my-2" />
                        <SidebarMenuItem>
                          <SidebarMenuButton
                            asChild
                            isActive={location.pathname === "/admin"}
                            tooltip="Administração"
                            className="h-10 rounded-lg text-[0.925rem] [&_svg]:size-[1.125rem]"
                          >
                            <Link to="/admin">
                              <ShieldCheck className="transition-transform duration-200 group-hover/menu-button:scale-110" />
                              <span>Administração</span>
                            </Link>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      </>
                    )}
                  </SidebarMenu>
                </SidebarGroupContent>
              </SidebarGroup>
            </SidebarContent>
            <SidebarFooter>
              <SidebarMenu>
                <SidebarMenuItem>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <SidebarMenuButton size="lg" className="rounded-lg">
                        <Avatar size="sm" className="rounded-lg">
                          <AvatarFallback className="rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 text-[11px] font-semibold text-white">
                            {getInitials(user?.name ?? "?")}
                          </AvatarFallback>
                        </Avatar>
                        <div className="grid flex-1 text-left leading-tight">
                          <span className="truncate text-sm font-medium">
                            {user?.name ?? "Usuário"}
                          </span>
                          <span className="truncate text-xs text-sidebar-foreground/60">
                            {user?.email}
                          </span>
                        </div>
                      </SidebarMenuButton>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent side="top" align="start" className="w-56">
                      <DropdownMenuItem variant="destructive" onClick={logout}>
                        <LogOut />
                        Sair
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarFooter>
          </Sidebar>
        </div>
        <SidebarInset>
          {/* Sem barra de cabeçalho fixa: cada tela monta seu próprio
              cabeçalho (`PageHeader`), então uma barra vazia aqui só
              criava espaço morto no topo. */}
          <main className="flex-1 overflow-auto p-6">
            {/* `NotificationsPage` lê isto via `useOutletContext` — mesma
                instância de `useNotifications` que alimenta o badge da
                sidebar acima, evitando um segundo fetch e mantendo os dois
                sincronizados sem um Context dedicado. */}
            <Outlet context={notifications} />
          </main>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}
