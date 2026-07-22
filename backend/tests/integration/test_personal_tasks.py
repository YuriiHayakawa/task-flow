"""T038 [US1] — CRUD de tarefas pessoais (criar/listar/editar/concluir/reabrir).

Cobre: FR-005 a FR-011, FR-059, invariantes de tarefa pessoal (data-model.md)."""

from datetime import datetime, timezone

from app.enums.task_status import TaskStatus


def test_create_personal_task_defaults_assignee_to_creator(client, make_user, auth_headers):
    user = make_user()
    headers = auth_headers(user)

    response = client.post(
        "/api/v1/tasks",
        json={"title": "Organizar a semana", "priority": "HIGH"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Organizar a semana"
    assert body["status"] == "PENDING"
    assert body["priority"] == "HIGH"
    assert body["assignee_id"] == str(user.id)
    assert body["creator_id"] == str(user.id)
    assert body["workspace_id"] is None
    assert body["project_id"] is None


def test_create_personal_task_rejects_assignee_different_from_creator(
    client, make_user, auth_headers
):
    user = make_user()
    other = make_user(email="other@example.com")
    headers = auth_headers(user)

    response = client.post(
        "/api/v1/tasks",
        json={"title": "Tarefa de outro", "assignee_id": str(other.id)},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


def test_list_personal_tasks_returns_only_own_tasks(client, make_user, make_task, auth_headers):
    user = make_user()
    other = make_user(email="other2@example.com")
    make_task(creator=user, title="Minha tarefa")
    make_task(creator=other, title="Tarefa alheia")
    headers = auth_headers(user)

    response = client.get("/api/v1/tasks", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "Minha tarefa"


def test_list_personal_tasks_empty_for_new_user(client, make_user, auth_headers):
    user = make_user()
    headers = auth_headers(user)

    response = client.get("/api/v1/tasks", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_get_personal_task_by_id(client, make_user, make_task, auth_headers):
    user = make_user()
    task = make_task(creator=user, title="Detalhe")
    headers = auth_headers(user)

    response = client.get(f"/api/v1/tasks/{task.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["title"] == "Detalhe"


def test_get_other_users_personal_task_returns_404(client, make_user, make_task, auth_headers):
    owner = make_user()
    other = make_user(email="viewer@example.com")
    task = make_task(creator=owner, title="Privada")
    headers = auth_headers(other)

    response = client.get(f"/api/v1/tasks/{task.id}", headers=headers)

    assert response.status_code == 404


def test_update_editable_fields(client, make_user, make_task, auth_headers):
    user = make_user()
    task = make_task(creator=user)
    headers = auth_headers(user)

    response = client.patch(
        f"/api/v1/tasks/{task.id}",
        json={
            "title": "Novo título",
            "description": "Nova descrição",
            "priority": "URGENT",
            "due_date": "2026-08-01",
        },
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Novo título"
    assert body["description"] == "Nova descrição"
    assert body["priority"] == "URGENT"
    assert body["due_date"] == "2026-08-01"


def test_update_task_status_to_done_sets_completed_at(client, make_user, make_task, auth_headers):
    user = make_user()
    task = make_task(creator=user)
    headers = auth_headers(user)

    response = client.patch(f"/api/v1/tasks/{task.id}", json={"status": "DONE"}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DONE"
    assert body["completed_at"] is not None


def test_reopen_task_clears_completed_at(client, make_user, make_task, auth_headers, db_session):
    user = make_user()
    task = make_task(creator=user, status=TaskStatus.DONE)
    task.completed_at = datetime.now(timezone.utc)
    db_session.flush()
    headers = auth_headers(user)

    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"status": "PENDING"}, headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["completed_at"] is None


def test_update_rejects_reassigning_personal_task(client, make_user, make_task, auth_headers):
    user = make_user()
    other = make_user(email="cant-assign@example.com")
    task = make_task(creator=user)
    headers = auth_headers(user)

    response = client.patch(
        f"/api/v1/tasks/{task.id}", json={"assignee_id": str(other.id)}, headers=headers
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


def test_update_other_users_personal_task_returns_404(client, make_user, make_task, auth_headers):
    owner = make_user()
    other = make_user(email="cant-edit@example.com")
    task = make_task(creator=owner)
    headers = auth_headers(other)

    response = client.patch(f"/api/v1/tasks/{task.id}", json={"title": "Hack"}, headers=headers)

    assert response.status_code == 404
