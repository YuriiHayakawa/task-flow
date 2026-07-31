import uuid

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.models.task_history_entry import TaskHistoryEntry
from app.models.user import User


class TaskHistoryRepository:
    """Acesso a dados de `TaskHistoryEntry` — nenhuma regra de negócio aqui
    (Constitution III). Quem decide quais campos rastrear e como
    serializá-los é o `TaskService` (T110); este repository apenas persiste
    e consulta."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, entry: TaskHistoryEntry) -> TaskHistoryEntry:
        self.db.add(entry)
        self.db.flush()
        return entry

    def list_by_task(self, task_id: uuid.UUID) -> list[Row]:
        """Junta com `User` para trazer `name`/`email` de quem alterou em
        uma única consulta (evita N+1) — mesmo padrão de
        `CommentRepository`/`AttachmentRepository`. Ordenado por
        `changed_at` **descendente** (contracts/collaboration.md — ao
        contrário de Comments/Checklist/Attachments, aqui o mais recente
        vem primeiro) + `id` asc como desempate determinístico."""
        stmt = (
            select(
                TaskHistoryEntry.id,
                TaskHistoryEntry.field_changed,
                TaskHistoryEntry.old_value,
                TaskHistoryEntry.new_value,
                TaskHistoryEntry.changed_by_id,
                User.name.label("changed_by_name"),
                User.email.label("changed_by_email"),
                TaskHistoryEntry.changed_at,
            )
            .join(User, User.id == TaskHistoryEntry.changed_by_id)
            .where(TaskHistoryEntry.task_id == task_id)
            .order_by(TaskHistoryEntry.changed_at.desc(), TaskHistoryEntry.id.asc())
        )
        return list(self.db.execute(stmt).all())
