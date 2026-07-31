"""T108/T111 [US12] — histórico de alterações da tarefa via HTTP:
visibilidade ampla (qualquer membro do workspace, mesmo não-participante),
entrada por campo rastreado, ordem cronológica descendente.

Cobre: FR-041, FR-042, contracts/collaboration.md
(`GET /api/v1/tasks/{task_id}/history`)."""

import uuid

from app.enums.workspace_role import WorkspaceRole


# --- GET /tasks/{task_id}/history ------------------------------------------------


def test_list_history_empty_when_no_changes(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/history", headers=auth_headers(owner))

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_status_change_creates_history_entry(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    client.patch(f"/api/v1/tasks/{task.id}", json={"status": "DONE"}, headers=auth_headers(owner))
    response = client.get(f"/api/v1/tasks/{task.id}/history", headers=auth_headers(owner))

    body = response.json()
    assert len(body["items"]) == 1
    entry = body["items"][0]
    assert entry["field_changed"] == "status"
    assert entry["old_value"] == "PENDING"
    assert entry["new_value"] == "DONE"
    assert entry["changed_by_id"] == str(owner.id)
    assert entry["changed_by_name"] == owner.name
    assert entry["changed_by_email"] == owner.email
    assert entry["changed_at"] is not None


def test_priority_change_creates_history_entry(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    client.patch(f"/api/v1/tasks/{task.id}", json={"priority": "URGENT"}, headers=auth_headers(owner))
    response = client.get(f"/api/v1/tasks/{task.id}/history", headers=auth_headers(owner))

    entry = response.json()["items"][0]
    assert entry["field_changed"] == "priority"
    assert entry["new_value"] == "URGENT"


def test_due_date_change_creates_history_entry(client, make_user, make_workspace, make_task, auth_headers):
    from datetime import date

    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace, due_date=date(2026, 1, 1))

    client.patch(
        f"/api/v1/tasks/{task.id}", json={"due_date": "2026-03-15"}, headers=auth_headers(owner)
    )
    response = client.get(f"/api/v1/tasks/{task.id}/history", headers=auth_headers(owner))

    entry = response.json()["items"][0]
    assert entry["field_changed"] == "due_date"
    assert entry["old_value"] == "2026-01-01"
    assert entry["new_value"] == "2026-03-15"


def test_assignee_change_creates_history_entry(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    new_assignee = make_user(email="new-assignee-history@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=new_assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)

    client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"assignee_id": str(new_assignee.id)},
        headers=auth_headers(owner),
    )
    response = client.get(f"/api/v1/tasks/{task.id}/history", headers=auth_headers(owner))

    entry = response.json()["items"][0]
    assert entry["field_changed"] == "assignee_id"
    assert entry["old_value"] == str(owner.id)
    assert entry["new_value"] == str(new_assignee.id)


def test_untracked_field_change_creates_no_history_entry(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    client.patch(f"/api/v1/tasks/{task.id}", json={"title": "Novo título"}, headers=auth_headers(owner))
    response = client.get(f"/api/v1/tasks/{task.id}/history", headers=auth_headers(owner))

    assert response.json()["items"] == []


def test_multiple_changes_in_one_patch_create_multiple_entries(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"status": "IN_PROGRESS", "priority": "HIGH"},
        headers=auth_headers(owner),
    )
    response = client.get(f"/api/v1/tasks/{task.id}/history", headers=auth_headers(owner))

    fields = {entry["field_changed"] for entry in response.json()["items"]}
    assert fields == {"status", "priority"}


def test_history_ordered_chronologically_descending(
    client, make_user, make_workspace, make_task, auth_headers, db_session
):
    """PostgreSQL `now()` fica "congelado" por transação — como todo o teste
    roda na mesma transação compartilhada (fixture `db_session`), as três
    entradas recebem `changed_at` idêntico. Força-se timestamps distintos
    diretamente, o mesmo ajuste já necessário em `test_comments.py`
    (Fase 9) — em produção, cada requisição HTTP real tem sua própria
    transação, então esse empate nunca ocorre de fato."""
    from datetime import timedelta

    from app.models.task_history_entry import TaskHistoryEntry

    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    client.patch(f"/api/v1/tasks/{task.id}", json={"status": "IN_PROGRESS"}, headers=auth_headers(owner))
    client.patch(f"/api/v1/tasks/{task.id}", json={"priority": "URGENT"}, headers=auth_headers(owner))
    client.patch(f"/api/v1/tasks/{task.id}", json={"status": "DONE"}, headers=auth_headers(owner))

    entries = (
        db_session.query(TaskHistoryEntry)
        .filter(TaskHistoryEntry.task_id == task.id)
        .order_by(TaskHistoryEntry.new_value)
        .all()
    )
    now = entries[0].changed_at
    for index, entry in enumerate(
        sorted(entries, key=lambda e: {"IN_PROGRESS": 0, "URGENT": 1, "DONE": 2}[e.new_value])
    ):
        entry.changed_at = now + timedelta(minutes=index)
    db_session.flush()

    response = client.get(f"/api/v1/tasks/{task.id}/history", headers=auth_headers(owner))

    fields_in_order = [entry["field_changed"] for entry in response.json()["items"]]
    new_values_in_order = [entry["new_value"] for entry in response.json()["items"]]
    assert new_values_in_order[0] == "DONE"  # a última alteração (DONE) vem primeiro
    assert len(fields_in_order) == 3


def test_history_visible_to_workspace_member_without_participation(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    """FR-042: qualquer membro do workspace consulta o histórico — não
    exige ser responsável nem participante explícito."""
    owner = make_user()
    plain_member = make_user(email="plain-member-history@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    client.patch(f"/api/v1/tasks/{task.id}", json={"status": "DONE"}, headers=auth_headers(owner))

    response = client.get(f"/api/v1/tasks/{task.id}/history", headers=auth_headers(plain_member))

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_history_personal_task_creator_can_view(client, make_user, make_task, auth_headers):
    creator = make_user()
    task = make_task(creator=creator)
    client.patch(f"/api/v1/tasks/{task.id}", json={"status": "DONE"}, headers=auth_headers(creator))

    response = client.get(f"/api/v1/tasks/{task.id}/history", headers=auth_headers(creator))

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_history_outsider_returns_404(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    outsider = make_user(email="outsider-history@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/history", headers=auth_headers(outsider))

    assert response.status_code == 404


def test_history_nonexistent_task_returns_404(client, make_user, auth_headers):
    user = make_user()

    response = client.get(f"/api/v1/tasks/{uuid.uuid4()}/history", headers=auth_headers(user))

    assert response.status_code == 404


# --- Acceptance Scenario 3: reatribuição por remoção de membro -----------------


def test_reassignment_before_member_removal_appears_as_assignee_change(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    """spec.md US12, cenário 3: uma tarefa reatribuída (via `PATCH
    /tasks/{id}`, o fluxo normal exigido antes de remover um membro
    responsável por tarefas ativas — US3/FR-024) aparece no histórico como
    uma alteração de responsável comum, sem tratamento especial."""
    from app.enums.task_status import TaskStatus

    owner = make_user()
    member_to_remove = make_user(email="member-to-remove-history@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member_to_remove, role=WorkspaceRole.MEMBER)
    task = make_task(
        creator=owner, assignee=member_to_remove, workspace=workspace, status=TaskStatus.PENDING
    )

    # Reatribui a tarefa ao Owner antes de remover o membro (fluxo normal via API).
    reassign_response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"assignee_id": str(owner.id)}, headers=auth_headers(owner)
    )
    assert reassign_response.status_code == 200

    remove_response = client.delete(
        f"/api/v1/workspaces/{workspace.id}/members/{member_to_remove.id}",
        headers=auth_headers(owner),
    )
    assert remove_response.status_code == 204

    history_response = client.get(f"/api/v1/tasks/{task.id}/history", headers=auth_headers(owner))

    entries = history_response.json()["items"]
    assert len(entries) == 1
    assert entries[0]["field_changed"] == "assignee_id"
    assert entries[0]["old_value"] == str(member_to_remove.id)
    assert entries[0]["new_value"] == str(owner.id)


# --- Regressão -----------------------------------------------------------------


def test_notifications_endpoint_still_works(client, make_user, auth_headers):
    user = make_user()

    response = client.get("/api/v1/notifications", headers=auth_headers(user))

    assert response.status_code == 200
