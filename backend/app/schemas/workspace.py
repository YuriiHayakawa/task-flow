import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.enums.workspace_role import WorkspaceRole


class WorkspaceCreate(BaseModel):
    """Corpo de `POST /api/v1/workspaces` (contracts/workspaces.md)."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class WorkspaceUpdate(BaseModel):
    """Corpo de `PATCH /api/v1/workspaces/{workspace_id}` — ambos opcionais."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class WorkspaceRead(BaseModel):
    """`my_role` é contextual (depende de quem pergunta) — sempre construído
    explicitamente pelo Service, nunca via `from_attributes` direto do ORM."""

    id: uuid.UUID
    name: str
    description: str | None
    my_role: WorkspaceRole
    created_at: datetime
    updated_at: datetime
