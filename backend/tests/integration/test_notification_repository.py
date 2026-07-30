"""T082 [US6] — validação isolada de `NotificationRepository`, sem Service/
Routes: persistência crua, sem decisão de destinatários/dedup (Constitution
III). `list_by_recipient`/`mark_read` não têm consumidor nesta fase — testados
aqui apenas como comportamento de repository, conforme `tasks.md` os atribui
explicitamente a T082 (consumidor pleno chega na Fase 13/US11)."""

from app.enums.notification_type import NotificationType
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository


def test_create_new_comment_notification_persists_via_flush_not_commit(
    db_session, make_user, make_workspace, make_task
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = NotificationRepository(db_session)

    notification = repo.create(
        Notification(
            recipient_id=owner.id,
            task_id=task.id,
            type=NotificationType.NEW_COMMENT,
            title="Novo comentário",
            message="Alguém comentou na sua tarefa.",
        )
    )

    assert notification.id is not None
    assert notification.created_at is not None
    assert notification.is_read is False


def test_create_persists_all_expected_fields(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = NotificationRepository(db_session)

    notification = repo.create(
        Notification(
            recipient_id=owner.id,
            task_id=task.id,
            type=NotificationType.NEW_COMMENT,
            title="Novo comentário",
            message="Fulano comentou: 'Olá'",
        )
    )
    db_session.flush()
    db_session.refresh(notification)

    assert notification.recipient_id == owner.id
    assert notification.task_id == task.id
    assert notification.type == NotificationType.NEW_COMMENT
    assert notification.title == "Novo comentário"
    assert notification.message == "Fulano comentou: 'Olá'"
    assert notification.is_read is False


def test_list_by_recipient_returns_only_own_notifications(
    db_session, make_user, make_workspace, make_task
):
    owner = make_user()
    other = make_user(email="other-notif@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = NotificationRepository(db_session)
    repo.create(
        Notification(
            recipient_id=owner.id, task_id=task.id, type=NotificationType.NEW_COMMENT,
            title="Para o owner", message="msg",
        )
    )
    repo.create(
        Notification(
            recipient_id=other.id, task_id=task.id, type=NotificationType.NEW_COMMENT,
            title="Para o other", message="msg",
        )
    )

    rows = repo.list_by_recipient(owner.id)

    assert len(rows) == 1
    assert rows[0].recipient_id == owner.id
    assert rows[0].title == "Para o owner"


def test_list_by_recipient_filters_by_is_read(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = NotificationRepository(db_session)
    unread = repo.create(
        Notification(
            recipient_id=owner.id, task_id=task.id, type=NotificationType.NEW_COMMENT,
            title="Não lida", message="msg",
        )
    )
    read = repo.create(
        Notification(
            recipient_id=owner.id, task_id=task.id, type=NotificationType.NEW_COMMENT,
            title="Lida", message="msg",
        )
    )
    repo.mark_read(read)

    unread_rows = repo.list_by_recipient(owner.id, is_read=False)
    read_rows = repo.list_by_recipient(owner.id, is_read=True)

    assert [row.id for row in unread_rows] == [unread.id]
    assert [row.id for row in read_rows] == [read.id]


def test_list_by_recipient_ordered_by_created_at_descending(
    db_session, make_user, make_workspace, make_task
):
    from datetime import datetime, timedelta, timezone

    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = NotificationRepository(db_session)
    now = datetime.now(timezone.utc)
    older = repo.create(
        Notification(
            recipient_id=owner.id, task_id=task.id, type=NotificationType.NEW_COMMENT,
            title="Mais antiga", message="msg",
        )
    )
    newer = repo.create(
        Notification(
            recipient_id=owner.id, task_id=task.id, type=NotificationType.NEW_COMMENT,
            title="Mais recente", message="msg",
        )
    )
    db_session.flush()
    older.created_at = now - timedelta(minutes=5)
    newer.created_at = now
    db_session.flush()

    rows = repo.list_by_recipient(owner.id)

    assert [row.id for row in rows] == [newer.id, older.id]


def test_mark_read_is_idempotent(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = NotificationRepository(db_session)
    notification = repo.create(
        Notification(
            recipient_id=owner.id, task_id=task.id, type=NotificationType.NEW_COMMENT,
            title="T", message="msg",
        )
    )

    repo.mark_read(notification)
    assert notification.is_read is True

    repo.mark_read(notification)  # chamar de novo não deve falhar nem mudar nada
    assert notification.is_read is True


def test_repository_does_not_decide_recipients_or_dedupe() -> None:
    """Confirmação estática (não um teste de comportamento): `create` recebe
    a `Notification` já pronta — quem decide destinatários (responsável +
    `TaskMember`, exceto autor) e deduplica é o `CommentService` (Bloco 2),
    nunca este repository. `create` não tem nenhum parâmetro de
    'participantes' ou 'task' para calcular isso."""
    import inspect

    signature = inspect.signature(NotificationRepository.create)
    assert list(signature.parameters) == ["self", "notification"]
