import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification


class NotificationRepository:
    """Acesso a dados de `Notification` — nenhuma regra de negócio aqui
    (Constitution III). Quem decide destinatários, exclui o autor, ou
    deduplica é o `CommentService` (US6) — aqui, na T082 — e futuramente
    `NotificationService`/`TaskService` (US11); este repository apenas
    persiste e consulta.

    `list_by_recipient`/`mark_read` não têm consumidor nesta fase (T082 é o
    único ponto da Fase 8 que usa `create`) — implementados agora porque
    `tasks.md` os atribui explicitamente a esta tarefa: "Criar
    backend/app/repositories/notification_repository.py (`create`,
    `list_by_recipient`, `mark_read` — primeiro consumidor é `NEW_COMMENT`,
    estendido na US11)". A Fase 13/US11 (T103–T107) constrói
    `NotificationService`/`GET /notifications`/`PATCH .../read` sobre eles,
    sem precisar alterar esta classe."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.flush()
        return notification

    def list_by_recipient(
        self, recipient_id: uuid.UUID, is_read: bool | None = None
    ) -> list[Notification]:
        """Formato alinhado a `GET /api/v1/notifications`
        (contracts/dashboard-and-notifications.md, Fase 13): filtro opcional
        por `is_read`, ordenado por `created_at` desc."""
        stmt = select(Notification).where(Notification.recipient_id == recipient_id)
        if is_read is not None:
            stmt = stmt.where(Notification.is_read == is_read)
        stmt = stmt.order_by(Notification.created_at.desc())
        return list(self.db.scalars(stmt))

    def mark_read(self, notification: Notification) -> Notification:
        """Alinhado a `PATCH /api/v1/notifications/{id}/read` (Fase 13) —
        idempotente (setar `True` quando já é `True` não é um erro)."""
        notification.is_read = True
        self.db.flush()
        return notification
