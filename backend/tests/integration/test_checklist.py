"""T092/T095 [US9] — checklist em tarefas via HTTP: visibilidade, colaboração
restrita a participantes, marcação de concluído/pendente, remoção.

Cobre: FR-035, FR-036, contracts/collaboration.md
(`GET/POST /tasks/{task_id}/checklist`, `PATCH/DELETE .../checklist/{item_id}`)."""

import uuid

from app.enums.workspace_role import WorkspaceRole
from app.models.checklist_item import ChecklistItem
from app.models.task_member import TaskMember


# --- GET /tasks/{task_id}/checklist --------------------------------------------


def test_list_items_empty(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/checklist", headers=auth_headers(owner))

    assert response.status_code == 200
    assert response.json() == []


def test_list_items_multiple(client, make_user, make_workspace, make_task, auth_headers, db_session):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(ChecklistItem(task_id=task.id, description="Passo 1"))
    db_session.add(ChecklistItem(task_id=task.id, description="Passo 2"))
    db_session.flush()

    response = client.get(f"/api/v1/tasks/{task.id}/checklist", headers=auth_headers(owner))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {item["description"] for item in body} == {"Passo 1", "Passo 2"}


def test_list_items_any_workspace_member_can_view(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    member = make_user(email="member-list-checklist@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/checklist", headers=auth_headers(member))

    assert response.status_code == 200


def test_list_items_outsider_returns_404(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    outsider = make_user(email="outsider-list-checklist@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/checklist", headers=auth_headers(outsider))

    assert response.status_code == 404


def test_list_items_personal_task_creator_returns_200(client, make_user, make_task, auth_headers):
    creator = make_user()
    task = make_task(creator=creator)

    response = client.get(f"/api/v1/tasks/{task.id}/checklist", headers=auth_headers(creator))

    assert response.status_code == 200


def test_list_items_nonexistent_task_returns_404(client, make_user, auth_headers):
    user = make_user()

    response = client.get(f"/api/v1/tasks/{uuid.uuid4()}/checklist", headers=auth_headers(user))

    assert response.status_code == 404


# --- POST /tasks/{task_id}/checklist --------------------------------------------


def test_create_item_assignee_success(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    assignee = make_user(email="assignee-create-checklist@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/checklist",
        json={"description": "Novo passo"},
        headers=auth_headers(assignee),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["description"] == "Novo passo"
    assert body["is_done"] is False
    assert body["completed_at"] is None


def test_create_item_explicit_participant_success(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    participant = make_user(email="participant-create-checklist@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    response = client.post(
        f"/api/v1/tasks/{task.id}/checklist",
        json={"description": "Passo do participante"},
        headers=auth_headers(participant),
    )

    assert response.status_code == 201


def test_create_item_personal_task_creator_success(client, make_user, make_task, auth_headers):
    creator = make_user()
    task = make_task(creator=creator)

    response = client.post(
        f"/api/v1/tasks/{task.id}/checklist",
        json={"description": "Passo pessoal"},
        headers=auth_headers(creator),
    )

    assert response.status_code == 201


def test_create_item_plain_member_forbidden(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    plain_member = make_user(email="plain-member-create-checklist@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/checklist",
        json={"description": "Não deveria funcionar"},
        headers=auth_headers(plain_member),
    )

    assert response.status_code == 403


def test_create_item_owner_admin_not_participant_forbidden(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    admin = make_user(email="admin-create-checklist@example.com")
    creator = make_user(email="creator-create-checklist@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    response_owner = client.post(
        f"/api/v1/tasks/{task.id}/checklist", json={"description": "X"}, headers=auth_headers(owner)
    )
    response_admin = client.post(
        f"/api/v1/tasks/{task.id}/checklist", json={"description": "X"}, headers=auth_headers(admin)
    )

    assert response_owner.status_code == 403
    assert response_admin.status_code == 403


def test_create_item_outsider_returns_404(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    outsider = make_user(email="outsider-create-checklist@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/checklist", json={"description": "X"}, headers=auth_headers(outsider)
    )

    assert response.status_code == 404


def test_create_item_empty_description_returns_422(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/checklist", json={"description": ""}, headers=auth_headers(owner)
    )

    assert response.status_code == 422


def test_create_item_nonexistent_task_returns_404(client, make_user, auth_headers):
    user = make_user()

    response = client.post(
        f"/api/v1/tasks/{uuid.uuid4()}/checklist", json={"description": "X"}, headers=auth_headers(user)
    )

    assert response.status_code == 404


# --- PATCH /tasks/{task_id}/checklist/{item_id} --------------------------------


def test_mark_item_done_sets_completed_at(
    client, make_user, make_workspace, make_task, auth_headers, db_session
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    item = ChecklistItem(task_id=task.id, description="Passo")
    db_session.add(item)
    db_session.flush()

    response = client.patch(
        f"/api/v1/tasks/{task.id}/checklist/{item.id}",
        json={"is_done": True},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_done"] is True
    assert body["completed_at"] is not None


def test_mark_item_pending_clears_completed_at(
    client, make_user, make_workspace, make_task, auth_headers, db_session
):
    from datetime import datetime, timezone

    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    item = ChecklistItem(task_id=task.id, description="Passo", is_done=True)
    item.completed_at = datetime.now(timezone.utc)
    db_session.add(item)
    db_session.flush()

    response = client.patch(
        f"/api/v1/tasks/{task.id}/checklist/{item.id}",
        json={"is_done": False},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_done"] is False
    assert body["completed_at"] is None


def test_update_item_forbidden_for_plain_member(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    plain_member = make_user(email="plain-member-update-checklist@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    item = ChecklistItem(task_id=task.id, description="Passo")
    db_session.add(item)
    db_session.flush()

    response = client.patch(
        f"/api/v1/tasks/{task.id}/checklist/{item.id}",
        json={"is_done": True},
        headers=auth_headers(plain_member),
    )

    assert response.status_code == 403


def test_update_item_nonexistent_returns_404(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.patch(
        f"/api/v1/tasks/{task.id}/checklist/{uuid.uuid4()}",
        json={"is_done": True},
        headers=auth_headers(owner),
    )

    assert response.status_code == 404


def test_update_item_from_another_task_returns_404(
    client, make_user, make_workspace, make_task, auth_headers, db_session
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task_1 = make_task(creator=owner, workspace=workspace, title="Tarefa 1")
    task_2 = make_task(creator=owner, workspace=workspace, title="Tarefa 2")
    item = ChecklistItem(task_id=task_1.id, description="Passo da tarefa 1")
    db_session.add(item)
    db_session.flush()

    response = client.patch(
        f"/api/v1/tasks/{task_2.id}/checklist/{item.id}",
        json={"is_done": True},
        headers=auth_headers(owner),
    )

    assert response.status_code == 404


def test_update_item_outsider_returns_404(
    client, make_user, make_workspace, make_task, auth_headers, db_session
):
    owner = make_user()
    outsider = make_user(email="outsider-update-checklist@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    item = ChecklistItem(task_id=task.id, description="Passo")
    db_session.add(item)
    db_session.flush()

    response = client.patch(
        f"/api/v1/tasks/{task.id}/checklist/{item.id}",
        json={"is_done": True},
        headers=auth_headers(outsider),
    )

    assert response.status_code == 404


def test_update_item_rejects_description_field(
    client, make_user, make_workspace, make_task, auth_headers, db_session
):
    """Refinamento #7: sem edição textual de `description` neste MVP."""
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    item = ChecklistItem(task_id=task.id, description="Original")
    db_session.add(item)
    db_session.flush()

    response = client.patch(
        f"/api/v1/tasks/{task.id}/checklist/{item.id}",
        json={"description": "Tentando editar"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 422


# --- DELETE /tasks/{task_id}/checklist/{item_id} -------------------------------


def test_delete_item_success(client, make_user, make_workspace, make_task, auth_headers, db_session):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    item = ChecklistItem(task_id=task.id, description="Passo")
    db_session.add(item)
    db_session.flush()

    response = client.delete(
        f"/api/v1/tasks/{task.id}/checklist/{item.id}", headers=auth_headers(owner)
    )

    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get(f"/api/v1/tasks/{task.id}/checklist", headers=auth_headers(owner))
    assert get_response.json() == []


def test_delete_item_forbidden_for_plain_member(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    plain_member = make_user(email="plain-member-delete-checklist@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    item = ChecklistItem(task_id=task.id, description="Passo")
    db_session.add(item)
    db_session.flush()

    response = client.delete(
        f"/api/v1/tasks/{task.id}/checklist/{item.id}", headers=auth_headers(plain_member)
    )

    assert response.status_code == 403


def test_delete_item_nonexistent_returns_404(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.delete(
        f"/api/v1/tasks/{task.id}/checklist/{uuid.uuid4()}", headers=auth_headers(owner)
    )

    assert response.status_code == 404


def test_delete_item_outsider_returns_404(
    client, make_user, make_workspace, make_task, auth_headers, db_session
):
    owner = make_user()
    outsider = make_user(email="outsider-delete-checklist@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    item = ChecklistItem(task_id=task.id, description="Passo")
    db_session.add(item)
    db_session.flush()

    response = client.delete(
        f"/api/v1/tasks/{task.id}/checklist/{item.id}", headers=auth_headers(outsider)
    )

    assert response.status_code == 404


# --- Isolamento entre workspaces -------------------------------------------------


def test_isolation_member_of_other_workspace_cannot_view(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    workspace_a = make_workspace(owner=owner, name="WS A")
    workspace_b = make_workspace(owner=owner, name="WS B")
    member_b = make_user(email="member-b-checklist-isolation@example.com")
    add_workspace_member(workspace=workspace_b, user=member_b, role=WorkspaceRole.MEMBER)
    task_in_a = make_task(creator=owner, workspace=workspace_a)

    response = client.get(
        f"/api/v1/tasks/{task_in_a.id}/checklist", headers=auth_headers(member_b)
    )

    assert response.status_code == 404


# --- Regressão -----------------------------------------------------------------


def test_task_members_endpoint_still_works(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/members", headers=auth_headers(owner))

    assert response.status_code == 200


def test_comments_endpoint_still_works(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/comments", headers=auth_headers(owner))

    assert response.status_code == 200
