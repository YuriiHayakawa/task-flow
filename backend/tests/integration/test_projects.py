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
    assert body["is_member"] is True


def test_create_project_adds_creator_as_project_member(
    client, make_user, make_workspace, auth_headers
):
    """003-membros-projeto/FR-003: quem cria o projeto já entra como seu
    primeiro membro, na mesma transação."""
    owner = make_user()
    workspace = make_workspace(owner=owner)

    create_response = client.post(
        f"/api/v1/workspaces/{workspace.id}/projects",
        json={"name": "Projeto Beta"},
        headers=auth_headers(owner),
    )
    project_id = create_response.json()["id"]

    members_response = client.get(
        f"/api/v1/projects/{project_id}/members", headers=auth_headers(owner)
    )

    assert members_response.status_code == 200
    body = members_response.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == owner.email


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
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_project_member,
    auth_headers,
):
    owner = make_user()
    member = make_user(email="list-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace, name="Projeto Visível")
    make_project_member(project=project, user=member)

    response = client.get(
        f"/api/v1/workspaces/{workspace.id}/projects", headers=auth_headers(member)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Projeto Visível"
    assert body["items"][0]["is_member"] is True


def test_list_projects_hides_non_member_projects_from_member(
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_project_member,
    auth_headers,
):
    """003-membros-projeto/US2: um Member comum só vê os projetos dos quais
    é membro explícito — o outro projeto do mesmo workspace fica totalmente
    ausente da listagem."""
    owner = make_user()
    member = make_user(email="list-member-2@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project_a = make_project(workspace=workspace, name="Projeto A")
    make_project(workspace=workspace, name="Projeto B")
    make_project_member(project=project_a, user=member)

    response = client.get(
        f"/api/v1/workspaces/{workspace.id}/projects", headers=auth_headers(member)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Projeto A"


def test_list_projects_admin_sees_all_with_is_member_flag(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    """003-membros-projeto/US3: Admin vê a listagem completa (mesmo projetos
    dos quais não participa), com `is_member` indicando quais pode abrir."""
    owner = make_user()
    admin = make_user(email="list-admin@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    make_project(workspace=workspace, name="Projeto Sem Acesso")

    response = client.get(
        f"/api/v1/workspaces/{workspace.id}/projects", headers=auth_headers(admin)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["is_member"] is False


def test_list_projects_owner_sees_all_as_member(
    client, make_user, make_workspace, make_project, auth_headers
):
    """003-membros-projeto/US3: Owner vê tudo com `is_member=True`, mesmo
    sem nunca ter sido adicionado explicitamente."""
    owner = make_user()
    workspace = make_workspace(owner=owner)
    make_project(workspace=workspace, name="Projeto do Owner")

    response = client.get(
        f"/api/v1/workspaces/{workspace.id}/projects", headers=auth_headers(owner)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["is_member"] is True


def test_list_projects_outsider_returns_404(client, make_user, make_workspace, auth_headers):
    owner = make_user()
    outsider = make_user(email="outsider-list@example.com")
    workspace = make_workspace(owner=owner)

    response = client.get(
        f"/api/v1/workspaces/{workspace.id}/projects", headers=auth_headers(outsider)
    )

    assert response.status_code == 404


def test_get_project_visible_to_member(
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_project_member,
    auth_headers,
):
    owner = make_user()
    member = make_user(email="get-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)
    make_project_member(project=project, user=member)

    response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers(member))

    assert response.status_code == 200
    assert response.json()["id"] == str(project.id)
    assert response.json()["is_member"] is True


def test_get_project_not_member_returns_404(
    client, make_user, make_workspace, make_project, auth_headers
):
    owner = make_user()
    outsider = make_user(email="outsider-get@example.com")
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace)

    response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers(outsider))

    assert response.status_code == 404


def test_get_project_workspace_member_without_project_access_returns_404(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    """003-membros-projeto/US2: ser membro do WORKSPACE não basta mais —
    sem ser membro explícito do PROJETO, o acesso é recusado (`404`, nunca
    `403` — nunca confirma a existência do projeto a quem não tem acesso)."""
    owner = make_user()
    member = make_user(email="get-member-no-access@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)

    response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers(member))

    assert response.status_code == 404


def test_get_project_owner_without_explicit_membership(
    client, make_user, make_workspace, make_project, auth_headers
):
    """003-membros-projeto/US3: Owner acessa mesmo sem nunca ter sido
    adicionado como `ProjectMember` explícito."""
    owner = make_user()
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace)

    response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers(owner))

    assert response.status_code == 200
    assert response.json()["is_member"] is True


def test_get_project_admin_without_membership_returns_404(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    """003-membros-projeto/US3: Admin vê o projeto na listagem (ver testes
    de `list_projects` acima) mas não abre o conteúdo sem ser membro."""
    owner = make_user()
    admin = make_user(email="get-admin-no-access@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    project = make_project(workspace=workspace)

    response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers(admin))

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
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_project_member,
    auth_headers,
):
    owner = make_user()
    admin = make_user(email="admin-update-project@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    project = make_project(workspace=workspace)
    make_project_member(project=project, user=admin)

    response = client.patch(
        f"/api/v1/projects/{project.id}",
        json={"name": "Editado pelo Admin"},
        headers=auth_headers(admin),
    )

    assert response.status_code == 200


def test_update_project_admin_without_membership_returns_404(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    """003-membros-projeto/US1/FR-004: Admin que não é membro do projeto
    nem chega à checagem de role — barrado antes por `require_project_visible`."""
    owner = make_user()
    admin = make_user(email="admin-update-no-access@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    project = make_project(workspace=workspace)

    response = client.patch(
        f"/api/v1/projects/{project.id}",
        json={"name": "Não deveria funcionar"},
        headers=auth_headers(admin),
    )

    assert response.status_code == 404


def test_update_project_forbidden_for_member(
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_project_member,
    auth_headers,
):
    owner = make_user()
    member = make_user(email="member-update-project@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)
    make_project_member(project=project, user=member)

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
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_project_member,
    auth_headers,
):
    owner = make_user()
    member = make_user(email="member-delete-project@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)
    make_project_member(project=project, user=member)

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
