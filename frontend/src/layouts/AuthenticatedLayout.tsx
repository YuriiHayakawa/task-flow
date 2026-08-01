import {
  Bell,
  Building2,
  ListTodo,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  User as UserIcon,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "@/contexts/AuthContext";
import { Separator } from "@/components/ui/separator";
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
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/workspaces", label: "Workspaces", icon: Building2 },
  { to: "/tasks", label: "Minhas tarefas", icon: ListTodo },
  { to: "/notifications", label: "Notificações", icon: Bell },
  { to: "/profile", label: "Perfil", icon: UserIcon },
] as const;

export function AuthenticatedLayout() {
  const { user, isSystemAdmin, logout } = useAuth();

  return (
    <TooltipProvider delayDuration={0}>
      <SidebarProvider>
        <Sidebar collapsible="icon">
          <SidebarHeader>
            <span className="truncate px-2 py-1 text-sm font-semibold tracking-tight group-data-[collapsible=icon]:hidden">
              TaskFlow
            </span>
          </SidebarHeader>
          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu>
                  {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
                    <SidebarMenuItem key={to}>
                      <SidebarMenuButton asChild tooltip={label}>
                        <NavLink to={to}>
                          <Icon />
                          <span>{label}</span>
                        </NavLink>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                  {isSystemAdmin && (
                    <SidebarMenuItem>
                      <SidebarMenuButton asChild tooltip="Administração">
                        <NavLink to="/admin">
                          <ShieldCheck />
                          <span>Administração</span>
                        </NavLink>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  )}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>
          <SidebarFooter>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton onClick={logout} tooltip="Sair">
                  <LogOut />
                  <span>{user?.name ?? "Sair"}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarFooter>
        </Sidebar>
        <SidebarInset>
          <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <Separator orientation="vertical" className="h-4" />
            <span className="text-muted-foreground text-sm">{user?.email}</span>
          </header>
          <main className="flex-1 overflow-auto p-6">
            <Outlet />
          </main>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}
