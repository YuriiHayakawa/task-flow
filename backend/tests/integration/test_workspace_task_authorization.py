"""T079 [US5] — GET/PATCH/DELETE /tasks/{task_id} ampliados para tarefas de
workspace via `require_task_visible`/`require_task_editor`/
`require_task_delete`, preservando o comportamento de tarefa pessoal (US1).

Cobre: plan.md ("Permissões de Edição e Exclusão"), research.md #8,
contracts/projects-and-tasks.md. `GET /tasks` (listagem) permanece fora do
escopo — isso é explicitamente Fase 8/US8."""

import uuid

from app.enums.workspace_role import WorkspaceRole
from app.models.task import Task
from app.models.task_member import TaskMember


# --- GET /tasks/{task_id} -----------------------------------------------------


def test_get_personal_task_creator_ok(client, make_user, make_task, auth_headers):
    creator = make_user()
    task = make_task(creator=creator, title="Pessoal")

    response = client.get(f"/api/v1/tasks/{task.id}", headers=auth_headers(creator))

    assert response.status_code == 200
    assert response.json()["title"] == "Pessoal"


def test_get_personal_task_other_user_returns_404(client, make_user, make_task, auth_headers):
    creator = make_user()
    other = make_user(email="other-get-personal@example.com")
    task = make_task(creator=creator)

    response = client.get(f"/api/v1/tasks/{task.id}", headers=auth_headers(other))

    assert response.status_code == 404


def test_get_workspace_task_any_member_ok(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    member = make_user(email="member-get-workspace@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace, title="De workspace")

    response = client.get(f"/api/v1/tasks/{task.id}", headers=auth_headers(member))

    assert response.status_code == 200
    assert response.json()["title"] == "De workspace"


def test_get_workspace_task_outsider_returns_404(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    outsider = make_user(email="outsider-get-workspace@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.get(f"/api/v1/tasks/{task.id}", headers=auth_headers(outsider))

    assert response.status_code == 404


def test_get_nonexistent_task_returns_404(client, make_user, auth_headers):
    user = make_user()

    response = client.get(f"/api/v1/tasks/{uuid.uuid4()}", headers=auth_headers(user))

    assert response.status_code == 404


# --- PATCH /tasks/{task_id} ----------------------------------------------------


def test_patch_personal_task_creator_ok(client, make_user, make_task, auth_headers):
    creator = make_user()
    task = make_task(creator=creator)

    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"title": "Editado"}, headers=auth_headers(creator)
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Editado"


def test_patch_personal_task_other_user_returns_404(client, make_user, make_task, auth_headers):
    creator = make_user()
    other = make_user(email="other-patch-personal@example.com")
    task = make_task(creator=creator)

    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"title": "Hack"}, headers=auth_headers(other)
    )

    assert response.status_code == 404


def test_patch_workspace_task_creator_ok(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    creator = make_user(email="creator-patch-ws@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"title": "Editado pelo criador"}, headers=auth_headers(creator)
    )

    assert response.status_code == 200


def test_patch_workspace_task_assignee_ok(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    creator = make_user(email="creator-patch-assignee@example.com")
    assignee = make_user(email="assignee-patch@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, assignee=assignee, workspace=workspace)

    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"title": "Editado pelo responsável"}, headers=auth_headers(assignee)
    )

    assert response.status_code == 200


def test_patch_workspace_task_owner_ok(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    creator = make_user(email="creator-patch-owner@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"title": "Editado pelo Owner"}, headers=auth_headers(owner)
    )

    assert response.status_code == 200


def test_patch_workspace_task_admin_ok(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    admin = make_user(email="admin-patch@example.com")
    creator = make_user(email="creator-patch-admin@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"title": "Editado pelo Admin"}, headers=auth_headers(admin)
    )

    assert response.status_code == 200


def test_patch_workspace_task_explicit_participant_forbidden(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    """Ser participante explícito NÃO concede permissão de editar — só
    criador, responsável, ou Owner/Admin (plan.md, refinamento #7)."""
    owner = make_user()
    creator = make_user(email="creator-patch-participant@example.com")
    participant = make_user(email="participant-patch@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"title": "Não deveria funcionar"}, headers=auth_headers(participant)
    )

    assert response.status_code == 403


def test_patch_workspace_task_plain_member_forbidden(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    creator = make_user(email="creator-patch-member@example.com")
    plain_member = make_user(email="plain-member-patch@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"title": "Não deveria funcionar"}, headers=auth_headers(plain_member)
    )

    assert response.status_code == 403


def test_patch_workspace_task_outsider_returns_404(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    outsider = make_user(email="outsider-patch@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"title": "Não deveria funcionar"}, headers=auth_headers(outsider)
    )

    assert response.status_code == 404


# --- DELETE /tasks/{task_id} ----------------------------------------------------


def test_delete_personal_task_creator_ok(client, make_user, make_task, auth_headers):
    creator = make_user()
    task = make_task(creator=creator)

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(creator))

    assert response.status_code == 204
    assert response.content == b""


def test_delete_personal_task_other_user_returns_404(client, make_user, make_task, auth_headers):
    creator = make_user()
    other = make_user(email="other-delete-personal@example.com")
    task = make_task(creator=creator)

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(other))

    assert response.status_code == 404


def test_delete_workspace_task_creator_ok(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    creator = make_user(email="creator-delete-ws@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(creator))

    assert response.status_code == 204


def test_delete_workspace_task_owner_ok(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    creator = make_user(email="creator-delete-owner@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(owner))

    assert response.status_code == 204


def test_delete_workspace_task_admin_ok(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    admin = make_user(email="admin-delete@example.com")
    creator = make_user(email="creator-delete-admin@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(admin))

    assert response.status_code == 204


def test_delete_workspace_task_assignee_only_forbidden(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    """O responsável isolado (não-criador) MUST NOT excluir — distinção-chave
    vs. PATCH, onde ele pode editar."""
    owner = make_user()
    creator = make_user(email="creator-delete-assignee@example.com")
    assignee = make_user(email="assignee-delete-forbidden@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, assignee=assignee, workspace=workspace)

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(assignee))

    assert response.status_code == 403


def test_delete_workspace_task_explicit_participant_forbidden(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    creator = make_user(email="creator-delete-participant@example.com")
    participant = make_user(email="participant-delete@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(participant))

    assert response.status_code == 403


def test_delete_workspace_task_plain_member_forbidden(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    creator = make_user(email="creator-delete-member@example.com")
    plain_member = make_user(email="plain-member-delete@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=creator, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=plain_member, role=WorkspaceRole.MEMBER)
    task = make_task(creator=creator, workspace=workspace)

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(plain_member))

    assert response.status_code == 403


def test_delete_workspace_task_outsider_returns_404(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    outsider = make_user(email="outsider-delete@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(outsider))

    assert response.status_code == 404


def test_delete_nonexistent_task_returns_404(client, make_user, auth_headers):
    user = make_user()

    response = client.delete(f"/api/v1/tasks/{uuid.uuid4()}", headers=auth_headers(user))

    assert response.status_code == 404


# --- Regressão específica: cascade da exclusão --------------------------------


def test_delete_workspace_task_removes_task_members(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers, db_session
):
    owner = make_user()
    participant = make_user(email="participant-cascade@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    response = client.delete(f"/api/v1/tasks/{task.id}", headers=auth_headers(owner))

    assert response.status_code == 204
    db_session.expire_all()
    assert db_session.get(Task, task.id) is None
