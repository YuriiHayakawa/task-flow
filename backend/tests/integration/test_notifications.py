"""T100 [US11] — notificações in-app via HTTP: listagem (com filtro por
`is_read`), marcação individual (idempotente) e marcação em massa,
isolamento por destinatário.

Cobre: FR-039, FR-040, contracts/dashboard-and-notifications.md
(`GET /notifications`, `PATCH .../{id}/read`, `PATCH .../read-all`)."""

import uuid
from datetime import datetime, timedelta, timezone

from app.enums.notification_type import NotificationType
from app.models.notification import Notification


def _make_notification(
    db_session,
    recipient,
    *,
    type_=NotificationType.NEW_COMMENT,
    title="Título",
    message="Mensagem",
    task_id=None,
    is_read=False,
):
    notification = Notification(
        recipient_id=recipient.id,
        task_id=task_id,
        type=type_,
        title=title,
        message=message,
        is_read=is_read,
    )
    db_session.add(notification)
    db_session.flush()
    return notification


# --- GET /notifications --------------------------------------------------------


def test_list_notifications_empty(client, make_user, auth_headers):
    user = make_user()

    response = client.get("/api/v1/notifications", headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_list_notifications_returns_own_only(client, make_user, auth_headers, db_session):
    user = make_user()
    someone_else = make_user(email="someone-else-notifications@example.com")
    _make_notification(db_session, user, title="Minha notificação")
    _make_notification(db_session, someone_else, title="Notificação de outro usuário")

    response = client.get("/api/v1/notifications", headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "Minha notificação"


def test_list_notifications_ordered_by_created_at_descending(
    client, make_user, auth_headers, db_session
):
    user = make_user()
    now = datetime.now(timezone.utc)
    older = _make_notification(db_session, user, title="Mais antiga")
    newer = _make_notification(db_session, user, title="Mais recente")
    older.created_at = now - timedelta(minutes=5)
    newer.created_at = now
    db_session.flush()

    response = client.get("/api/v1/notifications", headers=auth_headers(user))

    body = response.json()
    assert [item["title"] for item in body["items"]] == ["Mais recente", "Mais antiga"]


def test_list_notifications_filters_by_is_read_true(client, make_user, auth_headers, db_session):
    user = make_user()
    _make_notification(db_session, user, title="Lida", is_read=True)
    _make_notification(db_session, user, title="Não lida", is_read=False)

    response = client.get("/api/v1/notifications?is_read=true", headers=auth_headers(user))

    body = response.json()
    assert [item["title"] for item in body["items"]] == ["Lida"]


def test_list_notifications_filters_by_is_read_false(client, make_user, auth_headers, db_session):
    user = make_user()
    _make_notification(db_session, user, title="Lida", is_read=True)
    _make_notification(db_session, user, title="Não lida", is_read=False)

    response = client.get("/api/v1/notifications?is_read=false", headers=auth_headers(user))

    body = response.json()
    assert [item["title"] for item in body["items"]] == ["Não lida"]


def test_list_notifications_response_shape(client, make_user, make_task, auth_headers, db_session):
    user = make_user()
    task = make_task(creator=user)
    _make_notification(
        db_session,
        user,
        type_=NotificationType.DUE_SOON,
        title="Prazo próximo",
        message="Sua tarefa vence em breve.",
        task_id=task.id,
    )

    response = client.get("/api/v1/notifications", headers=auth_headers(user))

    item = response.json()["items"][0]
    assert item["type"] == "DUE_SOON"
    assert item["title"] == "Prazo próximo"
    assert item["message"] == "Sua tarefa vence em breve."
    assert item["task_id"] == str(task.id)
    assert item["is_read"] is False
    assert item["created_at"] is not None


# --- PATCH /notifications/{id}/read --------------------------------------------


def test_mark_notification_read_success(client, make_user, auth_headers, db_session):
    user = make_user()
    notification = _make_notification(db_session, user, is_read=False)

    response = client.patch(
        f"/api/v1/notifications/{notification.id}/read", headers=auth_headers(user)
    )

    assert response.status_code == 200
    assert response.json()["is_read"] is True


def test_mark_notification_read_is_idempotent(client, make_user, auth_headers, db_session):
    user = make_user()
    notification = _make_notification(db_session, user, is_read=True)

    response = client.patch(
        f"/api/v1/notifications/{notification.id}/read", headers=auth_headers(user)
    )

    assert response.status_code == 200
    assert response.json()["is_read"] is True


def test_mark_notification_read_of_another_user_returns_404(
    client, make_user, auth_headers, db_session
):
    owner = make_user()
    outsider = make_user(email="outsider-mark-read@example.com")
    notification = _make_notification(db_session, owner)

    response = client.patch(
        f"/api/v1/notifications/{notification.id}/read", headers=auth_headers(outsider)
    )

    assert response.status_code == 404


def test_mark_notification_read_nonexistent_returns_404(client, make_user, auth_headers):
    user = make_user()

    response = client.patch(
        f"/api/v1/notifications/{uuid.uuid4()}/read", headers=auth_headers(user)
    )

    assert response.status_code == 404


# --- PATCH /notifications/read-all ---------------------------------------------


def test_mark_all_read_updates_only_unread_of_recipient(
    client, make_user, auth_headers, db_session
):
    user = make_user()
    someone_else = make_user(email="someone-else-read-all@example.com")
    _make_notification(db_session, user, title="Não lida 1", is_read=False)
    _make_notification(db_session, user, title="Não lida 2", is_read=False)
    _make_notification(db_session, user, title="Já lida", is_read=True)
    other_unread = _make_notification(db_session, someone_else, title="De outro usuário", is_read=False)

    response = client.patch("/api/v1/notifications/read-all", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json() == {"updated": 2}
    # a notificação de outro usuário não foi alterada:
    db_session.refresh(other_unread)
    assert other_unread.is_read is False


def test_mark_all_read_second_call_updates_zero(client, make_user, auth_headers, db_session):
    user = make_user()
    _make_notification(db_session, user, is_read=False)

    first_response = client.patch("/api/v1/notifications/read-all", headers=auth_headers(user))
    second_response = client.patch("/api/v1/notifications/read-all", headers=auth_headers(user))

    assert first_response.json() == {"updated": 1}
    assert second_response.json() == {"updated": 0}


def test_mark_all_read_no_notifications_returns_zero(client, make_user, auth_headers):
    user = make_user()

    response = client.patch("/api/v1/notifications/read-all", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json() == {"updated": 0}


# --- Regressão -----------------------------------------------------------------


def test_comments_endpoint_still_works(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/comments", headers=auth_headers(owner))

    assert response.status_code == 200
