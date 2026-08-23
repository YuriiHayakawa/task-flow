import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """Corpo de `POST /api/v1/workspaces/{workspace_id}/projects`
    (contracts/projects-and-tasks.md). `workspace_id` vem do path, não do corpo."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectUpdate(BaseModel):
    """Corpo de `PATCH /api/v1/projects/{project_id}` — ambos opcionais."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class ProjectRead(BaseModel):
    """`is_member` é contextual (depende de quem pergunta) — sempre
    construído explicitamente pelo Service (`ProjectService.to_read`), nunca
    via `from_attributes` direto do ORM (mesmo padrão de
    `WorkspaceRead.my_role`, 003-membros-projeto)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    is_member: bool
    created_at: datetime
    updated_at: datetime
