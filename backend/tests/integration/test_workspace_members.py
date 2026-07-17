"""T055 [US3] — gestão de membros: adicionar, promover/rebaixar, remover, e o
bloqueio de remoção de membro responsável por tarefas ativas até reatribuição.

Cobre: FR-014, FR-015, FR-016, FR-019, FR-024, FR-025."""

from app.enums.task_status import TaskStatus
from app.enums.workspace_role import WorkspaceRole


def test_list_members_visible_to_any_role(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    member = make_user(email="list-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)

    response = client.get(f"/api/v1/workspaces/{workspace.id}/members", headers=auth_headers(member))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    emails = {item["email"] for item in body["items"]}
    assert emails == {owner.email, member.email}


def test_add_member_allowed_for_owner_and_admin(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    admin = make_user(email="adder-admin@example.com")
    new_member = make_user(email="new-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/members",
        json={"user_id": str(new_member.id)},
        headers=auth_headers(admin),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == new_member.email
    assert body["role"] == "MEMBER"


def test_add_member_forbidden_for_plain_member(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    member = make_user(email="cant-add@example.com")
    someone = make_user(email="someone@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/members",
        json={"user_id": str(someone.id)},
        headers=auth_headers(member),
    )

    assert response.status_code == 403


def test_add_member_rejects_duplicate(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    member = make_user(email="already-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/members",
        json={"user_id": str(member.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 409


def test_add_member_rejects_role_other_than_member(client, make_user, make_workspace, auth_headers):
    owner = make_user()
    candidate = make_user(email="candidate-role@example.com")
    workspace = make_workspace(owner=owner)

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/members",
        json={"user_id": str(candidate.id), "role": "ADMIN"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 422


def test_owner_promotes_member_to_admin(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    member = make_user(email="promote-me@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)

    response = client.patch(
        f"/api/v1/workspaces/{workspace.id}/members/{member.id}/role",
        json={"role": "ADMIN"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_admin_cannot_promote_or_demote(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    admin = make_user(email="admin-cant-promote@example.com")
    member = make_user(email="target-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)

    response = client.patch(
        f"/api/v1/workspaces/{workspace.id}/members/{member.id}/role",
        json={"role": "ADMIN"},
        headers=auth_headers(admin),
    )

    assert response.status_code == 403


def test_role_update_rejects_owner_value(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    member = make_user(email="cant-become-owner@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)

    response = client.patch(
        f"/api/v1/workspaces/{workspace.id}/members/{member.id}/role",
        json={"role": "OWNER"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 422


def test_no_one_can_alter_the_owner_role(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    admin = make_user(email="admin-vs-owner@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)

    # Nem o próprio Owner pode se "rebaixar" por esta rota (deve usar transfer-ownership).
    response = client.patch(
        f"/api/v1/workspaces/{workspace.id}/members/{owner.id}/role",
        json={"role": "ADMIN"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 403


def test_owner_and_admin_remove_a_member(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    admin = make_user(email="remover-admin@example.com")
    member = make_user(email="removable-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)

    response = client.delete(
        f"/api/v1/workspaces/{workspace.id}/members/{member.id}", headers=auth_headers(admin)
    )

    assert response.status_code == 204


def test_member_cannot_remove_anyone(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    member = make_user(email="powerless-member@example.com")
    other = make_user(email="other-target@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=other, role=WorkspaceRole.MEMBER)

    response = client.delete(
        f"/api/v1/workspaces/{workspace.id}/members/{other.id}", headers=auth_headers(member)
    )

    assert response.status_code == 403


def test_admin_cannot_remove_another_admin(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    admin_a = make_user(email="admin-a@example.com")
    admin_b = make_user(email="admin-b@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin_a, role=WorkspaceRole.ADMIN)
    add_workspace_member(workspace=workspace, user=admin_b, role=WorkspaceRole.ADMIN)

    response = client.delete(
        f"/api/v1/workspaces/{workspace.id}/members/{admin_b.id}", headers=auth_headers(admin_a)
    )

    assert response.status_code == 403


def test_owner_can_remove_an_admin(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    admin = make_user(email="removable-admin@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)

    response = client.delete(
        f"/api/v1/workspaces/{workspace.id}/members/{admin.id}", headers=auth_headers(owner)
    )

    assert response.status_code == 204


def test_cannot_remove_the_owner(
    client, make_user, make_workspace, add_workspace_member, auth_headers
):
    owner = make_user()
    admin = make_user(email="cant-remove-owner@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)

    response = client.delete(
        f"/api/v1/workspaces/{workspace.id}/members/{owner.id}", headers=auth_headers(admin)
    )

    assert response.status_code == 403


def test_remove_member_blocked_while_responsible_for_active_tasks(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    member = make_user(email="busy-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    make_task(creator=owner, assignee=member, workspace=workspace, status=TaskStatus.IN_PROGRESS)

    response = client.delete(
        f"/api/v1/workspaces/{workspace.id}/members/{member.id}", headers=auth_headers(owner)
    )

    assert response.status_code == 409
    details = response.json()["error"]["details"]
    assert len(details) == 1


def test_remove_member_succeeds_after_reassigning_active_tasks(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    member = make_user(email="busy-member-2@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=member, workspace=workspace, status=TaskStatus.PENDING)

    # Reatribui a tarefa ao Owner antes de remover o membro.
    task.assignee_id = owner.id
    db_session.flush()

    response = client.delete(
        f"/api/v1/workspaces/{workspace.id}/members/{member.id}", headers=auth_headers(owner)
    )

    assert response.status_code == 204


def test_remove_member_not_blocked_by_completed_task(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    member = make_user(email="member-with-done-task@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    make_task(creator=owner, assignee=member, workspace=workspace, status=TaskStatus.DONE)

    response = client.delete(
        f"/api/v1/workspaces/{workspace.id}/members/{member.id}", headers=auth_headers(owner)
    )

    assert response.status_code == 204
