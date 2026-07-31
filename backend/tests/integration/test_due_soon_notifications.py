"""T101 [US11] — `NotificationService.generate_due_soon_notifications`:
seleção de tarefas elegíveis a `DUE_SOON`, idempotência via
`due_soon_notified_for`, janela de detecção (`DUE_SOON_WINDOW_HOURS`).

Cobre a parte das regras de `research.md` #2 relativa à consulta/geração em
si (Bloco 2 desta fase). As regras sobre reset de `due_soon_notified_for`
disparado por `TaskService.update` (mudança de `due_date`, reabertura sem
alterar prazo) pertencem ao Bloco 4 (T106), onde `update()` ganha essa
lógica — testadas em `test_task_service.py`/testes de integração de
`TASK_CHANGED`, não aqui."""

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.enums.notification_type import NotificationType
from app.enums.task_status import TaskStatus
from app.repositories.notification_repository import NotificationRepository
from app.repositories.task_repository import TaskRepository
from app.services.notification_service import NotificationService


def _service(db_session) -> NotificationService:
    return NotificationService(NotificationRepository(db_session), TaskRepository(db_session))


_NOW = datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc)


def test_task_without_due_date_is_never_selected(db_session, make_user, make_task):
    user = make_user()
    make_task(creator=user, due_date=None)

    created = _service(db_session).generate_due_soon_notifications(now=_NOW)

    assert created == 0


def test_done_task_is_never_selected_even_within_window(db_session, make_user, make_task):
    user = make_user()
    make_task(creator=user, due_date=_NOW.date(), status=TaskStatus.DONE)

    created = _service(db_session).generate_due_soon_notifications(now=_NOW)

    assert created == 0


def test_task_due_today_is_selected(db_session, make_user, make_task):
    user = make_user()
    task = make_task(creator=user, due_date=_NOW.date())

    created = _service(db_session).generate_due_soon_notifications(now=_NOW)

    assert created == 1
    db_session.refresh(task)
    assert task.due_soon_notified_for == task.due_date


def test_task_overdue_is_selected(db_session, make_user, make_task):
    """Janela cobre tanto "vencendo hoje" quanto tarefas já atrasadas e
    ainda não notificadas (contracts/dashboard-and-notifications.md)."""
    user = make_user()
    make_task(creator=user, due_date=(_NOW - timedelta(days=10)).date())

    created = _service(db_session).generate_due_soon_notifications(now=_NOW)

    assert created == 1


def test_task_at_exact_window_boundary_is_selected(db_session, make_user, make_task):
    user = make_user()
    boundary_date = (_NOW + timedelta(hours=settings.DUE_SOON_WINDOW_HOURS)).date()
    make_task(creator=user, due_date=boundary_date)

    created = _service(db_session).generate_due_soon_notifications(now=_NOW)

    assert created == 1


def test_task_beyond_window_is_not_selected(db_session, make_user, make_task):
    user = make_user()
    beyond_window_date = (_NOW + timedelta(hours=settings.DUE_SOON_WINDOW_HOURS + 48)).date()
    make_task(creator=user, due_date=beyond_window_date)

    created = _service(db_session).generate_due_soon_notifications(now=_NOW)

    assert created == 0


def test_creates_notification_and_updates_due_soon_notified_for_together(
    db_session, make_user, make_task
):
    user = make_user()
    task = make_task(creator=user, due_date=_NOW.date())

    _service(db_session).generate_due_soon_notifications(now=_NOW)

    db_session.refresh(task)
    assert task.due_soon_notified_for == task.due_date

    from app.repositories.notification_repository import NotificationRepository as _Repo

    notifications = _Repo(db_session).list_by_recipient(task.assignee_id)
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.type == NotificationType.DUE_SOON
    assert notification.task_id == task.id
    assert notification.recipient_id == task.assignee_id


def test_repeated_execution_does_not_duplicate(db_session, make_user, make_task):
    user = make_user()
    make_task(creator=user, due_date=_NOW.date())
    service = _service(db_session)

    first_run = service.generate_due_soon_notifications(now=_NOW)
    second_run = service.generate_due_soon_notifications(now=_NOW)

    assert first_run == 1
    assert second_run == 0


def test_recipient_is_assignee_not_creator(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    from app.enums.workspace_role import WorkspaceRole

    creator = make_user()
    assignee = make_user(email="assignee-due-soon@example.com")
    workspace = make_workspace(owner=creator)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, assignee=assignee, workspace=workspace, due_date=_NOW.date())

    _service(db_session).generate_due_soon_notifications(now=_NOW)

    notifications = NotificationRepository(db_session).list_by_recipient(assignee.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_id == assignee.id

    creator_notifications = NotificationRepository(db_session).list_by_recipient(creator.id)
    assert creator_notifications == []


def test_personal_task_is_eligible(db_session, make_user, make_task):
    user = make_user()
    make_task(creator=user, due_date=_NOW.date())

    created = _service(db_session).generate_due_soon_notifications(now=_NOW)

    assert created == 1


def test_multiple_eligible_tasks_all_notified_in_one_run(db_session, make_user, make_task):
    user = make_user()
    make_task(creator=user, title="Tarefa 1", due_date=_NOW.date())
    make_task(creator=user, title="Tarefa 2", due_date=(_NOW - timedelta(days=1)).date())
    make_task(creator=user, title="Tarefa 3", due_date=None)  # não elegível

    created = _service(db_session).generate_due_soon_notifications(now=_NOW)

    assert created == 2
