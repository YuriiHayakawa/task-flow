import uuid
from datetime import datetime

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.enums.notification_type import NotificationType
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.notification import NotificationRead


class NotificationService:
    """FR-039/FR-040 (US11)."""

    def __init__(
        self, notification_repository: NotificationRepository, task_repository: TaskRepository
    ) -> None:
        self.notification_repository = notification_repository
        self.task_repository = task_repository
        self.db = notification_repository.db

    def list_notifications(
        self, recipient_id: uuid.UUID, is_read: bool | None
    ) -> list[NotificationRead]:
        notifications = self.notification_repository.list_by_recipient(recipient_id, is_read)
        return [NotificationRead.model_validate(n, from_attributes=True) for n in notifications]

    def mark_as_read(self, recipient_id: uuid.UUID, notification_id: uuid.UUID) -> NotificationRead:
        """Idempotente — marcar como lida uma notificação já lida não é
        erro. Notificação de outro destinatário nunca é encontrada
        (`get_by_recipient_and_id`), resultando em `404`, nunca `403`."""
        notification = self.notification_repository.get_by_recipient_and_id(
            recipient_id, notification_id
        )
        if notification is None:
            raise NotFoundError("Notificação não encontrada.")

        self.notification_repository.mark_read(notification)
        self.db.commit()
        self.db.refresh(notification)
        return NotificationRead.model_validate(notification, from_attributes=True)

    def mark_all_as_read(self, recipient_id: uuid.UUID) -> int:
        updated = self.notification_repository.mark_all_read(recipient_id)
        self.db.commit()
        return updated

    def generate_due_soon_notifications(self, now: datetime) -> int:
        """T104 (US11), research.md #2: para cada tarefa elegível (ver
        `NotificationRepository.list_due_soon_candidates`), cria uma
        `Notification` tipo `DUE_SOON` para o responsável e atualiza
        `due_soon_notified_for = due_date` — sempre os dois juntos, nunca um
        sem o outro (idempotência do job).

        **Não faz `commit()`** — diferente do resto desta classe. Quem
        chama este método (`run_due_soon_job`, Bloco 3) já opera dentro de
        uma `Session`/conexão dedicada da própria execução do job
        (advisory lock), e é ela quem decide commit (sucesso) ou rollback
        (exceção), conforme o fluxo de `research.md` #2 — commitar aqui
        romperia esse controle transacional externo."""
        candidates = self.notification_repository.list_due_soon_candidates(
            now=now, window_hours=settings.DUE_SOON_WINDOW_HOURS
        )

        created = 0
        for task in candidates:
            notification = Notification(
                recipient_id=task.assignee_id,
                task_id=task.id,
                type=NotificationType.DUE_SOON,
                title="Prazo se aproximando",
                message=f'A tarefa "{task.title}" está com prazo próximo ou vencido.',
            )
            self.notification_repository.create(notification)
            task.due_soon_notified_for = task.due_date
            self.task_repository.update(task)
            created += 1

        return created
