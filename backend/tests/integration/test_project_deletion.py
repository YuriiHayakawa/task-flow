"""T067 [US4] — exclusão de projeto preserva tarefas: `project_id` vira `null`,
workspace mantido, tarefas nunca removidas (refinamento #6, data-model.md).

Cobre: contracts/projects-and-tasks.md (`DELETE /api/v1/projects/{project_id}`)."""

from app.enums.task_status import TaskStatus
from app.models.task import Task


def test_delete_project_preserves_tasks_and_nulls_project_id(
    client, make_user, make_workspace, make_project, make_task, auth_headers, db_session
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace)
    task1 = make_task(creator=owner, workspace=workspace, project=project, title="T1")
    task2 = make_task(creator=owner, workspace=workspace, project=project, title="T2")

    response = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers(owner))

    assert response.status_code == 204

    db_session.expire_all()
    reloaded_task1 = db_session.get(Task, task1.id)
    reloaded_task2 = db_session.get(Task, task2.id)
    assert reloaded_task1 is not None
    assert reloaded_task2 is not None
    assert reloaded_task1.project_id is None
    assert reloaded_task2.project_id is None
    # Workspace da tarefa é mantido — ela vira uma tarefa colaborativa direta
    # do workspace, não uma tarefa pessoal nem órfã.
    assert reloaded_task1.workspace_id == workspace.id
    assert reloaded_task2.workspace_id == workspace.id


def test_delete_project_not_blocked_by_active_tasks(
    client, make_user, make_workspace, make_project, make_task, auth_headers
):
    """`count_by_project` nunca condiciona a exclusão — mesmo com tarefas
    ativas vinculadas, o Owner/Admin sempre pode excluir o projeto."""
    owner = make_user()
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace)
    make_task(creator=owner, workspace=workspace, project=project, status=TaskStatus.IN_PROGRESS)
    make_task(creator=owner, workspace=workspace, project=project, status=TaskStatus.PENDING)

    response = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers(owner))

    assert response.status_code == 204


def test_delete_project_with_no_tasks_succeeds(
    client, make_user, make_workspace, make_project, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace)

    response = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers(owner))

    assert response.status_code == 204


def test_delete_project_does_not_remove_workspace(
    client, make_user, make_workspace, make_project, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace)

    client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers(owner))

    response = client.get(f"/api/v1/workspaces/{workspace.id}", headers=auth_headers(owner))
    assert response.status_code == 200
