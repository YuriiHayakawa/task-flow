import uuid

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.models.task_member import TaskMember
from app.models.user import User


class TaskMemberRepository:
    """Acesso a dados de `TaskMember` — nenhuma regra de negócio aqui
    (Constitution III). Lista apenas participantes EXPLICITAMENTE
    adicionados; o responsável (assignee) implícito (FR-033) é composto pelo
    `TaskMemberService`, nunca aqui — nenhuma linha é fabricada para
    representá-lo."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, member: TaskMember) -> TaskMember:
        self.db.add(member)
        self.db.flush()
        return member

    def delete(self, member: TaskMember) -> None:
        self.db.delete(member)
        self.db.flush()

    def get_by_task_and_user(self, task_id: uuid.UUID, user_id: uuid.UUID) -> TaskMember | None:
        stmt = select(TaskMember).where(
            TaskMember.task_id == task_id, TaskMember.user_id == user_id
        )
        return self.db.scalars(stmt).first()

    def exists(self, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = select(TaskMember.id).where(
            TaskMember.task_id == task_id, TaskMember.user_id == user_id
        )
        return self.db.scalars(stmt).first() is not None

    def list_by_task(self, task_id: uuid.UUID) -> list[Row]:
        """Junta com `User` para trazer `name`/`email` em uma única consulta
        (evita N+1); `created_at` já sai rotulado como `added_at`, o nome de
        campo exposto por `TaskMemberRead`. Retorna somente participantes
        explícitos desta tarefa — nunca de outra (`WHERE task_id`)."""
        stmt = (
            select(
                TaskMember.user_id,
                User.name,
                User.email,
                TaskMember.created_at.label("added_at"),
            )
            .join(User, User.id == TaskMember.user_id)
            .where(TaskMember.task_id == task_id)
            .order_by(TaskMember.created_at)
        )
        return list(self.db.execute(stmt).all())
