"""T048 [US2] — dashboard: contagens por status, atrasada/vencendo hoje
(APP_TIMEZONE), estado vazio, isolamento entre usuários.

Cobre: FR-047 a FR-050, FR-011, research.md #7/#9, spec.md US2 (cenários 1-5;
o cenário 6 — combinar com tarefas de workspace — chega na US3/US4, T065)."""

from datetime import timedelta

from app.enums.task_status import TaskStatus
from app.utils.timezone import today_in_app_timezone


def test_dashboard_empty_for_user_without_tasks(client, make_user, auth_headers):
    user = make_user()
    headers = auth_headers(user)

    response = client.get("/api/v1/dashboard", headers=headers)

    assert response.status_code == 200
    assert response.json()["counts"] == {
        "pending": 0,
        "in_progress": 0,
        "done": 0,
        "overdue": 0,
        "due_today": 0,
    }


def test_dashboard_counts_tasks_by_status(client, make_user, make_task, auth_headers):
    user = make_user()
    make_task(creator=user, title="P1", status=TaskStatus.PENDING)
    make_task(creator=user, title="P2", status=TaskStatus.PENDING)
    make_task(creator=user, title="IP1", status=TaskStatus.IN_PROGRESS)
    make_task(creator=user, title="D1", status=TaskStatus.DONE)
    headers = auth_headers(user)

    response = client.get("/api/v1/dashboard", headers=headers)

    assert response.status_code == 200
    counts = response.json()["counts"]
    assert counts["pending"] == 2
    assert counts["in_progress"] == 1
    assert counts["done"] == 1


def test_dashboard_counts_overdue_task_not_done(client, make_user, make_task, auth_headers):
    user = make_user()
    yesterday = today_in_app_timezone() - timedelta(days=1)
    make_task(creator=user, status=TaskStatus.PENDING, due_date=yesterday)
    headers = auth_headers(user)

    response = client.get("/api/v1/dashboard", headers=headers)

    counts = response.json()["counts"]
    assert counts["overdue"] == 1
    assert counts["due_today"] == 0


def test_dashboard_counts_task_due_today(client, make_user, make_task, auth_headers):
    user = make_user()
    today = today_in_app_timezone()
    make_task(creator=user, status=TaskStatus.IN_PROGRESS, due_date=today)
    headers = auth_headers(user)

    response = client.get("/api/v1/dashboard", headers=headers)

    counts = response.json()["counts"]
    assert counts["due_today"] == 1
    assert counts["overdue"] == 0


def test_dashboard_done_task_with_past_due_date_is_not_overdue(
    client, make_user, make_task, auth_headers
):
    """Uma tarefa concluída nunca conta como atrasada, mesmo com prazo vencido
    (FR-011: atrasada/vencendo hoje são subconjuntos de tarefas NÃO concluídas)."""
    user = make_user()
    yesterday = today_in_app_timezone() - timedelta(days=1)
    make_task(creator=user, status=TaskStatus.DONE, due_date=yesterday)
    headers = auth_headers(user)

    response = client.get("/api/v1/dashboard", headers=headers)

    counts = response.json()["counts"]
    assert counts["overdue"] == 0
    assert counts["due_today"] == 0
    assert counts["done"] == 1


def test_dashboard_excludes_other_users_personal_tasks(
    client, make_user, make_task, auth_headers
):
    user = make_user()
    other = make_user(email="other-dashboard@example.com")
    make_task(creator=other, status=TaskStatus.PENDING)
    headers = auth_headers(user)

    response = client.get("/api/v1/dashboard", headers=headers)

    assert response.json()["counts"]["pending"] == 0


def test_dashboard_requires_authentication(client):
    response = client.get("/api/v1/dashboard")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"
