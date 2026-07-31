import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums.notification_type import NotificationType


class NotificationRead(BaseModel):
    """Resposta de `GET /api/v1/notifications`
    (contracts/dashboard-and-notifications.md)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    task_id: uuid.UUID | None
    is_read: bool
    created_at: datetime
