import {
  AlignLeft,
  ArrowLeft,
  Calendar,
  Check,
  FolderKanban,
  Type,
  UserRound,
} from "lucide-react";
import { useEffect, useRef, useState, type SubmitEvent } from "react";
import { Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/contexts/AuthContext";
import { useProjects } from "@/hooks/useProjects";
import { useTask } from "@/hooks/useTask";
import { useWorkspaceMembers } from "@/hooks/useWorkspaceMembers";
import { cn } from "@/lib/utils";
import * as taskService from "@/services/taskService";
import type { TaskCreate, TaskPriority, TaskStatus } from "@/types/task";
import { PRIORITY_LABEL, STATUS_LABEL } from "@/utils/taskStyle";

const STATUS_OPTIONS: TaskStatus[] = ["PENDING", "IN_PROGRESS", "DONE"];
const PRIORITY_OPTIONS: TaskPriority[] = ["LOW", "MEDIUM", "HIGH", "URGENT"];
const NO_PROJECT_VALUE = "__none__";

/** Formulário de página inteira (não Sheet) para tarefas de workspace/
 * projeto — diferente do Sheet simples de "Minhas tarefas" porque aqui
 * existem responsável e projeto para escolher, o que pede mais espaço.
 * Cobre criação (`/tasks/new?workspace_id=&project_id=`) e edição
 * (`/tasks/:taskId/edit`). */
export function TaskFormPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const isEdit = Boolean(taskId);

  const { task, isLoading: taskLoading, error: taskError, updateTask } = useTask(taskId ?? "");

  const workspaceId = isEdit ? (task?.workspace_id ?? "") : (searchParams.get("workspace_id") ?? "");
  const { members, isLoading: membersLoading } = useWorkspaceMembers(workspaceId);
  const { projects, isLoading: projectsLoading } = useProjects(workspaceId);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<TaskStatus>("PENDING");
  const [priority, setPriority] = useState<TaskPriority>("MEDIUM");
  const [dueDate, setDueDate] = useState("");
  const [assigneeId, setAssigneeId] = useState("");
  const [projectId, setProjectId] = useState<string>(searchParams.get("project_id") ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const initializedFromTask = useRef(false);

  // Em modo de edição, a tarefa chega de forma assíncrona — sincroniza o
  // formulário assim que ela carrega, uma única vez (não sobrescreve o que
  // o usuário já digitou em edições futuras do próprio `task`).
  useEffect(() => {
    if (isEdit && task && !initializedFromTask.current) {
      setTitle(task.title);
      setDescription(task.description ?? "");
      setStatus(task.status);
      setPriority(task.priority);
      setDueDate(task.due_date ?? "");
      setAssigneeId(task.assignee_id);
      setProjectId(task.project_id ?? "");
      initializedFromTask.current = true;
    }
  }, [isEdit, task]);

  // Em modo de criação, assim que a lista de membros chega, o responsável
  // default é o próprio usuário (ainda pode ser trocado).
  useEffect(() => {
    if (!isEdit && !assigneeId && currentUser && members.some((m) => m.user_id === currentUser.id)) {
      setAssigneeId(currentUser.id);
    }
  }, [isEdit, assigneeId, currentUser, members]);

  if (!isEdit && !workspaceId) {
    return <Navigate to="/workspaces" replace />;
  }
  if (isEdit && !taskId) {
    return <Navigate to="/workspaces" replace />;
  }

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const dueDatePayload = dueDate === "" ? null : dueDate;
      const projectPayload = projectId === "" ? null : projectId;

      if (isEdit && taskId) {
        await updateTask({
          title,
          description: description.trim() === "" ? null : description,
          status,
          priority,
          due_date: dueDatePayload,
          assignee_id: assigneeId,
        });
        navigate(`/tasks/${taskId}`);
      } else {
        const payload: TaskCreate = {
          title,
          description: description.trim() === "" ? null : description,
          status,
          priority,
          due_date: dueDatePayload,
          assignee_id: assigneeId || null,
          workspace_id: workspaceId,
          project_id: projectPayload,
        };
        const created = await taskService.create(payload);
        navigate(`/tasks/${created.id}`);
      }
    } catch {
      setError("Não foi possível salvar a tarefa. Verifique os dados e tente novamente.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const backTo = isEdit && task ? `/tasks/${task.id}` : workspaceId ? `/workspaces/${workspaceId}` : "/workspaces";

  // O `Select` de responsável/projeto só deve montar depois que `members`/
  // `projects` já carregaram: passar um `value` sem nenhum `SelectItem`
  // correspondente ainda montado faz o Radix Select "corrigir" sozinho o
  // valor de volta para vazio (via `onValueChange("")`), apagando o que
  // acabamos de sincronizar da tarefa — daí esperar o contexto completo
  // antes de renderizar o formulário, em vez de só a tarefa em si.
  const isFormLoading = isEdit
    ? taskLoading || (Boolean(task) && (membersLoading || projectsLoading))
    : membersLoading || projectsLoading;
  const showForm = isEdit ? !taskLoading && !taskError && Boolean(task) && !isFormLoading : !isFormLoading;

  return (
    <div className="flex flex-col gap-5">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate(backTo)}
        className="w-fit gap-1.5 text-muted-foreground"
      >
        <ArrowLeft className="size-4" />
        Voltar
      </Button>

      <PageHeader
        icon={FolderKanban}
        title={isEdit ? "Editar tarefa" : "Nova tarefa"}
        description="Tarefas de workspace têm responsável e podem pertencer a um projeto."
      />

      {isFormLoading && <Skeleton className="h-96 w-full rounded-2xl" />}
      {isEdit && !taskLoading && taskError && <p className="text-sm text-destructive">{taskError}</p>}

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-5 rounded-2xl border bg-card p-6 shadow-sm"
        >
          <div className="flex flex-col gap-2">
            <Label htmlFor="task-title">Título</Label>
            <div className="relative">
              <Type className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="task-title"
                required
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                className="h-11 rounded-xl pl-9"
                placeholder="Ex.: Preparar apresentação"
              />
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="task-description">Descrição</Label>
            <div className="relative">
              <AlignLeft className="pointer-events-none absolute top-3 left-3 size-4 text-muted-foreground" />
              <Textarea
                id="task-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                className="min-h-24 rounded-xl pl-9"
                placeholder="Detalhes da tarefa (opcional)"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label className="flex items-center gap-1.5">
                <UserRound className="size-3.5" />
                Responsável
              </Label>
              <Select value={assigneeId} onValueChange={setAssigneeId}>
                <SelectTrigger className="h-11 w-full rounded-xl">
                  <SelectValue placeholder="Selecione um responsável" />
                </SelectTrigger>
                <SelectContent>
                  {members.map((member) => (
                    <SelectItem key={member.user_id} value={member.user_id}>
                      {member.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-2">
              <Label className="flex items-center gap-1.5">
                <FolderKanban className="size-3.5" />
                Projeto
              </Label>
              <Select
                value={projectId === "" ? NO_PROJECT_VALUE : projectId}
                onValueChange={(value) => setProjectId(value === NO_PROJECT_VALUE ? "" : value)}
              >
                <SelectTrigger className="h-11 w-full rounded-xl">
                  <SelectValue placeholder="Nenhum" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_PROJECT_VALUE}>Nenhum (tarefa do workspace)</SelectItem>
                  {projects.map((project) => (
                    <SelectItem key={project.id} value={project.id}>
                      {project.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <Label>Status</Label>
            <div className="grid grid-cols-3 gap-2">
              {STATUS_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setStatus(option)}
                  className={cn(
                    "rounded-xl border px-2 py-2 text-xs font-medium transition-colors",
                    status === option
                      ? "border-blue-400 bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                      : "border-border text-muted-foreground hover:bg-muted",
                  )}
                >
                  {STATUS_LABEL[option]}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <Label>Prioridade</Label>
            <div className="grid grid-cols-4 gap-2">
              {PRIORITY_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setPriority(option)}
                  className={cn(
                    "rounded-xl border px-2 py-2 text-xs font-medium transition-colors",
                    priority === option
                      ? "border-blue-400 bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                      : "border-border text-muted-foreground hover:bg-muted",
                  )}
                >
                  {PRIORITY_LABEL[option]}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:w-1/2">
            <Label htmlFor="task-due-date">Prazo</Label>
            <div className="relative">
              <Calendar className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="task-due-date"
                type="date"
                value={dueDate}
                onChange={(event) => setDueDate(event.target.value)}
                className="h-11 rounded-xl pl-9"
              />
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="mt-2 flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate(backTo)}
              disabled={isSubmitting}
              className="rounded-xl"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || title.trim() === "" || assigneeId === ""}
              className="rounded-xl bg-blue-600 text-white hover:bg-blue-500"
            >
              <Check className="size-4" />
              {isSubmitting ? "Salvando..." : isEdit ? "Salvar" : "Criar tarefa"}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
