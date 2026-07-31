"""T112/T114 [US13] — administração de usuários da plataforma via HTTP:
listagem paginada, ativação/desativação, autorização exclusiva ao System
Admin, e a garantia de que ser System Admin não concede nenhum acesso a
workspaces/projetos/tarefas (FR-044 a FR-046).

Cobre: FR-043 a FR-046, contracts/auth-and-users.md (`GET /admin/users`,
`PATCH /admin/users/{user_id}/status`).

Nota: `GET /admin/users` reflete toda a tabela `users`, que pode conter
registros commitados por outras suítes de concorrência (ver
`test_user_repository.py`) — asserções de contagem usam deltas/membership,
não números absolutos."""

import uuid

from app.enums.workspace_role import WorkspaceRole


# --- GET /admin/users -----------------------------------------------------------


def test_list_users_as_system_admin_success(client, make_user, auth_headers):
    admin = make_user(email="admin-list@example.com", is_system_admin=True)
    target = make_user(email="target-list@example.com")

    response = client.get("/api/v1/admin/users", headers=auth_headers(admin))

    assert response.status_code == 200
    body = response.json()
    item_ids = {item["id"] for item in body["items"]}
    assert str(target.id) in item_ids
    assert str(admin.id) in item_ids


def test_list_users_shows_status(client, make_user, auth_headers):
    admin = make_user(email="admin-status@example.com", is_system_admin=True)
    active_user = make_user(email="active-status@example.com", is_active=True)
    inactive_user = make_user(email="inactive-status@example.com", is_active=False)

    response = client.get("/api/v1/admin/users", headers=auth_headers(admin))

    items_by_id = {item["id"]: item for item in response.json()["items"]}
    assert items_by_id[str(active_user.id)]["is_active"] is True
    assert items_by_id[str(inactive_user.id)]["is_active"] is False


def test_list_users_filters_by_is_active(client, make_user, auth_headers):
    admin = make_user(email="admin-filter@example.com", is_system_admin=True)
    active_user = make_user(email="active-filter@example.com", is_active=True)
    inactive_user = make_user(email="inactive-filter@example.com", is_active=False)

    response = client.get(
        "/api/v1/admin/users", params={"is_active": "false"}, headers=auth_headers(admin)
    )

    item_ids = {item["id"] for item in response.json()["items"]}
    assert str(inactive_user.id) in item_ids
    assert str(active_user.id) not in item_ids


def test_list_users_forbidden_for_non_admin(client, make_user, auth_headers):
    plain_user = make_user(email="plain-list-admin@example.com")

    response = client.get("/api/v1/admin/users", headers=auth_headers(plain_user))

    assert response.status_code == 403


def test_list_users_response_never_exposes_password_hash(client, make_user, auth_headers):
    admin = make_user(email="admin-no-hash@example.com", is_system_admin=True)
    make_user(email="target-no-hash@example.com")

    response = client.get("/api/v1/admin/users", headers=auth_headers(admin))

    for item in response.json()["items"]:
        assert "password_hash" not in item


# --- PATCH /admin/users/{user_id}/status ----------------------------------------


def test_deactivate_active_user(client, make_user, auth_headers):
    admin = make_user(email="admin-deactivate@example.com", is_system_admin=True)
    target = make_user(email="target-deactivate@example.com", is_active=True)

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/status",
        json={"is_active": False},
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_deactivated_user_cannot_login(client, make_user, auth_headers):
    admin = make_user(email="admin-login-block@example.com", is_system_admin=True)
    target = make_user(
        email="target-login-block@example.com", password="supersecret123", is_active=True
    )

    client.patch(
        f"/api/v1/admin/users/{target.id}/status",
        json={"is_active": False},
        headers=auth_headers(admin),
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": target.email, "password": "supersecret123"},
    )

    assert login_response.status_code == 403
    assert login_response.json()["error"]["code"] == "ACCOUNT_DISABLED"


def test_reactivate_disabled_user_restores_login(client, make_user, auth_headers):
    admin = make_user(email="admin-reactivate@example.com", is_system_admin=True)
    target = make_user(
        email="target-reactivate@example.com", password="supersecret123", is_active=False
    )

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/status",
        json={"is_active": True},
        headers=auth_headers(admin),
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": target.email, "password": "supersecret123"},
    )
    assert login_response.status_code == 200


def test_update_status_forbidden_for_non_admin(client, make_user, auth_headers):
    plain_user = make_user(email="plain-status@example.com")
    target = make_user(email="target-status-forbidden@example.com")

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/status",
        json={"is_active": False},
        headers=auth_headers(plain_user),
    )

    assert response.status_code == 403


def test_update_status_nonexistent_user_returns_404(client, make_user, auth_headers):
    admin = make_user(email="admin-404@example.com", is_system_admin=True)

    response = client.patch(
        f"/api/v1/admin/users/{uuid.uuid4()}/status",
        json={"is_active": False},
        headers=auth_headers(admin),
    )

    assert response.status_code == 404


def test_update_status_does_not_accept_name_or_email(client, make_user, auth_headers):
    """FR-045: o System Admin não edita nome/e-mail — só o status da conta."""
    admin = make_user(email="admin-no-name-edit@example.com", is_system_admin=True)
    target = make_user(email="target-no-name-edit@example.com", name="Nome Original")

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/status",
        json={"is_active": False, "name": "Nome Hackeado"},
        headers=auth_headers(admin),
    )

    # campo extra é ignorado (schema não usa extra="forbid" aqui) — o que
    # importa é que o nome não muda:
    assert response.status_code == 200
    assert response.json()["name"] == "Nome Original"


# --- FR-044/FR-046: System Admin não ganha acesso a workspaces ------------------


def test_system_admin_has_no_access_to_workspace_without_membership(
    client, make_user, make_workspace, auth_headers
):
    admin = make_user(email="admin-no-workspace-access@example.com", is_system_admin=True)
    owner = make_user(email="owner-no-admin-access@example.com")
    workspace = make_workspace(owner=owner)

    response = client.get(f"/api/v1/workspaces/{workspace.id}", headers=auth_headers(admin))

    assert response.status_code == 404


def test_system_admin_cannot_edit_workspace_without_membership(
    client, make_user, make_workspace, auth_headers
):
    admin = make_user(email="admin-no-workspace-edit@example.com", is_system_admin=True)
    owner = make_user(email="owner-no-admin-edit@example.com")
    workspace = make_workspace(owner=owner)

    response = client.patch(
        f"/api/v1/workspaces/{workspace.id}",
        json={"name": "Nome alterado pelo admin"},
        headers=auth_headers(admin),
    )

    assert response.status_code == 404


def test_system_admin_cannot_edit_task_without_membership(
    client, make_user, make_workspace, make_task, auth_headers
):
    admin = make_user(email="admin-no-task-edit@example.com", is_system_admin=True)
    owner = make_user(email="owner-no-admin-task-edit@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"status": "DONE"}, headers=auth_headers(admin)
    )

    assert response.status_code == 404


def test_system_admin_must_join_workspace_like_any_user_to_collaborate(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    """FR-046: a única forma de o System Admin colaborar num workspace é
    ser adicionado como membro comum — depois disso, ele acessa normalmente
    (não por ser admin, mas por ser membro, como qualquer outro usuário)."""
    admin = make_user(email="admin-joins@example.com", is_system_admin=True)
    owner = make_user(email="owner-admin-joins@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.MEMBER)

    response = client.get(f"/api/v1/workspaces/{workspace.id}", headers=auth_headers(admin))

    assert response.status_code == 200


# --- Nota explícita de design: nenhum endpoint /admin aceita workspace_id/project_id/task_id


def test_admin_routes_do_not_accept_workspace_scoped_params(client, make_user, auth_headers):
    admin = make_user(email="admin-no-scoped-params@example.com", is_system_admin=True)

    openapi_response = client.get("/openapi.json", headers=auth_headers(admin))

    admin_paths = [p for p in openapi_response.json()["paths"] if p.startswith("/api/v1/admin/")]
    assert all("workspace_id" not in p and "project_id" not in p and "task_id" not in p for p in admin_paths)


# --- Regressão -----------------------------------------------------------------


def test_history_endpoint_still_works(client, make_user, make_workspace, make_task, auth_headers):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}/history", headers=auth_headers(owner))

    assert response.status_code == 200
