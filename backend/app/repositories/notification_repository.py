import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.enums.task_status import TaskStatus
from app.models.notification import Notification
from app.models.task import Task


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

    def get_by_recipient_and_id(
        self, recipient_id: uuid.UUID, notification_id: uuid.UUID
    ) -> Notification | None:
        """Escopado por `recipient_id` E `notification_id` juntos — mesmo
        padrão de `ChecklistItemRepository.get_by_task_and_id`/
        `AttachmentRepository.get_by_task_and_id`: uma notificação de outro
        usuário nunca é encontrada, mesmo com o `notification_id` certo
        (contracts/dashboard-and-notifications.md — tratado como `404`, não
        `403`, mesmo padrão de segurança do resto da API)."""
        stmt = select(Notification).where(
            Notification.recipient_id == recipient_id, Notification.id == notification_id
        )
        return self.db.scalars(stmt).first()

    def mark_all_read(self, recipient_id: uuid.UUID) -> int:
        """`PATCH /api/v1/notifications/read-all` — marca todas as não lidas
        do destinatário; retorna a contagem efetivamente alterada (`updated`
        na resposta). `synchronize_session=False`: nenhum objeto ORM desta
        entidade precisa permanecer sincronizado em memória após esta
        chamada neste fluxo."""
        stmt = (
            update(Notification)
            .where(Notification.recipient_id == recipient_id, Notification.is_read.is_(False))
            .values(is_read=True)
            .execution_options(synchronize_session=False)
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount or 0

    def list_due_soon_candidates(self, *, now: datetime, window_hours: int) -> list[Task]:
        """Consulta de elegibilidade a `DUE_SOON` (T103, research.md #2) —
        atribuída a este repository (não a `TaskRepository`) por instrução
        explícita de `tasks.md`: "estender
        backend/app/repositories/notification_repository.py com consultas
        de tarefas elegíveis a DUE_SOON".

        Critérios (todos combinados em `AND`): `status != DONE`; `due_date`
        não nulo; `due_date` dentro de `window_hours` à frente de `now`
        (sem limite inferior — cobre tanto "vencendo hoje" quanto tarefas já
        atrasadas e ainda não notificadas); `due_soon_notified_for IS
        DISTINCT FROM due_date` (idempotência — uma tarefa já notificada
        para o `due_date` atual não é reselecionada)."""
        threshold = (now + timedelta(hours=window_hours)).date()
        stmt = (
            select(Task)
            .where(
                Task.status != TaskStatus.DONE,
                Task.due_date.is_not(None),
                Task.due_date <= threshold,
                Task.due_soon_notified_for.is_distinct_from(Task.due_date),
            )
            .order_by(Task.id.asc())
        )
        return list(self.db.scalars(stmt))
