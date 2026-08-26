import {
  Calendar,
  CheckCircle2,
  IdCard,
  Mail,
  PencilIcon,
  ShieldCheck,
  User as UserIcon,
  X,
} from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useProfile } from "@/hooks/useProfile";
import { cn } from "@/lib/utils";
import type { User } from "@/types/user";
import { getApiErrorMessage } from "@/utils/apiErrorMessage";
import { getInitials } from "@/utils/initials";

/** Mesmo hero escuro usado em Workspaces/Projetos/Tarefas (`WorkspaceMembersHero`,
 * `ProjectHero`, `TasksHero`...) — simplificado (sem ação nem estatística no
 * cabeçalho), já que esta tela é sobre UMA pessoa (o próprio usuário), não
 * uma lista. Identidade em azul fixo (não `pickAccentColor`, pensado para
 * variar entre cards de uma grade) — é o mesmo azul do avatar do usuário na
 * sidebar, então a "cara" da conta permanece reconhecível entre as duas. */
function ProfileHero({ user }: { user: User }) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0b1220] via-[#0a0f1e] to-[#05070f] p-5 shadow-xl shadow-black/20 sm:p-6">
      <div className="blob-drift-a pointer-events-none absolute -top-20 -left-14 size-56 rounded-full bg-blue-600/25 blur-[80px]" />
      <div className="blob-drift-b pointer-events-none absolute -right-16 -bottom-20 size-64 rounded-full bg-violet-500/20 blur-[90px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] bg-[size:32px_32px]" />
      <UserIcon
        className="pointer-events-none absolute -right-8 -bottom-10 size-44 -rotate-12 text-blue-500/[0.06]"
        strokeWidth={1}
      />

      <div className="relative flex items-center gap-4">
        <Avatar className="size-14 shrink-0 rounded-2xl ring-2 ring-white/10">
          <AvatarFallback className="rounded-2xl bg-gradient-to-br from-blue-400 to-blue-700 text-base font-semibold text-white">
            {getInitials(user.name)}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-xl font-bold tracking-tight text-white sm:text-2xl">
            {user.name}
          </h1>
          <p className="truncate text-xs text-slate-400 sm:text-sm">{user.email}</p>
        </div>
        <Badge
          className={cn(
            "shrink-0 border-transparent",
            user.is_active ? "bg-emerald-400/15 text-emerald-300" : "bg-slate-400/15 text-slate-300",
          )}
        >
          {user.is_active ? "Conta ativa" : "Conta desativada"}
        </Badge>
      </div>
    </div>
  );
}

/** US7 — perfil do usuário autenticado: ver/editar nome e e-mail, consultar
 * status da conta. `user` vem do `AuthContext` (via `useProfile`), que na
 * prática já está resolvido quando esta página monta (`ProtectedRoute`
 * segura a navegação até `isLoading` virar `false`) — mas o hiato
 * assíncrono existe (e é exercitado em teste, que monta a página sem esse
 * guard), então os campos são sincronizados por efeito em vez de inicializados
 * uma única vez, e um skeleton cobre a janela em que `user` ainda é `null`. */
export function ProfilePage() {
  const { user, updateProfile } = useProfile();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Campos começam travados (view) — só liberam depois de um clique
  // explícito em "Editar", pra evitar mexer num campo sem querer.
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (user) {
      setName(user.name);
      setEmail(user.email);
    }
  }, [user]);

  if (!user) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-[104px] rounded-2xl" />
        <Skeleton className="mx-auto h-96 w-full max-w-xl rounded-2xl" />
      </div>
    );
  }

  const hasChanges = name.trim() !== user.name || email.trim() !== user.email;
  const memberSinceLabel = new Date(user.created_at).toLocaleDateString("pt-BR");

  function startEditing() {
    setError(null);
    setSuccess(false);
    setIsEditing(true);
  }

  function cancelEditing() {
    setName(user!.name);
    setEmail(user!.email);
    setError(null);
    setIsEditing(false);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(false);
    setIsSubmitting(true);
    try {
      await updateProfile({
        ...(name.trim() !== user!.name ? { name: name.trim() } : {}),
        ...(email.trim() !== user!.email ? { email: email.trim() } : {}),
      });
      setSuccess(true);
      setIsEditing(false);
    } catch (err) {
      setError(getApiErrorMessage(err, "Não foi possível salvar as alterações. Tente novamente."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <ProfileHero user={user} />

      {/* Um card só, de novo — mas reformulado: botão "Editar" agora sólido
       * em azul (mesma cor de "Salvar alterações", reforçando que é a ação
       * primária do card) e uma faixa de metadados da conta (status,
       * antiguidade, tipo) embutida no rodapé do próprio card em vez de um
       * segundo card inteiro — mantém toda a informação de
       * "Detalhes da conta" sem duplicar a moldura/decoração visual. */}
      <div className="relative mx-auto w-full max-w-xl overflow-hidden rounded-2xl border bg-card p-6 shadow-sm">
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-400 via-blue-500 to-blue-600" />
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(37,99,235,0.14)_1px,transparent_0)] bg-[size:24px_24px] dark:bg-[radial-gradient(circle_at_1px_1px,rgba(96,165,250,0.16)_1px,transparent_0)]"
          style={{
            maskImage: "linear-gradient(to bottom, black, transparent 65%)",
            WebkitMaskImage: "linear-gradient(to bottom, black, transparent 65%)",
          }}
        />
        <div className="pointer-events-none absolute -top-14 -right-14 size-44 rounded-full bg-blue-400/15 blur-3xl" />

        <div className="relative mb-5 flex items-center gap-2.5">
          <div className="relative flex size-9 shrink-0 items-center justify-center">
            <div className="absolute inset-0 rounded-lg bg-blue-500/25 blur-md" />
            <div className="relative flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-700 shadow-md shadow-blue-900/20">
              <IdCard className="size-4 text-white" strokeWidth={2.25} />
            </div>
          </div>
          <h2 className="text-sm font-semibold">Dados da conta</h2>
        </div>

        <form onSubmit={handleSubmit} className="relative flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <Label htmlFor="profile-name">Nome</Label>
            <div className="relative">
              <UserIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="profile-name"
                required
                disabled={!isEditing}
                value={name}
                onChange={(event) => {
                  setName(event.target.value);
                  setSuccess(false);
                }}
                className="h-11 rounded-xl pl-9"
              />
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="profile-email">E-mail</Label>
            <div className="relative">
              <Mail className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="profile-email"
                type="email"
                required
                disabled={!isEditing}
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  setSuccess(false);
                }}
                className="h-11 rounded-xl pl-9"
              />
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}
          {success && (
            <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3.5 py-2.5 text-sm text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="size-4 shrink-0" />
              Perfil atualizado com sucesso.
            </div>
          )}

          {/* Ação do card sempre no rodapé, nunca no cabeçalho — "Editar"
           * (fora de edição) e "Cancelar"/"Salvar alterações" (em edição)
           * dividem a mesma posição. Padrão visual = o que já era do
           * "Editar" (compacto: h-8, rounded-lg, text-xs, ícone size-3.5,
           * leve elevação no hover) — os outros dois é que foram ajustados
           * para bater com ele, não o contrário. */}
          <div className="flex justify-end gap-2">
            {isEditing ? (
              <>
                <Button
                  type="button"
                  variant="outline"
                  onClick={cancelEditing}
                  disabled={isSubmitting}
                  className="h-8 rounded-lg text-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-sm"
                >
                  <X className="size-3.5" />
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmitting || !hasChanges || name.trim() === "" || email.trim() === ""}
                  className="h-8 rounded-lg bg-blue-600 text-xs text-white shadow-sm shadow-blue-900/20 transition-all duration-200 hover:-translate-y-0.5 hover:bg-blue-500 hover:shadow-md"
                >
                  {isSubmitting ? "Salvando..." : "Salvar alterações"}
                </Button>
              </>
            ) : (
              <Button
                type="button"
                onClick={startEditing}
                className="h-8 rounded-lg bg-blue-600 px-4 text-xs text-white shadow-sm shadow-blue-900/20 transition-all duration-200 hover:-translate-y-0.5 hover:bg-blue-500 hover:shadow-md"
              >
                <PencilIcon className="size-3.5" />
                Editar
              </Button>
            )}
          </div>
        </form>

        {/* Metadados somente-leitura da conta — mesma informação que estava
         * no segundo card, agora como uma faixa discreta de rodapé. Texto
         * de status abreviado ("Ativa"/"Desativada", não "Conta ativa") de
         * propósito: evita repetir literalmente o badge do hero. */}
        <div className="relative mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-border/70 pt-4 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span
              className={cn(
                "size-1.5 shrink-0 rounded-full",
                user.is_active ? "bg-emerald-500" : "bg-slate-400",
              )}
            />
            {user.is_active ? "Ativa" : "Desativada"}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Calendar className="size-3.5" />
            Membro desde {memberSinceLabel}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <ShieldCheck className="size-3.5" />
            {user.is_system_admin ? "Administrador da plataforma" : "Usuário"}
          </span>
        </div>
      </div>
    </div>
  );
}
