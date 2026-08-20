import uuid

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.enums.workspace_role import WorkspaceRole
from app.models.recurring_task import RecurringTask
from app.models.task import Task
from app.models.user import User
from app.repositories.recurring_task_repository import RecurringTaskRepository
from app.repositories.task_member_repository import TaskMemberRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository


def require_task_visible(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Task:
    """Visibilidade (contracts/_conventions.md, research.md #8): tarefa
    pessoal só é visível ao próprio criador; tarefa de workspace é visível a
    qualquer membro do workspace, qualquer role. `404` — nunca `403` — para
    quem não tem visibilidade nenhuma, nunca confirmando a existência da
    tarefa a quem não tem acesso.

    Não prevista nominalmente em T077 (que lista apenas
    `require_task_participant`/`require_task_editor`/`require_task_delete`),
    mas necessária como base compartilhada pelas três — e por
    `GET /tasks/{task_id}` e `GET /tasks/{task_id}/members` (Bloco 4), que
    também não têm `workspace_id` no path para reaproveitar
    `require_workspace_member` diretamente."""
    task = TaskRepository(db).get_by_id(task_id)
    if task is None:
        raise NotFoundError("Tarefa não encontrada.")

    if task.workspace_id is None:
        if task.creator_id != current_user.id:
            raise NotFoundError("Tarefa não encontrada.")
        return task

    role = WorkspaceMemberRepository(db).get_role(task.workspace_id, current_user.id)
    if role is None:
        raise NotFoundError("Tarefa não encontrada.")
    return task


def require_task_participant(
    task: Task = Depends(require_task_visible),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Task:
    """Colaboração (research.md #8): responsável, participante explícito
    (`TaskMember`), ou o próprio criador se a tarefa for pessoal. Owner/Admin
    do workspace MUST NOT ser tratados como participantes automáticos só por
    deterem essas roles — se quiserem colaborar, precisam ser adicionados
    como qualquer outro membro (`POST /tasks/{id}/members`)."""
    if task.workspace_id is None:
        return task  # já confirmado criador por require_task_visible

    if current_user.id == task.assignee_id:
        return task
    if TaskMemberRepository(db).exists(task.id, current_user.id):
        return task

    raise ForbiddenError("Você precisa ser participante desta tarefa para executar esta ação.")


def require_task_editor(
    task: Task = Depends(require_task_visible),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Task:
    """Administração — editar (refinamento #7): criador, responsável, ou
    Owner/Admin do workspace; tarefa pessoal, só o criador. Usada em
    `PATCH /tasks/{id}` e na gestão de `TaskMember`."""
    if task.workspace_id is None:
        return task  # já confirmado criador

    if current_user.id in (task.creator_id, task.assignee_id):
        return task

    role = WorkspaceMemberRepository(db).get_role(task.workspace_id, current_user.id)
    if role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        return task

    raise ForbiddenError("Você não tem permissão para editar esta tarefa.")


def require_task_delete(
    task: Task = Depends(require_task_visible),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Task:
    """Administração — excluir (refinamento #7): criador, ou Owner/Admin do
    workspace — o responsável isolado (que não seja também o criador) MUST
    NOT excluir; tarefa pessoal, só o criador. Usada em
    `DELETE /tasks/{id}`."""
    if task.workspace_id is None:
        return task  # já confirmado criador

    if current_user.id == task.creator_id:
        return task

    role = WorkspaceMemberRepository(db).get_role(task.workspace_id, current_user.id)
    if role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        return task

    raise ForbiddenError("Você não tem permissão para excluir esta tarefa.")


def require_recurring_task_owner(
    recurring_task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecurringTask:
    """Única regra de autorização de Tarefa Fixa (research.md #6, 002-tarefas-
    fixas): sem níveis de visibilidade/colaboração/administração como em
    `Task` — uma Tarefa Fixa nunca é vista por ninguém além do dono
    (FR-011), então um único nível já cobre 100% dos casos. `404` (nunca
    `403`) para quem não é dono, mesmo padrão de `require_task_visible`."""
    recurring_task = RecurringTaskRepository(db).get_by_id(recurring_task_id)
    if recurring_task is None or recurring_task.owner_id != current_user.id:
        raise NotFoundError("Tarefa fixa não encontrada.")
    return recurring_task
