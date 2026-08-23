import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectMemberCreate(BaseModel):
    """Corpo de `POST /api/v1/projects/{project_id}/members` — sem `role`
    (contracts/project-members.md): Membro de Projeto é uma lista flat."""

    user_id: uuid.UUID


class ProjectMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    name: str
    email: str
    joined_at: datetime
