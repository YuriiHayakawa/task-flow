"""T106 [US11] — `PATCH /tasks/{task_id}` gera `Notification` tipo
`TASK_CHANGED` para os participantes afetados (exceto quem alterou) quando
status/prioridade/prazo/responsável mudam; nenhuma notificação para campos
não rastreados. Cobre também a correção do bug de reatribuição de
responsável em tarefa de workspace encontrado na abertura desta fase, e o
reset de `due_soon_notified_for` quando o prazo muda.

Cobre: FR-039, research.md #2 (reset de `due_soon_notified_for`),
contracts/dashboard-and-notifications.md."""

from datetime import date, timedelta

from app.enums.notification_type import NotificationType
from app.enums.workspace_role import WorkspaceRole
from app.models.task import Task
from app.models.task_member import TaskMember
from app.repositories.notification_repository import NotificationRepository


# --- Correção do bug de reatribuição (Fase 13) ----------------------------------


def test_reassign_workspace_task_to_valid_member_succeeds(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    other_member = make_user(email="other-member-reassign@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=other_member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)

    response = client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"assignee_id": str(other_member.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["assignee_id"] == str(other_member.id)


def test_reassign_workspace_task_to_non_member_rejected(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    non_member = make_user(email="non-member-reassign@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"assignee_id": str(non_member.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


def test_reassign_project_task_to_non_project_member_rejected(
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_task,
    auth_headers,
):
    """003-membros-projeto/FR-009: ser membro do WORKSPACE não basta para
    ser reatribuído a uma tarefa de um projeto restrito."""
    owner = make_user()
    workspace_member = make_user(email="workspace-only-reassign@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=workspace_member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace, creator=owner)
    task = make_task(creator=owner, workspace=workspace, project=project)

    response = client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"assignee_id": str(workspace_member.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


def test_reassign_project_task_to_project_member_succeeds(
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_project_member,
    make_task,
    auth_headers,
):
    owner = make_user()
    project_member = make_user(email="project-member-reassign@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=project_member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace, creator=owner)
    make_project_member(project=project, user=project_member)
    task = make_task(creator=owner, workspace=workspace, project=project)

    response = client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"assignee_id": str(project_member.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["assignee_id"] == str(project_member.id)


def test_reassign_personal_task_to_another_user_still_rejected(
    client, make_user, make_task, auth_headers
):
    """Regressão: a correção do bug não deve afetar a invariante já
    existente de tarefa pessoal."""
    creator = make_user()
    other_user = make_user(email="other-user-personal-reassign@example.com")
    task = make_task(creator=creator)

    response = client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"assignee_id": str(other_user.id)},
        headers=auth_headers(creator),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


# --- Notificação TASK_CHANGED ---------------------------------------------------


def test_status_change_notifies_participant_except_author(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    participant = make_user(email="participant-task-changed@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"status": "IN_PROGRESS"}, headers=auth_headers(owner)
    )

    assert response.status_code == 200
    notifications = NotificationRepository(db_session).list_by_recipient(participant.id)
    assert len(notifications) == 1
    assert notifications[0].type == NotificationType.TASK_CHANGED
    assert notifications[0].task_id == task.id
    # o autor da alteração não recebe notificação sobre a própria ação:
    owner_notifications = NotificationRepository(db_session).list_by_recipient(owner.id)
    assert owner_notifications == []


def test_priority_change_notifies_participant(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    participant = make_user(email="participant-priority-changed@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    client.patch(f"/api/v1/tasks/{task.id}", json={"priority": "URGENT"}, headers=auth_headers(owner))

    notifications = NotificationRepository(db_session).list_by_recipient(participant.id)
    assert len(notifications) == 1


def test_due_date_change_notifies_participant(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    participant = make_user(email="participant-due-date-changed@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace, due_date=date.today())
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    new_due_date = (date.today() + timedelta(days=3)).isoformat()
    client.patch(
        f"/api/v1/tasks/{task.id}", json={"due_date": new_due_date}, headers=auth_headers(owner)
    )

    notifications = NotificationRepository(db_session).list_by_recipient(participant.id)
    assert len(notifications) == 1


def test_reassignment_notifies_both_old_and_new_assignee(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    old_assignee = make_user(email="old-assignee-task-changed@example.com")
    new_assignee = make_user(email="new-assignee-task-changed@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=old_assignee, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=new_assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=old_assignee, workspace=workspace)

    client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"assignee_id": str(new_assignee.id)},
        headers=auth_headers(owner),
    )

    old_notifications = NotificationRepository(db_session).list_by_recipient(old_assignee.id)
    new_notifications = NotificationRepository(db_session).list_by_recipient(new_assignee.id)
    assert len(old_notifications) == 1
    assert len(new_notifications) == 1


def test_untracked_field_change_generates_no_notification(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    participant = make_user(email="participant-untracked-change@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    client.patch(
        f"/api/v1/tasks/{task.id}", json={"title": "Novo título"}, headers=auth_headers(owner)
    )

    notifications = NotificationRepository(db_session).list_by_recipient(participant.id)
    assert notifications == []


def test_personal_task_change_generates_no_notification(client, make_user, make_task, auth_headers, db_session):
    creator = make_user()
    task = make_task(creator=creator)

    client.patch(f"/api/v1/tasks/{task.id}", json={"status": "DONE"}, headers=auth_headers(creator))

    notifications = NotificationRepository(db_session).list_by_recipient(creator.id)
    assert notifications == []


# --- Reset de due_soon_notified_for ---------------------------------------------


def test_due_date_change_resets_due_soon_notified_for(
    client, make_user, make_workspace, make_task, auth_headers, db_session
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace, due_date=date.today())
    task.due_soon_notified_for = task.due_date  # simula já notificado
    db_session.flush()

    new_due_date = (date.today() + timedelta(days=10)).isoformat()
    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"due_date": new_due_date}, headers=auth_headers(owner)
    )

    assert response.status_code == 200
    reloaded = db_session.get(Task, task.id)
    assert reloaded is not None
    assert reloaded.due_soon_notified_for is None


def test_due_date_unchanged_does_not_reset_due_soon_notified_for(
    client, make_user, make_workspace, make_task, auth_headers, db_session
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace, due_date=date.today())
    task.due_soon_notified_for = task.due_date
    db_session.flush()

    response = client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"due_date": task.due_date.isoformat()},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    reloaded = db_session.get(Task, task.id)
    assert reloaded is not None
    assert reloaded.due_soon_notified_for == reloaded.due_date


# --- Regressão -----------------------------------------------------------------


def test_notifications_endpoint_still_works(client, make_user, auth_headers):
    user = make_user()

    response = client.get("/api/v1/notifications", headers=auth_headers(user))

    assert response.status_code == 200
