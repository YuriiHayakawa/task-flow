import axios from "axios";
import {
  ArrowLeft,
  ArrowLeftRight,
  ShieldCheck,
  ShieldMinus,
  Trash2,
  UserPlus,
  Users,
} from "lucide-react";
import { useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";

import { AddMemberByEmailForm } from "@/components/forms/AddMemberByEmailForm";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useAuth } from "@/contexts/AuthContext";
import { useWorkspace } from "@/hooks/useWorkspace";
import { useWorkspaceMembers } from "@/hooks/useWorkspaceMembers";
import { cn } from "@/lib/utils";
import * as userService from "@/services/userService";
import type { ApiError } from "@/types/apiError";
import type { WorkspaceMember, WorkspaceRole } from "@/types/workspace";
import { pickAccentColor } from "@/utils/accentColor";
import { getApiErrorMessage } from "@/utils/apiErrorMessage";
import { getInitials } from "@/utils/initials";
import {
  ROLE_BADGE_CLASS,
  ROLE_BORDER_CLASS,
  ROLE_HERO_CHIP_CLASS,
  ROLE_ICON,
  ROLE_LABEL,
} from "@/utils/workspaceRole";

interface RoleCountChipProps {
  role: WorkspaceRole;
  count: number;
}

function RoleCountChip({ role, count }: RoleCountChipProps) {
  const Icon = ROLE_ICON[role];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold tabular-nums",
        ROLE_HERO_CHIP_CLASS[role],
      )}
    >
      <Icon className="size-2.5" />
      {count} {ROLE_LABEL[role]}
      {count > 1 ? "s" : ""}
    </span>
  );
}

interface RemoveMemberDialogProps {
  member: WorkspaceMember;
  onConfirm: () => Promise<void>;
}

function RemoveMemberDialog({ member, onConfirm }: RemoveMemberDialogProps) {
  const [error, setError] = useState<string | null>(null);
  const [pendingTasks, setPendingTasks] = useState<string[]>([]);
  const [isRemoving, setIsRemoving] = useState(false);

  async function handleConfirm() {
    setError(null);
    setPendingTasks([]);
    setIsRemoving(true);
    try {
      await onConfirm();
    } catch (err) {
      setError(getApiErrorMessage(err, "Não foi possível remover este membro."));
      if (axios.isAxiosError(err)) {
        const details = (err.response?.data as ApiError | undefined)?.error?.details;
        const titles = details
          ?.map((detail) => (typeof detail.title === "string" ? detail.title : null))
          .filter((title): title is string => title !== null);
        if (titles && titles.length > 0) setPendingTasks(titles);
      }
    } finally {
      setIsRemoving(false);
    }
  }

  return (
    <AlertDialog>
      <Tooltip>
        <TooltipTrigger asChild>
          <AlertDialogTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label={`Remover ${member.name}`}>
              <Trash2 className="size-4 text-destructive" />
            </Button>
          </AlertDialogTrigger>
        </TooltipTrigger>
        <TooltipContent>Remover do workspace</TooltipContent>
      </Tooltip>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Remover {member.name}?</AlertDialogTitle>
          <AlertDialogDescription>
            Esta pessoa perde acesso a este workspace, seus projetos e tarefas.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {error && (
          <div className="text-sm text-destructive">
            <p>{error}</p>
            {pendingTasks.length > 0 && (
              <ul className="mt-1.5 list-inside list-disc text-xs">
                {pendingTasks.map((title) => (
                  <li key={title}>{title}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isRemoving}>Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} disabled={isRemoving} variant="destructive">
            {isRemoving ? "Removendo..." : "Remover"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

interface TransferOwnershipDialogProps {
  member: WorkspaceMember;
  onConfirm: () => Promise<void>;
}

function TransferOwnershipDialog({ member, onConfirm }: TransferOwnershipDialogProps) {
  const [error, setError] = useState<string | null>(null);
  const [isTransferring, setIsTransferring] = useState(false);

  async function handleConfirm() {
    setError(null);
    setIsTransferring(true);
    try {
      await onConfirm();
    } catch (err) {
      setError(getApiErrorMessage(err, "Não foi possível transferir a titularidade."));
      setIsTransferring(false);
    }
  }

  return (
    <AlertDialog>
      <Tooltip>
        <TooltipTrigger asChild>
          <AlertDialogTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label={`Transferir titularidade para ${member.name}`}>
              <ArrowLeftRight className="size-4 text-amber-600 dark:text-amber-400" />
            </Button>
          </AlertDialogTrigger>
        </TooltipTrigger>
        <TooltipContent>Transferir titularidade</TooltipContent>
      </Tooltip>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Transferir titularidade para {member.name}?</AlertDialogTitle>
          <AlertDialogDescription>
            Você deixa de ser Owner (passa a Admin) e {member.name} assume o controle total deste
            workspace. Esta ação não pode ser desfeita por você sozinho — só o novo Owner poderá
            transferi-la de volta.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isTransferring}>Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} disabled={isTransferring} variant="warning">
            {isTransferring ? "Transferindo..." : "Transferir"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

interface MembersHeroProps {
  workspaceId: string;
  workspaceName: string;
  total: number;
  ownerCount: number;
  adminCount: number;
  memberCount: number;
  canManage: boolean;
  onAdd: () => void;
}

/** Mesma identidade escura dos outros heróis — o badge de ícone segue a
 * mesma cor determinística do workspace-pai (`pickAccentColor`), e o
 * resumo é a composição real por role (mesmos rótulos/cores de
 * `WorkspacesHero`, reaproveitados de `workspaceRole.ts`). */
function MembersHero({
  workspaceId,
  workspaceName,
  total,
  ownerCount,
  adminCount,
  memberCount,
  canManage,
  onAdd,
}: MembersHeroProps) {
  const accent = pickAccentColor(workspaceId);

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0b1220] via-[#0a0f1e] to-[#05070f] p-5 shadow-xl shadow-black/20 sm:p-6">
      <div className="blob-drift-a pointer-events-none absolute -top-20 -left-14 size-56 rounded-full bg-blue-600/25 blur-[80px]" />
      <div className="blob-drift-b pointer-events-none absolute -right-16 -bottom-20 size-64 rounded-full bg-violet-500/20 blur-[90px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] bg-[size:32px_32px]" />
      <Users
        className="pointer-events-none absolute -right-8 -bottom-10 size-44 -rotate-12 text-blue-500/[0.06]"
        strokeWidth={1}
      />

      <div className="relative flex flex-col gap-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="relative flex size-10 shrink-0 items-center justify-center">
              <div className={cn("absolute inset-0 rounded-xl opacity-70 blur-md", accent.glowClass)} />
              <div
                className={cn(
                  "relative flex size-10 items-center justify-center rounded-xl bg-gradient-to-br shadow-lg",
                  accent.gradientClass,
                  accent.shadowClass,
                )}
              >
                <Users className="size-5 text-white" strokeWidth={2.25} />
              </div>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">Membros</h1>
              <p className="text-xs text-slate-400 sm:text-sm">
                Quem participa de &quot;{workspaceName}&quot; e com qual role.
              </p>
            </div>
          </div>
          {canManage && (
            <Button
              onClick={onAdd}
              className="h-10 w-fit gap-1.5 rounded-xl bg-white px-4 text-sm font-semibold text-[#05070f] shadow-lg shadow-black/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-xl hover:shadow-blue-500/10"
            >
              <UserPlus className="size-4" />
              Adicionar membro
            </Button>
          )}
        </div>

        {total > 0 && (
          <div className="flex flex-col gap-3 border-t border-white/10 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2.5">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-blue-400/15">
                <Users className="size-4 text-blue-300" />
              </div>
              <div className="leading-tight">
                <p className="text-xl font-bold tabular-nums text-white">{total}</p>
                <p className="text-[11px] font-medium text-slate-400">
                  {total === 1 ? "membro" : "membros"}
                </p>
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-1.5">
              {ownerCount > 0 && <RoleCountChip role="OWNER" count={ownerCount} />}
              {adminCount > 0 && <RoleCountChip role="ADMIN" count={adminCount} />}
              {memberCount > 0 && <RoleCountChip role="MEMBER" count={memberCount} />}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function WorkspaceMembersPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const { workspace, refetch: refetchWorkspace } = useWorkspace(workspaceId ?? "");
  const {
    members,
    isLoading,
    error,
    addMember,
    updateMemberRole,
    removeMember,
    transferOwnership,
  } = useWorkspaceMembers(workspaceId ?? "");
  const [addOpen, setAddOpen] = useState(false);

  if (!workspaceId) {
    return <Navigate to="/workspaces" replace />;
  }

  const myRole = workspace?.my_role;
  const canManageMembers = myRole === "OWNER" || myRole === "ADMIN";
  const isOwner = myRole === "OWNER";

  async function handleAddMember(email: string) {
    const found = await userService.lookupByEmail(email);
    await addMember({ user_id: found.id });
    setAddOpen(false);
  }

  /** `useWorkspace` e `useWorkspaceMembers` são hooks independentes — a
   * transferência de titularidade muda `my_role` do usuário atual (o
   * campo que `useWorkspace` fornece), então além de recarregar a lista
   * de membros (já feito por `transferOwnership`), também precisamos
   * recarregar o workspace, senão a badge "Você é Owner" e as permissões
   * da página ficam desatualizadas até um refresh manual. */
  async function handleTransferOwnership(newOwnerUserId: string) {
    await transferOwnership({ new_owner_user_id: newOwnerUserId });
    await refetchWorkspace();
  }

  const ownerCount = members.filter((member) => member.role === "OWNER").length;
  const adminCount = members.filter((member) => member.role === "ADMIN").length;
  const memberCount = members.filter((member) => member.role === "MEMBER").length;

  return (
    // Provider próprio (não depende só do da `AuthenticatedLayout`) — a
    // página funciona mesmo renderizada isolada (ex.: testes).
    <TooltipProvider delayDuration={0}>
      <div className="flex flex-col gap-5">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(`/workspaces/${workspaceId}`)}
          className="w-fit gap-1.5 text-muted-foreground"
        >
          <ArrowLeft className="size-4" />
          {workspace?.name ?? "Workspace"}
        </Button>

        <MembersHero
          workspaceId={workspaceId}
          workspaceName={workspace?.name ?? "..."}
          total={members.length}
          ownerCount={ownerCount}
          adminCount={adminCount}
          memberCount={memberCount}
          canManage={canManageMembers}
          onAdd={() => setAddOpen(true)}
        />

        {isLoading && (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
          </div>
        )}

        {!isLoading && error && <p className="text-sm text-destructive">{error}</p>}

        {!isLoading && !error && (
          <div className="flex flex-col gap-2">
            {members.map((member) => {
              const RoleIcon = ROLE_ICON[member.role];
              const isSelf = member.user_id === currentUser?.id;
              const canChangeRole = isOwner && member.role !== "OWNER";
              const canRemove =
                member.role === "MEMBER" ? canManageMembers : member.role === "ADMIN" ? isOwner : false;
              const canTransferTo = isOwner && member.role !== "OWNER";

              return (
                <div
                  key={member.user_id}
                  className={cn(
                    "flex flex-wrap items-center gap-3 rounded-xl border border-l-4 bg-card p-3 shadow-sm",
                    ROLE_BORDER_CLASS[member.role],
                  )}
                >
                  <Avatar className="rounded-lg">
                    <AvatarFallback className="rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 text-xs font-semibold text-white">
                      {getInitials(member.name)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {member.name}
                      {isSelf && <span className="ml-1.5 text-xs text-muted-foreground">(você)</span>}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">{member.email}</p>
                  </div>
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium",
                      ROLE_BADGE_CLASS[member.role],
                    )}
                  >
                    <RoleIcon className="size-3" />
                    {ROLE_LABEL[member.role]}
                  </span>

                  <div className="flex items-center gap-1">
                    {canChangeRole && (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={
                              member.role === "MEMBER"
                                ? `Promover ${member.name} a Admin`
                                : `Rebaixar ${member.name} a Member`
                            }
                            onClick={() =>
                              void updateMemberRole(member.user_id, member.role === "MEMBER" ? "ADMIN" : "MEMBER")
                            }
                          >
                            {member.role === "MEMBER" ? (
                              <ShieldCheck className="size-4 text-blue-600 dark:text-blue-400" />
                            ) : (
                              <ShieldMinus className="size-4 text-muted-foreground" />
                            )}
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                          {member.role === "MEMBER" ? "Promover a Admin" : "Rebaixar a Member"}
                        </TooltipContent>
                      </Tooltip>
                    )}
                    {canTransferTo && (
                      <TransferOwnershipDialog
                        member={member}
                        onConfirm={() => handleTransferOwnership(member.user_id)}
                      />
                    )}
                    {canRemove && (
                      <RemoveMemberDialog member={member} onConfirm={() => removeMember(member.user_id)} />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <Sheet open={addOpen} onOpenChange={setAddOpen}>
          <SheetContent>
            <SheetHeader>
              <div className="flex items-center gap-2.5">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/20">
                  <UserPlus className="size-4 text-white" />
                </div>
                <SheetTitle>Adicionar membro</SheetTitle>
              </div>
            </SheetHeader>
            <div className="px-4 pb-4">
              <AddMemberByEmailForm
                onAdd={handleAddMember}
                onCancel={() => setAddOpen(false)}
                helperText="A pessoa entra como Member — promover a Admin é uma ação separada."
              />
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </TooltipProvider>
  );
}
