"""T074/T078 [US5] — participantes de tarefa: visibilidade, adição, remoção,
responsável implícito, isolamento entre workspaces.

Cobre: FR-030 a FR-034, contracts/projects-and-tasks.md
(`GET/POST /tasks/{id}/members`, `DELETE /tasks/{id}/members/{user_id}`)."""

import uuid

from app.enums.workspace_role import WorkspaceRole
from app.models.task_member import TaskMember


# --- GET /tasks/{task_id}/members --------------------------------------------


def test_list_members_no_explicit_members_returns_only_assignee(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/members", headers=auth_headers(owner))

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["user_id"] == str(owner.id)
    assert body[0]["added_at"] is None


def test_list_members_includes_explicit_and_assignee_without_duplication(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    assignee = make_user(email="assignee-list@example.com")
    participant = make_user(email="participant-list@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    response = client.get(f"/api/v1/tasks/{task.id}/members", headers=auth_headers(owner))

    assert response.status_code == 200
    body = response.json()
    user_ids = [item["user_id"] for item in body]
    assert len(user_ids) == len(set(user_ids))  # sem duplicidade
    assert set(user_ids) == {str(assignee.id), str(participant.id)}

    by_id = {item["user_id"]: item for item in body}
    assert by_id[str(assignee.id)]["added_at"] is None
    assert by_id[str(participant.id)]["added_at"] is not None


def test_list_members_outsider_returns_404(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    outsider = make_user(email="outsider-list-members@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/members", headers=auth_headers(outsider))

    assert response.status_code == 404


def test_list_members_owner_visible_even_without_being_participant(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    creator = make_user(email="creator-owner-visible@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/members", headers=auth_headers(owner))

    assert response.status_code == 200


def test_list_members_personal_task_returns_only_creator(client, make_user, make_task, auth_headers):
    creator = make_user()
    task = make_task(creator=creator)

    response = client.get(f"/api/v1/tasks/{task.id}/members", headers=auth_headers(creator))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["user_id"] == str(creator.id)


def test_personal_task_never_persists_task_member_row(
    client, make_user, make_task, auth_headers, db_session
):
    """Auditoria FR-031 vs. FR-033 (contracts/projects-and-tasks.md): o
    criador aparece como participante implícito em `GET /members` (FR-033,
    aplica-se a toda tarefa), mas isso nunca persiste uma linha em
    `task_members` para tarefa pessoal (FR-031 — proíbe participantes
    ADICIONAIS/explícitos, não o conceito de participante em si). Confirma a
    nível de banco, não apenas pela resposta HTTP, e mesmo após uma tentativa
    (rejeitada) de POST."""
    creator = make_user()
    other = make_user(email="other-no-persist@example.com")
    task = make_task(creator=creator)

    get_response = client.get(f"/api/v1/tasks/{task.id}/members", headers=auth_headers(creator))
    assert get_response.status_code == 200
    assert len(get_response.json()) == 1

    post_response = client.post(
        f"/api/v1/tasks/{task.id}/members",
        json={"user_id": str(other.id)},
        headers=auth_headers(creator),
    )
    assert post_response.status_code == 400

    rows = db_session.query(TaskMember).filter(TaskMember.task_id == task.id).all()
    assert rows == []


# --- POST /tasks/{task_id}/members --------------------------------------------


def test_add_member_valid(client, make_user, make_workspace, add_workspace_member, make_task, auth_headers):
    owner = make_user()
    candidate = make_user(email="candidate-add@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=candidate, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/members",
        json={"user_id": str(candidate.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == str(candidate.id)
    assert body["added_at"] is not None


def test_add_member_user_outside_workspace_rejected(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    outsider = make_user(email="outsider-add@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/members",
        json={"user_id": str(outsider.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


def test_add_member_nonexistent_user_rejected(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/members",
        json={"user_id": str(uuid.uuid4())},
        headers=auth_headers(owner),
    )

    assert response.status_code == 400


def test_add_member_assignee_returns_409(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    assignee = make_user(email="assignee-409@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/members",
        json={"user_id": str(assignee.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 409


def test_add_member_duplicate_returns_409(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    candidate = make_user(email="candidate-duplicate@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=candidate, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=candidate.id))
    db_session.flush()

    response = client.post(
        f"/api/v1/tasks/{task.id}/members",
        json={"user_id": str(candidate.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 409


def test_add_member_personal_task_rejected(client, make_user, make_task, auth_headers):
    creator = make_user()
    other = make_user(email="other-personal-add@example.com")
    task = make_task(creator=creator)  # workspace=None -> tarefa pessoal

    response = client.post(
        f"/api/v1/tasks/{task.id}/members",
        json={"user_id": str(other.id)},
        headers=auth_headers(creator),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


def test_add_member_forbidden_for_plain_member(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    plain_member = make_user(email="plain-member-add@example.com")
    candidate = make_user(email="candidate-forbidden@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=candidate, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/members",
        json={"user_id": str(candidate.id)},
        headers=auth_headers(plain_member),
    )

    assert response.status_code == 403


def test_add_member_outsider_returns_404(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    outsider = make_user(email="outsider-add-forbidden@example.com")
    candidate = make_user(email="candidate-outsider-add@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.post(
        f"/api/v1/tasks/{task.id}/members",
        json={"user_id": str(candidate.id)},
        headers=auth_headers(outsider),
    )

    assert response.status_code == 404


# --- DELETE /tasks/{task_id}/members/{user_id} --------------------------------


def test_remove_member_explicit_success(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    participant = make_user(email="participant-remove@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    response = client.delete(
        f"/api/v1/tasks/{task.id}/members/{participant.id}", headers=auth_headers(owner)
    )

    assert response.status_code == 204
    assert response.content == b""


def test_remove_member_nonexistent_link_returns_404(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.delete(
        f"/api/v1/tasks/{task.id}/members/{uuid.uuid4()}", headers=auth_headers(owner)
    )

    assert response.status_code == 404


def test_remove_assignee_rejected(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    assignee = make_user(email="assignee-remove-rejected@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)

    response = client.delete(
        f"/api/v1/tasks/{task.id}/members/{assignee.id}", headers=auth_headers(owner)
    )

    assert response.status_code == 400


def test_remove_member_forbidden_for_plain_member(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    plain_member = make_user(email="plain-member-remove@example.com")
    participant = make_user(email="participant-remove-2@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    response = client.delete(
        f"/api/v1/tasks/{task.id}/members/{participant.id}", headers=auth_headers(plain_member)
    )

    assert response.status_code == 403


def test_remove_member_outsider_returns_404(
    client, make_user, make_workspace, make_task, auth_headers, db_session
):
    owner = make_user()
    outsider = make_user(email="outsider-remove@example.com")
    participant = make_user(email="participant-remove-3@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    response = client.delete(
        f"/api/v1/tasks/{task.id}/members/{participant.id}", headers=auth_headers(outsider)
    )

    assert response.status_code == 404


# --- Isolamento entre workspaces ---------------------------------------------


def test_isolation_cannot_add_member_from_another_workspace(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    workspace_a = make_workspace(owner=owner, name="WS A")
    workspace_b = make_workspace(owner=owner, name="WS B")
    member_of_b = make_user(email="member-of-b@example.com")
    add_workspace_member(workspace=workspace_b, user=member_of_b, role=WorkspaceRole.MEMBER)
    task_in_a = make_task(creator=owner, workspace=workspace_a)

    response = client.post(
        f"/api/v1/tasks/{task_in_a.id}/members",
        json={"user_id": str(member_of_b.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 400


def test_isolation_member_of_other_workspace_cannot_view(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    workspace_a = make_workspace(owner=owner, name="WS A")
    workspace_b = make_workspace(owner=owner, name="WS B")
    member_of_b = make_user(email="member-of-b-view@example.com")
    add_workspace_member(workspace=workspace_b, user=member_of_b, role=WorkspaceRole.MEMBER)
    task_in_a = make_task(creator=owner, workspace=workspace_a)

    response = client.get(
        f"/api/v1/tasks/{task_in_a.id}/members", headers=auth_headers(member_of_b)
    )

    assert response.status_code == 404
