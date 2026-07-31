import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskHistoryEntryRead(BaseModel):
    """`changed_by_id`/`changed_by_name`/`changed_by_email` achatados —
    mesmo padrão de `CommentRead`/`AttachmentRead` (o contrato original lista
    apenas `changed_by`)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    field_changed: str
    old_value: str | None
    new_value: str | None
    changed_by_id: uuid.UUID
    changed_by_name: str
    changed_by_email: str
    changed_at: datetime
