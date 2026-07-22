"""T066 [US4] — CRUD de projeto e matriz de permissões Owner/Admin/Member.

Cobre: FR-020, FR-022, FR-023, FR-026, contracts/projects-and-tasks.md."""

from app.enums.workspace_role import WorkspaceRole


def test_create_project_owner(client, make_user, make_workspace, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/projects",
        json={"name": "Projeto Alpha", "description": "desc"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Projeto Alpha"
    assert body["description"] == "desc"
    assert body["workspace_id"] == str(workspace.id)


def test_create_project_admin(client, make_user, make_workspace, add_workspace_member, auth_headers):
    owner = make_user()
    admin = make_user(email="admin-project@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/projects",
        json={"name": "Projeto Admin"},
        headers=auth_headers(admin),
    )

    assert response.status_code == 201


def test_create_project_forbidden_for_member(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    member = make_user(email="member-project@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/projects",
        json={"name": "Não deveria existir"},
        headers=auth_headers(member),
    )

    assert response.status_code == 403


def test_create_project_outsider_returns_404(client, make_user, make_workspace, auth_headers):
    owner = make_user()
    outsider = make_user(email="outsider-project@example.com")
    workspace = make_workspace(owner=owner)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/projects",
        json={"name": "Não deveria existir"},
        headers=auth_headers(outsider),
    )

    assert response.status_code == 404


def test_create_project_requires_authentication(client, make_user, make_workspace):
    owner = make_user()
    workspace = make_workspace(owner=owner)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/projects", json={"name": "Projeto"}
    )

    assert response.status_code == 401


def test_create_project_rejects_empty_name(client, make_user, make_workspace, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/projects",
        json={"name": ""},
        headers=auth_headers(owner),
    )

    assert response.status_code == 422


def test_list_projects_visible_to_member(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    owner = make_user()
    member = make_user(email="list-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    make_project(workspace=workspace, name="Projeto Visível")

    response = client.get(
        f"/api/v1/workspaces/{workspace.id}/projects", headers=auth_headers(member)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Projeto Visível"


def test_list_projects_outsider_returns_404(client, make_user, make_workspace, auth_headers):
    owner = make_user()
    outsider = make_user(email="outsider-list@example.com")
    workspace = make_workspace(owner=owner)

    response = client.get(
        f"/api/v1/workspaces/{workspace.id}/projects", headers=auth_headers(outsider)
    )

    assert response.status_code == 404


def test_get_project_visible_to_member(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    owner = make_user()
    member = make_user(email="get-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)

    response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers(member))

    assert response.status_code == 200
    assert response.json()["id"] == str(project.id)


def test_get_project_not_member_returns_404(
    client, make_user, make_workspace, make_project, auth_headers
):
    owner = make_user()
    outsider = make_user(email="outsider-get@example.com")
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace)

    response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers(outsider))

    assert response.status_code == 404


def test_get_project_nonexistent_returns_404(client, make_user, auth_headers):
    import uuid

    user = make_user()
    response = client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=auth_headers(user))

    assert response.status_code == 404


def test_update_project_allowed_for_owner_partial(
    client, make_user, make_workspace, make_project, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace, name="Original", description="Descrição original")

    response = client.patch(
        f"/api/v1/projects/{project.id}",
        json={"name": "Renomeado"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renomeado"
    assert body["description"] == "Descrição original"  # não enviado, preservado


def test_update_project_allowed_for_admin(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    owner = make_user()
    admin = make_user(email="admin-update-project@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    project = make_project(workspace=workspace)

    response = client.patch(
        f"/api/v1/projects/{project.id}",
        json={"name": "Editado pelo Admin"},
        headers=auth_headers(admin),
    )

    assert response.status_code == 200


def test_update_project_forbidden_for_member(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    owner = make_user()
    member = make_user(email="member-update-project@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)

    response = client.patch(
        f"/api/v1/projects/{project.id}",
        json={"name": "Não deveria funcionar"},
        headers=auth_headers(member),
    )

    assert response.status_code == 403


def test_update_project_outsider_returns_404(
    client, make_user, make_workspace, make_project, auth_headers
):
    owner = make_user()
    outsider = make_user(email="outsider-update@example.com")
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace)

    response = client.patch(
        f"/api/v1/projects/{project.id}",
        json={"name": "Não deveria funcionar"},
        headers=auth_headers(outsider),
    )

    assert response.status_code == 404


def test_delete_project_forbidden_for_member(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    owner = make_user()
    member = make_user(email="member-delete-project@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)

    response = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers(member))

    assert response.status_code == 403


def test_delete_project_allowed_for_owner(
    client, make_user, make_workspace, make_project, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace)

    response = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers(owner))

    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers(owner))
    assert get_response.status_code == 404


def test_project_isolated_between_workspaces(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    """Um membro de um workspace nunca acessa projeto de OUTRO workspace, mesmo
    sendo Owner de um deles (isolamento cruzado, FR-023)."""
    owner_a = make_user()
    owner_b = make_user(email="owner-b@example.com")
    workspace_a = make_workspace(owner=owner_a, name="WS A")
    workspace_b = make_workspace(owner=owner_b, name="WS B")
    project_b = make_project(workspace=workspace_b, name="Projeto de B")

    response = client.get(f"/api/v1/projects/{project_b.id}", headers=auth_headers(owner_a))

    assert response.status_code == 404
