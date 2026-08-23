"""003-membros-projeto/US1 — gestão de membros de um projeto.

Cobre: FR-002 a FR-005, contracts/project-members.md."""

from sqlalchemy import select, text

from app.enums.task_status import TaskStatus
from app.enums.workspace_role import WorkspaceRole
from app.models.project_member import ProjectMember


def test_add_member_success(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    owner = make_user()
    target = make_user(email="add-target@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=target, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)

    response = client.post(
        f"/api/v1/projects/{project.id}/members",
        json={"user_id": str(target.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == str(target.id)
    assert body["email"] == target.email


def test_add_member_forbidden_for_project_member_with_workspace_role_member(
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_project_member,
    auth_headers,
):
    owner = make_user()
    member = make_user(email="add-member-caller@example.com")
    target = make_user(email="add-member-target@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=target, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)
    make_project_member(project=project, user=member)

    response = client.post(
        f"/api/v1/projects/{project.id}/members",
        json={"user_id": str(target.id)},
        headers=auth_headers(member),
    )

    assert response.status_code == 403


def test_add_member_admin_without_project_access_returns_404(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    """FR-004: Admin só gerencia membros de um projeto do qual já
    participa — sem isso, nem chega à checagem de role."""
    owner = make_user()
    admin = make_user(email="add-admin-no-access@example.com")
    target = make_user(email="add-admin-target@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=admin, role=WorkspaceRole.ADMIN)
    add_workspace_member(workspace=workspace, user=target, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)

    response = client.post(
        f"/api/v1/projects/{project.id}/members",
        json={"user_id": str(target.id)},
        headers=auth_headers(admin),
    )

    assert response.status_code == 404


def test_add_member_rejects_non_workspace_member(
    client, make_user, make_workspace, make_project, auth_headers
):
    """FR-002: `user_id` MUST já ser membro do workspace do projeto."""
    owner = make_user()
    outsider = make_user(email="add-outsider@example.com")
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace)

    response = client.post(
        f"/api/v1/projects/{project.id}/members",
        json={"user_id": str(outsider.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 400


def test_add_member_conflict_when_already_member(
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_project_member,
    auth_headers,
):
    owner = make_user()
    target = make_user(email="add-duplicate@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=target, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)
    make_project_member(project=project, user=target)

    response = client.post(
        f"/api/v1/projects/{project.id}/members",
        json={"user_id": str(target.id)},
        headers=auth_headers(owner),
    )

    assert response.status_code == 409


def test_list_members(
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_project_member,
    auth_headers,
):
    owner = make_user()
    member = make_user(email="list-members@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)
    make_project_member(project=project, user=member)

    response = client.get(f"/api/v1/projects/{project.id}/members", headers=auth_headers(owner))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == member.email


def test_remove_member_success(
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_project_member,
    auth_headers,
):
    owner = make_user()
    member = make_user(email="remove-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)
    make_project_member(project=project, user=member)

    response = client.delete(
        f"/api/v1/projects/{project.id}/members/{member.id}", headers=auth_headers(owner)
    )

    assert response.status_code == 204

    list_response = client.get(
        f"/api/v1/projects/{project.id}/members", headers=auth_headers(owner)
    )
    assert list_response.json()["total"] == 0


def test_remove_member_not_found(
    client, make_user, make_workspace, add_workspace_member, make_project, auth_headers
):
    owner = make_user()
    member = make_user(email="remove-not-found@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)

    response = client.delete(
        f"/api/v1/projects/{project.id}/members/{member.id}", headers=auth_headers(owner)
    )

    assert response.status_code == 404


def test_remove_member_blocked_by_active_tasks_in_project(
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_project_member,
    make_task,
    auth_headers,
):
    """003-membros-projeto/US5/FR-010."""
    owner = make_user()
    member = make_user(email="remove-blocked@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)
    make_project_member(project=project, user=member)
    task = make_task(creator=owner, assignee=member, workspace=workspace, project=project)

    response = client.delete(
        f"/api/v1/projects/{project.id}/members/{member.id}", headers=auth_headers(owner)
    )

    assert response.status_code == 409
    details = response.json()["error"]["details"]
    assert details == [{"task_id": str(task.id), "title": task.title}]


def test_remove_member_succeeds_after_task_reassigned(
    client,
    make_user,
    make_workspace,
    add_workspace_member,
    make_project,
    make_project_member,
    make_task,
    auth_headers,
):
    owner = make_user()
    member = make_user(email="remove-reassigned@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    project = make_project(workspace=workspace)
    make_project_member(project=project, user=member)
    make_task(
        creator=owner,
        assignee=member,
        workspace=workspace,
        project=project,
        status=TaskStatus.DONE,
    )

    response = client.delete(
        f"/api/v1/projects/{project.id}/members/{member.id}", headers=auth_headers(owner)
    )

    assert response.status_code == 204


def test_migration_backfill_adds_every_workspace_member_to_every_project(
    db_session, make_user, make_workspace, add_workspace_member, make_project
):
    """FR-012 (spec.md, Roteiro 6 do quickstart.md) — a mesma instrução SQL
    de backfill embutida na migração `0006_project_members` (research.md
    #4), exercitada aqui contra dados que simulam o estado ANTES dela: um
    workspace com membros e um projeto já existentes, sem nenhum
    `ProjectMember`. A suíte já aplica todas as migrações (incl. a 0006)
    uma única vez no início da sessão de teste — testar a própria execução
    de `alembic upgrade` em isolamento fugiria do padrão já estabelecido em
    `conftest.py` (nenhuma outra migração deste projeto tem teste dedicado
    nesse formato); o que importa validar é que a instrução SQL do backfill
    produz o resultado correto, o que este teste faz diretamente."""
    owner = make_user()
    member = make_user(email="migration-member@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    # `make_project` sem `creator=` não cria ProjectMember nenhum — simula
    # exatamente o estado de um projeto criado ANTES desta feature existir.
    project = make_project(workspace=workspace)

    db_session.execute(
        text(
            "INSERT INTO project_members (id, project_id, user_id, created_at) "
            "SELECT gen_random_uuid(), p.id, wm.user_id, now() "
            "FROM projects p "
            "JOIN workspace_members wm ON wm.workspace_id = p.workspace_id "
            "WHERE p.id = :project_id"
        ),
        {"project_id": project.id},
    )
    db_session.flush()

    member_ids = set(
        db_session.scalars(
            select(ProjectMember.user_id).where(ProjectMember.project_id == project.id)
        )
    )

    assert member_ids == {owner.id, member.id}
