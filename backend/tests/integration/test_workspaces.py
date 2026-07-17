"""T052 [US3] — CRUD de workspace e matriz de permissões Owner/Admin/Member.

Cobre: FR-012, FR-013, FR-017, FR-020, FR-022, FR-023, contracts/workspaces.md."""

from app.enums.workspace_role import WorkspaceRole


def test_create_workspace_creator_becomes_owner(client, make_user, auth_headers):
    user = make_user()
    headers = auth_headers(user)

    response = client.post(
        "/api/v1/workspaces",
        json={"name": "Equipe de Produto", "description": "Workspace do time"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Equipe de Produto"
    assert body["description"] == "Workspace do time"
    assert body["my_role"] == "OWNER"


def test_list_workspaces_returns_only_workspaces_user_belongs_to(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    user = make_user()
    other = make_user(email="other-ws@example.com")
    mine = make_workspace(owner=user, name="Meu workspace")
    make_workspace(owner=other, name="Workspace alheio")
    headers = auth_headers(user)

    response = client.get("/api/v1/workspaces", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Meu workspace"
    assert body["items"][0]["id"] == str(mine.id)


def test_get_workspace_visible_to_any_member_role(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    member = make_user(email="member-view@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)

    response = client.get(f"/api/v1/workspaces/{workspace.id}", headers=auth_headers(member))

    assert response.status_code == 200
    assert response.json()["my_role"] == "MEMBER"


def test_get_workspace_not_member_returns_404(client, make_user, make_workspace, auth_headers):
    owner = make_user()
    outsider = make_user(email="outsider@example.com")
    workspace = make_workspace(owner=owner)

    response = client.get(f"/api/v1/workspaces/{workspace.id}", headers=auth_headers(outsider))

    assert response.status_code == 404


def test_update_workspace_allowed_for_owner(client, make_user, make_workspace, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)

    response = client.patch(
        f"/api/v1/workspaces/{workspace.id}",
        json={"name": "Novo nome"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Novo nome"


def test_update_workspace_forbidden_for_admin(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    admin = make_user(email="admin-update@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)

    response = client.patch(
        f"/api/v1/workspaces/{workspace.id}",
        json={"name": "Não deveria funcionar"},
        headers=auth_headers(admin),
    )

    assert response.status_code == 403


def test_update_workspace_forbidden_for_member(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    member = make_user(email="member-update@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)

    response = client.patch(
        f"/api/v1/workspaces/{workspace.id}",
        json={"name": "Não deveria funcionar"},
        headers=auth_headers(member),
    )

    assert response.status_code == 403


def test_delete_workspace_allowed_for_owner(client, make_user, make_workspace, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)

    response = client.delete(f"/api/v1/workspaces/{workspace.id}", headers=auth_headers(owner))
    assert response.status_code == 204

    # Após a exclusão, o workspace não existe mais para ninguém.
    get_response = client.get(f"/api/v1/workspaces/{workspace.id}", headers=auth_headers(owner))
    assert get_response.status_code == 404


def test_delete_workspace_forbidden_for_admin(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    admin = make_user(email="admin-delete@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)

    response = client.delete(f"/api/v1/workspaces/{workspace.id}", headers=auth_headers(admin))

    assert response.status_code == 403


def test_workspace_routes_require_authentication(client, make_user, make_workspace):
    owner = make_user()
    workspace = make_workspace(owner=owner)

    response = client.get(f"/api/v1/workspaces/{workspace.id}")

    assert response.status_code == 401
