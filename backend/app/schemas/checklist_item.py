import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChecklistItemCreate(BaseModel):
    """Corpo de `POST /api/v1/tasks/{task_id}/checklist`
    (contracts/collaboration.md) — `task_id` vem do path."""

    description: str = Field(min_length=1, max_length=255)


class ChecklistItemUpdate(BaseModel):
    """Corpo de `PATCH /api/v1/tasks/{task_id}/checklist/{item_id}` — único
    campo suportado (refinamento #7: sem edição textual de `description`
    neste MVP)."""

    is_done: bool


class ChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    description: str
    is_done: bool
    completed_at: datetime | None
