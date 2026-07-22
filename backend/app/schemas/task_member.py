import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskMemberCreate(BaseModel):
    """Corpo de `POST /api/v1/tasks/{task_id}/members`
    (contracts/projects-and-tasks.md) — `task_id` vem do path."""

    user_id: uuid.UUID


class TaskMemberRead(BaseModel):
    """`added_at` é `None` para o responsável (assignee) quando ele não tem
    uma linha própria em `TaskMember` — participante implícito (FR-033),
    composto pelo Service, nunca por este schema nem pelo repository."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    name: str
    email: str
    added_at: datetime | None
