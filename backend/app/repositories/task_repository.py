import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import ColumnElement, and_, false, func, or_, select
from sqlalchemy.orm import Session

from app.enums.task_status import TaskStatus
from app.models.task import Task


def active_task_filter() -> ColumnElement[bool]:
    """Expressão reutilizável de "tarefa ativa" (FR-024, data-model.md):
    qualquer tarefa cujo status seja diferente de `DONE`."""
    return Task.status != TaskStatus.DONE


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

    def list_personal_by_creator(self, creator_id: uuid.UUID) -> list[Task]:
        """Tarefas pessoais (`workspace_id IS NULL`) do próprio criador — nunca
        tarefas pessoais de terceiros (FR-059)."""
        stmt = (
            select(Task)
            .where(Task.creator_id == creator_id, Task.workspace_id.is_(None))
            .order_by(Task.created_at.desc())
        )
        return list(self.db.scalars(stmt))

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
    ) -> dict[str, int]:
        """Contagens do dashboard (FR-047 a FR-050): tarefas pessoais do
        próprio usuário + tarefas dos workspaces em `workspace_ids` (vazio até
        a US3/US4 ativarem a união em T065 — esta consulta não muda, só passa
        a receber uma lista não vazia). "Atrasada"/"vencendo hoje" usam
        `today` já calculado na timezone da aplicação pelo chamador
        (research.md #9), nunca `CURRENT_DATE` do banco (que seria UTC)."""
        visible = or_(
            and_(Task.creator_id == creator_id, Task.workspace_id.is_(None)),
            Task.workspace_id.in_(workspace_ids) if workspace_ids else false(),
        )
        active = active_task_filter()

        stmt = select(
            func.count().filter(visible, Task.status == TaskStatus.PENDING).label("pending"),
            func.count()
            .filter(visible, Task.status == TaskStatus.IN_PROGRESS)
            .label("in_progress"),
            func.count().filter(visible, Task.status == TaskStatus.DONE).label("done"),
            func.count().filter(visible, active, Task.due_date < today).label("overdue"),
            func.count().filter(visible, active, Task.due_date == today).label("due_today"),
        )
        row = self.db.execute(stmt).one()
        return {
            "pending": row.pending,
            "in_progress": row.in_progress,
            "done": row.done,
            "overdue": row.overdue,
            "due_today": row.due_today,
        }
