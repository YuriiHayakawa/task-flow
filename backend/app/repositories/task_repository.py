import uuid

from sqlalchemy import ColumnElement, select
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
