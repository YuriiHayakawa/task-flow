import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums.task_priority import TaskPriority
from app.enums.task_status import TaskStatus


class TaskCreate(BaseModel):
    """Corpo de `POST /api/v1/tasks` (contracts/projects-and-tasks.md).

    `workspace_id`/`project_id` já existem no contrato completo, mas nesta fase
    (US1) só o caminho de tarefa pessoal (ambos ausentes) é processado pelo
    `TaskService` — a validação de workspace/projeto chega na US4 (T072)."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None
    assignee_id: uuid.UUID | None = None
    workspace_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None


class TaskUpdate(BaseModel):
    """Corpo de `PATCH /api/v1/tasks/{task_id}` — "dados operacionais" (plan.md).

    Todos os campos são opcionais (atualização parcial); usar
    `model_dump(exclude_unset=True)` no Service para aplicar somente o que foi
    enviado."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    assignee_id: uuid.UUID | None = None
    workspace_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    assignee_id: uuid.UUID
    creator_id: uuid.UUID
    workspace_id: uuid.UUID | None
    project_id: uuid.UUID | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
