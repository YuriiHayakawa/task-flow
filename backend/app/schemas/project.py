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
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
