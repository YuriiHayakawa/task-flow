"""T068 [US4] — criação de tarefa em workspace/projeto: workspace derivado do
projeto, incompatibilidade workspace/projeto rejeitada, responsável deve ser
membro do workspace.

Cobre: FR-006 a FR-008, FR-021, contracts/projects-and-tasks.md
(`POST /api/v1/tasks`)."""

import uuid

from app.enums.workspace_role import WorkspaceRole


def test_create_personal_task_still_works(client, make_user, auth_headers):
    """Regressão (US1): tarefa pessoal continua funcionando exatamente como
    antes — nenhum campo de workspace/projeto informado."""
    user = make_user()

    response = client.post(
        "/api/v1/tasks", json={"title": "Tarefa pessoal"}, headers=auth_headers(user)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["workspace_id"] is None
    assert body["project_id"] is None
    assert body["assignee_id"] == str(user.id)
    assert body["creator_id"] == str(user.id)


def test_member_creates_task_directly_in_workspace(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    member = make_user(email="member-task@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)

    response = client.post(
        "/api/v1/tasks",
        json={"title": "Tarefa de workspace", "workspace_id": str(workspace.id)},
        headers=auth_headers(member),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["workspace_id"] == str(workspace.id)
    assert body["project_id"] is None
    assert body["assignee_id"] == str(member.id)  # default: o próprio criador


def test_member_creates_task_with_project_id_only_derives_workspace(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    owner = make_user()
    member = make_user(email="member-project-task@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)

    response = client.post(
        "/api/v1/tasks",
        json={"title": "Tarefa de projeto", "project_id": str(project.id)},
        headers=auth_headers(member),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == str(project.id)
    assert body["workspace_id"] == str(workspace.id)  # derivado do projeto


def test_project_and_matching_workspace_id_accepted(
    client, make_user, make_workspace, make_project, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace)

    response = client.post(
        "/api/v1/tasks",
        json={
            "title": "Tarefa consistente",
            "project_id": str(project.id),
            "workspace_id": str(workspace.id),
        },
        headers=auth_headers(owner),
    )

    assert response.status_code == 201


def test_project_workspace_mismatch_returns_400(
    client, make_user, make_workspace, make_project, auth_headers
):
    owner = make_user()
    workspace_a = make_workspace(owner=owner, name="WS A")
    workspace_b = make_workspace(owner=owner, name="WS B")
    project_in_a = make_project(workspace=workspace_a)

    response = client.post(
        "/api/v1/tasks",
        json={
            "title": "Tarefa inconsistente",
            "project_id": str(project_in_a.id),
            "workspace_id": str(workspace_b.id),
        },
        headers=auth_headers(owner),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


def test_outsider_cannot_create_task_directly_in_workspace(
    client, make_user, make_workspace, auth_headers
):
    owner = make_user()
    outsider = make_user(email="outsider-task@example.com")
    workspace = make_workspace(owner=owner)

    response = client.post(
        "/api/v1/tasks",
        json={"title": "Não deveria existir", "workspace_id": str(workspace.id)},
        headers=auth_headers(outsider),
    )

    assert response.status_code == 403


def test_outsider_cannot_create_task_in_project(
    client, make_user, make_workspace, make_project, auth_headers
):
    owner = make_user()
    outsider = make_user(email="outsider-project-task@example.com")
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace)

    response = client.post(
        "/api/v1/tasks",
        json={"title": "Não deveria existir", "project_id": str(project.id)},
        headers=auth_headers(outsider),
    )

    assert response.status_code == 403


def test_create_task_nonexistent_workspace_returns_403(client, make_user, auth_headers):
    """Workspace inexistente é tratado com o mesmo 403 de não-membro — nunca
    um erro genérico distinto (`get_role` retorna `None` para os dois casos)."""
    user = make_user()

    response = client.post(
        "/api/v1/tasks",
        json={"title": "Tarefa", "workspace_id": str(uuid.uuid4())},
        headers=auth_headers(user),
    )

    assert response.status_code == 403


def test_create_task_nonexistent_project_returns_403(client, make_user, auth_headers):
    user = make_user()

    response = client.post(
        "/api/v1/tasks",
        json={"title": "Tarefa", "project_id": str(uuid.uuid4())},
        headers=auth_headers(user),
    )

    assert response.status_code == 403


def test_assignee_member_accepted(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    member = make_user(email="assignee-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)

    response = client.post(
        "/api/v1/tasks",
        json={
            "title": "Tarefa atribuída",
            "workspace_id": str(workspace.id),
            "assignee_id": str(member.id),
        },
        headers=auth_headers(owner),
    )

    assert response.status_code == 201
    assert response.json()["assignee_id"] == str(member.id)


def test_assignee_not_member_rejected(client, make_user, make_workspace, auth_headers):
    owner = make_user()
    outsider = make_user(email="assignee-outsider@example.com")
    workspace = make_workspace(owner=owner)

    response = client.post(
        "/api/v1/tasks",
        json={
            "title": "Tarefa",
            "workspace_id": str(workspace.id),
            "assignee_id": str(outsider.id),
        },
        headers=auth_headers(owner),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


def test_assignee_nonexistent_user_rejected(client, make_user, make_workspace, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)

    response = client.post(
        "/api/v1/tasks",
        json={
            "title": "Tarefa",
            "workspace_id": str(workspace.id),
            "assignee_id": str(uuid.uuid4()),
        },
        headers=auth_headers(owner),
    )

    assert response.status_code == 400


def test_task_creation_isolated_between_workspaces(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    """Ser membro do workspace A não permite criar tarefa no workspace B."""
    owner = make_user()
    member = make_user(email="cross-ws-member@example.com")
    workspace_a = make_workspace(owner=owner, name="WS A")
    workspace_b = make_workspace(owner=owner, name="WS B")
    add_workspace_member(workspace=workspace_a, user=member, role=WorkspaceRole.MEMBER)

    response = client.post(
        "/api/v1/tasks",
        json={"title": "Tarefa cruzada", "workspace_id": str(workspace_b.id)},
        headers=auth_headers(member),
    )

    assert response.status_code == 403
