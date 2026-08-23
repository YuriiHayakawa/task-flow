import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import ColumnElement, and_, case, false, func, or_, select
from sqlalchemy.orm import Session

from app.enums.task_priority import TaskPriority
from app.enums.task_sort_by import TaskSortBy
from app.enums.task_sort_order import TaskSortOrder
from app.enums.task_status import TaskStatus
from app.models.task import Task


def active_task_filter() -> ColumnElement[bool]:
    """Expressão reutilizável de "tarefa ativa" (FR-024, data-model.md):
    qualquer tarefa cujo status seja diferente de `DONE`."""
    return Task.status != TaskStatus.DONE


def _visible_task_condition(
    *,
    creator_id: uuid.UUID,
    workspace_ids: Sequence[uuid.UUID],
    owner_workspace_ids: Sequence[uuid.UUID],
    member_project_ids: Sequence[uuid.UUID],
) -> ColumnElement[bool]:
    """Visibilidade de tarefa (003-membros-projeto, data-model.md) —
    reutilizada por `search` e `count_by_status`, nunca reimplementada em
    cada uma:

    - tarefa pessoal do próprio usuário (inalterado);
    - tarefa de workspace SEM projeto vinculado: basta ser membro do
      workspace (inalterado);
    - tarefa de workspace COM projeto vinculado: exige também acesso ao
      projeto — Owner do workspace do projeto (`owner_workspace_ids`) OU
      membro explícito do projeto (`member_project_ids`, sempre também
      restrito a `workspace_ids` — evita que um `ProjectMember` órfão de um
      workspace do qual a pessoa não é mais membro conceda visibilidade,
      spec.md "Edge Cases")."""
    return or_(
        and_(Task.creator_id == creator_id, Task.workspace_id.is_(None)),
        and_(Task.workspace_id.in_(workspace_ids), Task.project_id.is_(None))
        if workspace_ids
        else false(),
        and_(Task.workspace_id.in_(owner_workspace_ids), Task.project_id.is_not(None))
        if owner_workspace_ids
        else false(),
        and_(Task.workspace_id.in_(workspace_ids), Task.project_id.in_(member_project_ids))
        if workspace_ids and member_project_ids
        else false(),
    )


class TaskRepository:
    """Acesso a dados de `Task` — nenhuma regra de negócio aqui (Constitution III)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, task: Task) -> Task:
        self.db.add(task)
        self.db.flush()
        return task

    def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        return self.db.get(Task, task_id)

    def update(self, task: Task) -> Task:
        self.db.flush()
        return task

    def delete(self, task: Task) -> None:
        self.db.delete(task)
        self.db.flush()

    def list_active_by_assignee_in_workspace(
        self, workspace_id: uuid.UUID, assignee_id: uuid.UUID
    ) -> list[Task]:
        """Usado por `WorkspaceMemberService` (FR-024/FR-025) para bloquear a
        remoção de um membro responsável por tarefas ativas no workspace,
        até que sejam reatribuídas."""
        stmt = select(Task).where(
            Task.workspace_id == workspace_id,
            Task.assignee_id == assignee_id,
            active_task_filter(),
        )
        return list(self.db.scalars(stmt))

    def list_active_by_assignee_in_project(
        self, project_id: uuid.UUID, assignee_id: uuid.UUID
    ) -> list[Task]:
        """003-membros-projeto/FR-010 — mesmo padrão de
        `list_active_by_assignee_in_workspace`, usado por
        `ProjectMemberService.remove_member` para bloquear a remoção de um
        membro responsável por tarefas ativas DENTRO DESSE PROJETO
        especificamente."""
        stmt = select(Task).where(
            Task.project_id == project_id,
            Task.assignee_id == assignee_id,
            active_task_filter(),
        )
        return list(self.db.scalars(stmt))

    def count_by_project(self, project_id: uuid.UUID) -> int:
        """Usado apenas para o log estruturado de `ProjectService.delete`
        (refinamento #6, data-model.md) — nunca como pré-condição de exclusão:
        a exclusão de projeto é sempre permitida, e o `ON DELETE SET NULL` do
        banco desvincula as tarefas automaticamente na mesma transação."""
        stmt = select(func.count()).select_from(Task).where(Task.project_id == project_id)
        return self.db.scalar(stmt) or 0

    def count_by_status(
        self,
        *,
        creator_id: uuid.UUID,
        workspace_ids: Sequence[uuid.UUID],
        today: date,
        owner_workspace_ids: Sequence[uuid.UUID] = (),
        member_project_ids: Sequence[uuid.UUID] = (),
        scope_workspace_id: uuid.UUID | None = None,
        scope_project_id: uuid.UUID | None = None,
        personal_only: bool = False,
    ) -> dict[str, int]:
        """Contagens do dashboard (FR-047 a FR-050): tarefas pessoais do
        próprio usuário + tarefas dos workspaces em `workspace_ids` (vazio até
        a US3/US4 ativarem a união em T065 — esta consulta não muda, só passa
        a receber uma lista não vazia). "Atrasada"/"vencendo hoje" usam
        `today` já calculado na timezone da aplicação pelo chamador
        (research.md #9), nunca `CURRENT_DATE` do banco (que seria UTC).

        `owner_workspace_ids`/`member_project_ids` (003-membros-projeto):
        tarefas de projetos restritos aos quais o usuário não tem acesso
        deixam de ser contadas — ver `_visible_task_condition`.

        `scope_workspace_id`/`scope_project_id`/`personal_only` (dashboard com
        escopo — não previstos nas Fases 4/US2 originais) apenas ESTREITAM
        `visible` com um `AND` adicional, mesmo padrão já documentado em
        `search()` abaixo: filtrar por um workspace/projeto do qual o usuário
        não é membro simplesmente não retorna nada, porque já está fora de
        `visible` — nenhuma checagem de autorização separada é necessária
        aqui (a mutualexclusividade entre os três é responsabilidade do
        Service, não desta consulta)."""
        visible = _visible_task_condition(
            creator_id=creator_id,
            workspace_ids=workspace_ids,
            owner_workspace_ids=owner_workspace_ids,
            member_project_ids=member_project_ids,
        )
        conditions: list[ColumnElement[bool]] = [visible]
        if personal_only:
            conditions.append(Task.workspace_id.is_(None))
        if scope_workspace_id is not None:
            conditions.append(Task.workspace_id == scope_workspace_id)
        if scope_project_id is not None:
            conditions.append(Task.project_id == scope_project_id)
        scoped = and_(*conditions)
        active = active_task_filter()

        stmt = select(
            func.count().filter(scoped, Task.status == TaskStatus.PENDING).label("pending"),
            func.count()
            .filter(scoped, Task.status == TaskStatus.IN_PROGRESS)
            .label("in_progress"),
            func.count().filter(scoped, Task.status == TaskStatus.DONE).label("done"),
            func.count().filter(scoped, active, Task.due_date < today).label("overdue"),
            func.count().filter(scoped, active, Task.due_date == today).label("due_today"),
        )
        row = self.db.execute(stmt).one()
        return {
            "pending": row.pending,
            "in_progress": row.in_progress,
            "done": row.done,
            "overdue": row.overdue,
            "due_today": row.due_today,
        }

    def search(
        self,
        *,
        creator_id: uuid.UUID,
        workspace_ids: Sequence[uuid.UUID],
        owner_workspace_ids: Sequence[uuid.UUID] = (),
        member_project_ids: Sequence[uuid.UUID] = (),
        search: str | None,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        workspace_id: uuid.UUID | None,
        project_id: uuid.UUID | None,
        assignee_id: uuid.UUID | None,
        sort_by: TaskSortBy,
        sort_order: TaskSortOrder,
        page: int,
        page_size: int,
    ) -> tuple[list[Task], int]:
        """FR-055 a FR-059 (US8): endpoint central de listagem — mesma
        visibilidade (`visible`) já usada em `count_by_status` (tarefas
        pessoais do próprio usuário + tarefas dos workspaces em
        `workspace_ids`), com busca/filtros/ordenação/paginação combináveis
        numa única consulta parametrizada (evita N+1). Os filtros adicionais
        (`workspace_id`/`project_id`/`assignee_id`) são aplicados em `AND`
        sobre `visible` — filtrar por um workspace do qual o usuário não é
        membro simplesmente não retorna nada, sem precisar de uma checagem
        de autorização separada (FR-059: nunca vaza tarefas fora da
        visibilidade já garantida).

        `priority` é armazenado como `VARCHAR` simples (`native_enum=False`,
        sem ordem nativa no banco) — ordenar por ele com um `ORDER BY`
        ingênuo seria alfabético (`HIGH, LOW, MEDIUM, URGENT`), não
        semântico. Por isso usa uma expressão `CASE` mapeando para a ordem
        `LOW < MEDIUM < HIGH < URGENT` (`data-model.md`), decisão
        documentada aqui por não haver essa definição explícita em nenhum
        documento."""
        visible = _visible_task_condition(
            creator_id=creator_id,
            workspace_ids=workspace_ids,
            owner_workspace_ids=owner_workspace_ids,
            member_project_ids=member_project_ids,
        )

        conditions = [visible]
        if search:
            conditions.append(Task.title.ilike(f"%{search}%"))
        if status is not None:
            conditions.append(Task.status == status)
        if priority is not None:
            conditions.append(Task.priority == priority)
        if workspace_id is not None:
            conditions.append(Task.workspace_id == workspace_id)
        if project_id is not None:
            conditions.append(Task.project_id == project_id)
        if assignee_id is not None:
            conditions.append(Task.assignee_id == assignee_id)

        where_clause = and_(*conditions)

        priority_rank = case(
            (Task.priority == TaskPriority.LOW, 1),
            (Task.priority == TaskPriority.MEDIUM, 2),
            (Task.priority == TaskPriority.HIGH, 3),
            (Task.priority == TaskPriority.URGENT, 4),
        )
        sort_column = {
            TaskSortBy.DUE_DATE: Task.due_date,
            TaskSortBy.PRIORITY: priority_rank,
            TaskSortBy.CREATED_AT: Task.created_at,
        }[sort_by]
        order_expr = sort_column.asc() if sort_order == TaskSortOrder.ASC else sort_column.desc()

        total = self.db.scalar(select(func.count()).select_from(Task).where(where_clause)) or 0

        stmt = (
            select(Task)
            .where(where_clause)
            .order_by(order_expr, Task.id.asc())  # desempate determinístico
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.scalars(stmt))
        return items, total
