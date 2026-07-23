"""T080/T084 [US6] — comentários em tarefas via HTTP: visibilidade,
colaboração restrita a participantes, notificações NEW_COMMENT, atomicidade.

Cobre: FR-027 a FR-029, FR-039, contracts/collaboration.md
(`GET/POST /tasks/{task_id}/comments`)."""

import uuid

import pytest

from app.enums.notification_type import NotificationType
from app.enums.workspace_role import WorkspaceRole
from app.models.comment import Comment
from app.models.notification import Notification
from app.models.task_member import TaskMember
from app.repositories.notification_repository import NotificationRepository


# --- GET /tasks/{task_id}/comments --------------------------------------------


def test_list_comments_empty(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/comments", headers=auth_headers(owner))

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_list_comments_multiple_in_order(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    headers = auth_headers(owner)
    client.post(f"/api/v1/tasks/{task.id}/comments", json={"content": "Primeiro"}, headers=headers)
    client.post(f"/api/v1/tasks/{task.id}/comments", json={"content": "Segundo"}, headers=headers)

    response = client.get(f"/api/v1/tasks/{task.id}/comments", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [c["content"] for c in body["items"]] == ["Primeiro", "Segundo"]


def test_list_comments_flattened_author_fields(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user(name="Dona Owner", email="owner-list-comment@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    headers = auth_headers(owner)
    client.post(f"/api/v1/tasks/{task.id}/comments", json={"content": "Olá"}, headers=headers)

    response = client.get(f"/api/v1/tasks/{task.id}/comments", headers=headers)

    item = response.json()["items"][0]
    assert set(item.keys()) == {"id", "author_id", "author_name", "author_email", "content", "created_at"}
    assert item["author_id"] == str(owner.id)
    assert item["author_name"] == "Dona Owner"
    assert item["author_email"] == "owner-list-comment@example.com"


def test_list_comments_any_workspace_member_can_view(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    member = make_user(email="member-list-comment@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/comments", headers=auth_headers(member))

    assert response.status_code == 200


def test_list_comments_participant_can_view(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    participant = make_user(email="participant-list-comment@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    response = client.get(f"/api/v1/tasks/{task.id}/comments", headers=auth_headers(participant))

    assert response.status_code == 200


def test_list_comments_owner_admin_can_view_as_member(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    admin = make_user(email="admin-list-comment@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    task = make_task(creator=owner, workspace=workspace)

    response_owner = client.get(f"/api/v1/tasks/{task.id}/comments", headers=auth_headers(owner))
    response_admin = client.get(f"/api/v1/tasks/{task.id}/comments", headers=auth_headers(admin))

    assert response_owner.status_code == 200
    assert response_admin.status_code == 200


def test_list_comments_outsider_returns_404(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    outsider = make_user(email="outsider-list-comment@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/comments", headers=auth_headers(outsider))

    assert response.status_code == 404


def test_list_comments_other_workspace_member_returns_404(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    workspace_a = make_workspace(owner=owner, name="WS A")
    workspace_b = make_workspace(owner=owner, name="WS B")
    member_b = make_user(email="member-b-list-comment@example.com")
    add_workspace_member(workspace=workspace_b, user=member_b, role=WorkspaceRole.MEMBER)
    task_in_a = make_task(creator=owner, workspace=workspace_a)

    response = client.get(f"/api/v1/tasks/{task_in_a.id}/comments", headers=auth_headers(member_b))

    assert response.status_code == 404


def test_list_comments_personal_task_creator_returns_200(
    client, make_user, make_task, auth_headers
):
    creator = make_user()
    task = make_task(creator=creator)

    response = client.get(f"/api/v1/tasks/{task.id}/comments", headers=auth_headers(creator))

    assert response.status_code == 200


def test_list_comments_personal_task_other_user_returns_404(
    client, make_user, make_task, auth_headers
):
    creator = make_user()
    other = make_user(email="other-personal-list-comment@example.com")
    task = make_task(creator=creator)

    response = client.get(f"/api/v1/tasks/{task.id}/comments", headers=auth_headers(other))

    assert response.status_code == 404


def test_list_comments_nonexistent_task_returns_404(client, make_user, auth_headers):
    user = make_user()

    response = client.get(f"/api/v1/tasks/{uuid.uuid4()}/comments", headers=auth_headers(user))

    assert response.status_code == 404


# --- POST /tasks/{task_id}/comments --------------------------------------------


def test_create_comment_assignee_success(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    assignee = make_user(email="assignee-post-comment@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"content": "Comentário do responsável"},
        headers=auth_headers(assignee),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["content"] == "Comentário do responsável"
    assert body["author_id"] == str(assignee.id)


def test_create_comment_explicit_task_member_success(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    participant = make_user(email="participant-post-comment@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    response = client.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"content": "Comentário do participante"},
        headers=auth_headers(participant),
    )

    assert response.status_code == 201


def test_create_comment_personal_task_creator_success(client, make_user, make_task, auth_headers):
    creator = make_user()
    task = make_task(creator=creator)

    response = client.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"content": "Comentário pessoal"},
        headers=auth_headers(creator),
    )

    assert response.status_code == 201
    assert response.json()["author_id"] == str(creator.id)


def test_create_comment_plain_member_forbidden(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    plain_member = make_user(email="plain-member-post-comment@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"content": "Não deveria funcionar"},
        headers=auth_headers(plain_member),
    )

    assert response.status_code == 403


def test_create_comment_owner_admin_not_participant_forbidden(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    admin = make_user(email="admin-post-comment@example.com")
    creator = make_user(email="creator-post-comment@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    response_owner = client.post(
        f"/api/v1/tasks/{task.id}/comments", json={"content": "X"}, headers=auth_headers(owner)
    )
    response_admin = client.post(
        f"/api/v1/tasks/{task.id}/comments", json={"content": "X"}, headers=auth_headers(admin)
    )

    assert response_owner.status_code == 403
    assert response_admin.status_code == 403


def test_create_comment_creator_not_participant_forbidden(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    """Criador de tarefa de workspace só comenta se também for responsável
    ou participante explícito — não apenas por ser criador."""
    owner = make_user()
    creator = make_user(email="creator-not-participant@example.com")
    assignee = make_user(email="assignee-not-creator@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, assignee=assignee, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/comments", json={"content": "X"}, headers=auth_headers(creator)
    )

    assert response.status_code == 403


def test_create_comment_outsider_returns_404(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    outsider = make_user(email="outsider-post-comment@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/comments", json={"content": "X"}, headers=auth_headers(outsider)
    )

    assert response.status_code == 404


def test_create_comment_empty_content_returns_422(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/comments", json={"content": ""}, headers=auth_headers(owner)
    )

    assert response.status_code == 422


def test_create_comment_whitespace_only_content_returns_422(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/comments", json={"content": "     "}, headers=auth_headers(owner)
    )

    assert response.status_code == 422


def test_create_comment_content_stripped(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"content": "   com espaços nas pontas   "},
        headers=auth_headers(owner),
    )

    assert response.status_code == 201
    assert response.json()["content"] == "com espaços nas pontas"


def test_create_comment_author_id_comes_from_token_not_body(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    assignee = make_user(email="assignee-author-token@example.com")
    someone_else = make_user(email="someone-else-author@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"content": "Comentário", "author_id": str(someone_else.id)},
        headers=auth_headers(assignee),
    )

    assert response.status_code == 201
    assert response.json()["author_id"] == str(assignee.id)  # nunca someone_else


def test_create_comment_nonexistent_task_returns_404(client, make_user, auth_headers):
    user = make_user()

    response = client.post(
        f"/api/v1/tasks/{uuid.uuid4()}/comments", json={"content": "X"}, headers=auth_headers(user)
    )

    assert response.status_code == 404


def test_create_comment_response_has_exact_contract_fields(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/comments", json={"content": "X"}, headers=auth_headers(owner)
    )

    assert set(response.json().keys()) == {
        "id", "author_id", "author_name", "author_email", "content", "created_at",
    }


# --- Notificações via POST -----------------------------------------------------


def test_create_comment_notifies_assignee_and_participants_excluding_author(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    assignee = make_user(email="assignee-notif@example.com")
    participant = make_user(email="participant-notif@example.com")
    author = make_user(email="author-notif@example.com")  # participante explícito, é quem comenta
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=author, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.add(TaskMember(task_id=task.id, user_id=author.id))
    db_session.flush()

    response = client.post(
        f"/api/v1/tasks/{task.id}/comments", json={"content": "Olá"}, headers=auth_headers(author)
    )
    assert response.status_code == 201

    notifications = (
        db_session.query(Notification).filter(Notification.task_id == task.id).all()
    )
    recipients = {n.recipient_id for n in notifications}
    assert recipients == {assignee.id, participant.id}
    assert author.id not in recipients  # autor nunca recebe


def test_create_comment_owner_admin_not_participant_not_notified(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    admin = make_user(email="admin-not-notified@example.com")
    assignee = make_user(email="assignee-notif-2@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=owner.id))
    db_session.flush()

    client.post(f"/api/v1/tasks/{task.id}/comments", json={"content": "Olá"}, headers=auth_headers(owner))

    notifications = db_session.query(Notification).filter(Notification.task_id == task.id).all()
    recipients = {n.recipient_id for n in notifications}
    assert admin.id not in recipients
    assert recipients == {assignee.id}


def test_create_comment_dedup_assignee_also_explicit_member(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    assignee = make_user(email="assignee-dedup@example.com")
    author = make_user(email="author-dedup@example.com")  # participante explícito separado
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=author, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=assignee.id))  # dado legado: assignee tb explícito
    db_session.add(TaskMember(task_id=task.id, user_id=author.id))
    db_session.flush()

    client.post(f"/api/v1/tasks/{task.id}/comments", json={"content": "Olá"}, headers=auth_headers(author))

    notifications = db_session.query(Notification).filter(Notification.task_id == task.id).all()
    assert len(notifications) == 1
    assert notifications[0].recipient_id == assignee.id


def test_create_comment_personal_task_zero_notifications(
    client, make_user, make_task, auth_headers, db_session
):
    creator = make_user()
    task = make_task(creator=creator)

    client.post(
        f"/api/v1/tasks/{task.id}/comments", json={"content": "Sozinho"}, headers=auth_headers(creator)
    )

    notifications = db_session.query(Notification).filter(Notification.task_id == task.id).all()
    assert notifications == []


def test_create_comment_notification_fields(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    assignee = make_user(email="assignee-fields@example.com")
    author = make_user(name="Fulano", email="author-fields@example.com")  # participante explícito
    workspace = make_workspace(owner=owner, name="WS")
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=author, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace, title="Tarefa Y")
    db_session.add(TaskMember(task_id=task.id, user_id=author.id))
    db_session.flush()

    client.post(f"/api/v1/tasks/{task.id}/comments", json={"content": "Olá"}, headers=auth_headers(author))

    notification = (
        db_session.query(Notification).filter(Notification.task_id == task.id).one()
    )
    assert notification.type == NotificationType.NEW_COMMENT
    assert notification.task_id == task.id
    assert notification.title == "Novo comentário"
    assert notification.message == 'Fulano comentou na tarefa "Tarefa Y".'
    assert notification.is_read is False


# --- Atomicidade via HTTP ------------------------------------------------------


def test_create_comment_http_rolls_back_on_notification_failure(
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_task,
    auth_headers,
    db_session,
    monkeypatch,
):
    owner = make_user()
    assignee = make_user(email="assignee-http-atomicity@example.com")
    participant = make_user(email="participant-http-atomicity@example.com")
    author = make_user(email="author-http-atomicity@example.com")  # participante explícito, quem comenta
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=author, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.add(TaskMember(task_id=task.id, user_id=author.id))
    db_session.flush()
    # 2 destinatários esperados (assignee + participant) -> falha na 2a.

    call_count = {"n": 0}
    original_create = NotificationRepository.create

    def _failing_create(self: NotificationRepository, notification: Notification) -> Notification:
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("Falha simulada")
        return original_create(self, notification)

    monkeypatch.setattr(NotificationRepository, "create", _failing_create)

    # Tratamento global vigente: o fixture `client` usa `TestClient(app)` com
    # `raise_server_exceptions=True` (padrão) — uma exceção não tratada por
    # nenhum handler de domínio (`AppError`) propaga para o chamador do
    # teste, em vez de virar uma resposta 500 observável aqui. Em produção
    # (fora do TestClient), o handler genérico de `core/exceptions.py`
    # converteria para 500 sem vazar detalhes — o que importa para T083/T084
    # é que create_comment não deixa nada persistido, verificado abaixo.
    with pytest.raises(RuntimeError):
        client.post(
            f"/api/v1/tasks/{task.id}/comments", json={"content": "Vai falhar"}, headers=auth_headers(author)
        )

    comments = db_session.query(Comment).filter(Comment.task_id == task.id).all()
    notifications = db_session.query(Notification).filter(Notification.task_id == task.id).all()
    assert comments == []
    assert notifications == []


# --- Regressão -----------------------------------------------------------------


def test_no_notifications_route_in_openapi(client):
    response = client.get("/openapi.json")
    paths = response.json()["paths"]
    assert not any("notifications" in path for path in paths)


def test_task_members_endpoint_still_works(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/members", headers=auth_headers(owner))

    assert response.status_code == 200


def test_get_tasks_list_still_restricted_to_personal(client, make_user, make_task, auth_headers):
    user = make_user()
    make_task(creator=user, title="Pessoal")

    response = client.get("/api/v1/tasks", headers=auth_headers(user))

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
