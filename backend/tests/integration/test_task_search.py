"""T089 [US8] — busca/filtros/ordenação de tarefas via HTTP, combinados.

Cobre: FR-055 a FR-059, contracts/projects-and-tasks.md (`GET /tasks`)."""

from datetime import date, timedelta

from app.enums.task_priority import TaskPriority
from app.enums.task_status import TaskStatus
from app.enums.workspace_role import WorkspaceRole


def test_search_by_title(client, make_user, make_task, auth_headers):
    user = make_user()
    make_task(creator=user, title="Organizar reunião")
    make_task(creator=user, title="Comprar material")
    headers = auth_headers(user)

    response = client.get("/api/v1/tasks?search=reuni", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Organizar reunião"


def test_filter_by_status(client, make_user, make_task, auth_headers):
    user = make_user()
    make_task(creator=user, title="A", status=TaskStatus.PENDING)
    make_task(creator=user, title="B", status=TaskStatus.DONE)
    headers = auth_headers(user)

    response = client.get("/api/v1/tasks?status=PENDING", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "A"


def test_filter_by_status_and_priority_combined(client, make_user, make_task, auth_headers):
    user = make_user()
    make_task(creator=user, title="Urgente pendente", status=TaskStatus.PENDING, priority=TaskPriority.URGENT)
    make_task(creator=user, title="Baixa pendente", status=TaskStatus.PENDING, priority=TaskPriority.LOW)
    make_task(creator=user, title="Urgente concluída", status=TaskStatus.DONE, priority=TaskPriority.URGENT)
    headers = auth_headers(user)

    response = client.get(
        "/api/v1/tasks?status=PENDING&priority=URGENT", headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Urgente pendente"


def test_filter_by_workspace_and_project(
    client, make_user, make_workspace, make_project, make_task, auth_headers
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    project = make_project(workspace=workspace)
    make_task(creator=owner, title="No projeto", workspace=workspace, project=project)
    make_task(creator=owner, title="Direto no workspace", workspace=workspace)
    headers = auth_headers(owner)

    response = client.get(
        f"/api/v1/tasks?workspace_id={workspace.id}&project_id={project.id}", headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "No projeto"


def test_filter_by_assignee(
    client, make_user, make_workspace, add_workspace_member, make_task, auth_headers
):
    owner = make_user()
    member = make_user(email="member-search-http@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    make_task(creator=owner, assignee=member, title="Do membro", workspace=workspace)
    make_task(creator=owner, assignee=owner, title="Do owner", workspace=workspace)
    headers = auth_headers(owner)

    response = client.get(f"/api/v1/tasks?assignee_id={member.id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Do membro"


def test_sort_by_due_date_ascending(client, make_user, make_task, auth_headers):
    user = make_user()
    today = date.today()
    make_task(creator=user, title="Depois", due_date=today + timedelta(days=5))
    make_task(creator=user, title="Antes", due_date=today + timedelta(days=1))
    headers = auth_headers(user)

    response = client.get("/api/v1/tasks?sort_by=due_date&sort_order=asc", headers=headers)

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert titles == ["Antes", "Depois"]


def test_sort_by_priority_semantic_order(client, make_user, make_task, auth_headers):
    user = make_user()
    make_task(creator=user, title="Baixa", priority=TaskPriority.LOW)
    make_task(creator=user, title="Urgente", priority=TaskPriority.URGENT)
    make_task(creator=user, title="Média", priority=TaskPriority.MEDIUM)
    headers = auth_headers(user)

    response = client.get("/api/v1/tasks?sort_by=priority&sort_order=asc", headers=headers)

    titles = [item["title"] for item in response.json()["items"]]
    assert titles == ["Baixa", "Média", "Urgente"]


def test_sort_by_created_at_default(client, make_user, make_task, auth_headers, db_session):
    user = make_user()
    task_1 = make_task(creator=user, title="Primeira")
    task_2 = make_task(creator=user, title="Segunda")
    task_1.created_at = task_1.created_at - timedelta(minutes=5)
    db_session.flush()
    headers = auth_headers(user)

    response = client.get("/api/v1/tasks", headers=headers)

    titles = [item["title"] for item in response.json()["items"]]
    assert titles == ["Segunda", "Primeira"]  # default: created_at desc


def test_empty_result_returns_200_with_empty_list(client, make_user, make_task, auth_headers):
    user = make_user()
    make_task(creator=user, title="Qualquer coisa")
    headers = auth_headers(user)

    response = client.get("/api/v1/tasks?search=termo-que-nao-existe", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_pagination(client, make_user, make_task, auth_headers):
    user = make_user()
    for i in range(5):
        make_task(creator=user, title=f"Tarefa {i}")
    headers = auth_headers(user)

    response = client.get("/api/v1/tasks?page=1&page_size=2", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2


def test_combined_search_filter_and_sort(client, make_user, make_task, auth_headers):
    """Cenário do teste independente da US8: busca + filtro de status +
    ordenação por prazo, tudo ao mesmo tempo."""
    user = make_user()
    today = date.today()
    make_task(
        creator=user, title="Reunião A", status=TaskStatus.PENDING, due_date=today + timedelta(days=3)
    )
    make_task(
        creator=user, title="Reunião B", status=TaskStatus.PENDING, due_date=today + timedelta(days=1)
    )
    make_task(creator=user, title="Reunião C", status=TaskStatus.DONE, due_date=today)
    make_task(creator=user, title="Outra coisa", status=TaskStatus.PENDING, due_date=today)
    headers = auth_headers(user)

    response = client.get(
        "/api/v1/tasks?search=reuni&status=PENDING&sort_by=due_date&sort_order=asc", headers=headers
    )

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert titles == ["Reunião B", "Reunião A"]


def test_visibility_never_leaks_other_users_personal_tasks(client, make_user, make_task, auth_headers):
    user = make_user()
    other = make_user(email="other-search-visibility@example.com")
    make_task(creator=other, title="Tarefa alheia")
    headers = auth_headers(user)

    response = client.get("/api/v1/tasks", headers=headers)

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_filter_by_workspace_not_a_member_of_returns_empty(
    client, make_user, make_workspace, make_task, auth_headers
):
    owner = make_user()
    outsider = make_user(email="outsider-search-filter@example.com")
    workspace = make_workspace(owner=owner)
    make_task(creator=owner, title="Tarefa alheia", workspace=workspace)
    headers = auth_headers(outsider)

    response = client.get(f"/api/v1/tasks?workspace_id={workspace.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_requires_authentication(client):
    response = client.get("/api/v1/tasks")

    assert response.status_code == 401


def test_invalid_sort_by_returns_422(client, make_user, auth_headers):
    user = make_user()

    response = client.get("/api/v1/tasks?sort_by=invalid_value", headers=auth_headers(user))

    assert response.status_code == 422


def test_invalid_status_filter_returns_422(client, make_user, auth_headers):
    user = make_user()

    response = client.get("/api/v1/tasks?status=NOT_A_STATUS", headers=auth_headers(user))

    assert response.status_code == 422
