"""T010/T014/T017/T020/T023 [US1-US4] — tarefas fixas via HTTP: criar,
listar, concluir/desconcluir a ocorrência de hoje, editar, excluir,
isolamento por dono.

Cobre: FR-001 a FR-014, contracts/recurring-tasks.md
(`POST/GET /recurring-tasks`, `PATCH/DELETE /recurring-tasks/{id}`,
`POST/DELETE /recurring-tasks/{id}/completions`)."""

import uuid
from datetime import date, datetime, time
from datetime import timezone as dt_timezone

import pytest

from app.utils import timezone as timezone_module


class _FrozenDateTime(datetime):
    """`now()` sempre retorna meio-dia UTC da data configurada — meio-dia
    evita qualquer problema de virada de dia ao converter para
    `APP_TIMEZONE` (America/Sao_Paulo, UTC-3), mesmo padrão de
    `test_timezone_calculations.py`."""

    _fixed_date: date = date(2026, 1, 1)

    @classmethod
    def now(cls, tz=None):
        base = datetime.combine(cls._fixed_date, time(12, 0), tzinfo=dt_timezone.utc)
        return base.astimezone(tz) if tz is not None else base


@pytest.fixture()
def freeze_today(monkeypatch):
    """Retorna uma função para definir/mudar "hoje" durante o teste — usada
    para testar reset automático de um dia para o outro (US1, cenário 3)."""
    monkeypatch.setattr(timezone_module, "datetime", _FrozenDateTime)

    def _set(new_date: date) -> None:
        _FrozenDateTime._fixed_date = new_date

    return _set


# --- POST /recurring-tasks — US1 diária -----------------------------------------


def test_create_daily_success(client, make_user, auth_headers, freeze_today):
    user = make_user()
    freeze_today(date(2026, 8, 24))  # segunda-feira

    response = client.post(
        "/api/v1/recurring-tasks",
        json={"title": "Beber água", "recurrence_type": "DAILY"},
        headers=auth_headers(user),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Beber água"
    assert body["recurrence_type"] == "DAILY"
    assert body["weekdays"] == []
    assert body["month_day"] is None
    assert body["is_due_today"] is True
    assert body["completed_today"] is False


def test_list_recurring_tasks(client, make_user, make_recurring_task, auth_headers, freeze_today):
    user = make_user()
    freeze_today(date(2026, 8, 24))
    make_recurring_task(owner=user, title="A")
    make_recurring_task(owner=user, title="B")

    response = client.get("/api/v1/recurring-tasks", headers=auth_headers(user))

    assert response.status_code == 200
    titles = {item["title"] for item in response.json()}
    assert titles == {"A", "B"}


def test_list_isolated_by_owner(client, make_user, make_recurring_task, auth_headers, freeze_today):
    owner = make_user()
    other = make_user(email="other-list-recurring@example.com")
    freeze_today(date(2026, 8, 24))
    make_recurring_task(owner=owner, title="Da Ana")

    response = client.get("/api/v1/recurring-tasks", headers=auth_headers(other))

    assert response.status_code == 200
    assert response.json() == []


# --- POST/DELETE /recurring-tasks/{id}/completions — US1 -------------------------


def test_complete_today_success(client, make_user, make_recurring_task, auth_headers, freeze_today):
    user = make_user()
    freeze_today(date(2026, 8, 24))
    recurring_task = make_recurring_task(owner=user)

    response = client.post(
        f"/api/v1/recurring-tasks/{recurring_task.id}/completions", headers=auth_headers(user)
    )

    assert response.status_code == 201
    assert response.json()["completed_today"] is True


def test_complete_today_is_idempotent(
    client, make_user, make_recurring_task, auth_headers, freeze_today, db_session
):
    from app.models.recurring_task_completion import RecurringTaskCompletion

    user = make_user()
    freeze_today(date(2026, 8, 24))
    recurring_task = make_recurring_task(owner=user)

    client.post(f"/api/v1/recurring-tasks/{recurring_task.id}/completions", headers=auth_headers(user))
    response = client.post(
        f"/api/v1/recurring-tasks/{recurring_task.id}/completions", headers=auth_headers(user)
    )

    assert response.status_code == 201
    count = (
        db_session.query(RecurringTaskCompletion)
        .filter(RecurringTaskCompletion.recurring_task_id == recurring_task.id)
        .count()
    )
    assert count == 1


def test_uncomplete_today_success(client, make_user, make_recurring_task, auth_headers, freeze_today):
    user = make_user()
    freeze_today(date(2026, 8, 24))
    recurring_task = make_recurring_task(owner=user)
    client.post(f"/api/v1/recurring-tasks/{recurring_task.id}/completions", headers=auth_headers(user))

    response = client.delete(
        f"/api/v1/recurring-tasks/{recurring_task.id}/completions", headers=auth_headers(user)
    )

    assert response.status_code == 200
    assert response.json()["completed_today"] is False


def test_uncomplete_when_already_pending_is_noop(
    client, make_user, make_recurring_task, auth_headers, freeze_today
):
    user = make_user()
    freeze_today(date(2026, 8, 24))
    recurring_task = make_recurring_task(owner=user)

    response = client.delete(
        f"/api/v1/recurring-tasks/{recurring_task.id}/completions", headers=auth_headers(user)
    )

    assert response.status_code == 200
    assert response.json()["completed_today"] is False


def test_daily_resets_automatically_next_day(
    client, make_user, make_recurring_task, auth_headers, freeze_today
):
    """FR-006/FR-007/SC-002 — o cenário central da feature: concluir hoje não
    afeta o estado do dia seguinte, sem nenhuma ação manual."""
    user = make_user()
    freeze_today(date(2026, 8, 24))
    recurring_task = make_recurring_task(owner=user)
    client.post(f"/api/v1/recurring-tasks/{recurring_task.id}/completions", headers=auth_headers(user))

    freeze_today(date(2026, 8, 25))
    response = client.get("/api/v1/recurring-tasks", headers=auth_headers(user))

    body = next(item for item in response.json() if item["id"] == str(recurring_task.id))
    assert body["is_due_today"] is True
    assert body["completed_today"] is False


# --- POST /recurring-tasks — US2 semanal ------------------------------------------


def test_create_weekly_without_weekdays_returns_400(client, make_user, auth_headers, freeze_today):
    user = make_user()
    freeze_today(date(2026, 8, 24))

    response = client.post(
        "/api/v1/recurring-tasks",
        json={"title": "Revisar e-mails", "recurrence_type": "WEEKLY", "weekdays": []},
        headers=auth_headers(user),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


def test_create_weekly_success(client, make_user, auth_headers, freeze_today):
    user = make_user()
    freeze_today(date(2026, 8, 24))  # segunda

    response = client.post(
        "/api/v1/recurring-tasks",
        json={"title": "Revisar e-mails", "recurrence_type": "WEEKLY", "weekdays": [0, 2, 4]},
        headers=auth_headers(user),
    )

    assert response.status_code == 201
    body = response.json()
    assert sorted(body["weekdays"]) == [0, 2, 4]
    assert body["is_due_today"] is True  # segunda está entre os selecionados


def test_weekly_is_not_due_on_non_selected_day(
    client, make_user, make_recurring_task, auth_headers, freeze_today
):
    from app.enums.recurrence_type import RecurrenceType

    user = make_user()
    freeze_today(date(2026, 8, 24))
    recurring_task = make_recurring_task(
        owner=user, recurrence_type=RecurrenceType.WEEKLY, weekdays=[0, 2, 4]
    )

    freeze_today(date(2026, 8, 25))  # terça — fora do conjunto
    response = client.get("/api/v1/recurring-tasks", headers=auth_headers(user))

    body = next(item for item in response.json() if item["id"] == str(recurring_task.id))
    assert body["is_due_today"] is False


def test_complete_on_non_occurrence_day_returns_400(
    client, make_user, make_recurring_task, auth_headers, freeze_today
):
    from app.enums.recurrence_type import RecurrenceType

    user = make_user()
    freeze_today(date(2026, 8, 25))  # terça
    recurring_task = make_recurring_task(
        owner=user, recurrence_type=RecurrenceType.WEEKLY, weekdays=[0, 2, 4]
    )

    response = client.post(
        f"/api/v1/recurring-tasks/{recurring_task.id}/completions", headers=auth_headers(user)
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


# --- POST /recurring-tasks — US3 mensal -------------------------------------------


def test_create_monthly_without_month_day_returns_400(client, make_user, auth_headers, freeze_today):
    user = make_user()
    freeze_today(date(2026, 8, 24))

    response = client.post(
        "/api/v1/recurring-tasks",
        json={"title": "Pagar boleto", "recurrence_type": "MONTHLY"},
        headers=auth_headers(user),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


def test_create_monthly_day_out_of_range_returns_422(client, make_user, auth_headers, freeze_today):
    user = make_user()
    freeze_today(date(2026, 8, 24))

    response = client.post(
        "/api/v1/recurring-tasks",
        json={"title": "Pagar boleto", "recurrence_type": "MONTHLY", "month_day": 32},
        headers=auth_headers(user),
    )

    assert response.status_code == 422


def test_monthly_short_month_falls_back_to_last_day(
    client, make_user, make_recurring_task, auth_headers, freeze_today
):
    from app.enums.recurrence_type import RecurrenceType

    user = make_user()
    freeze_today(date(2026, 8, 24))
    recurring_task = make_recurring_task(
        owner=user, recurrence_type=RecurrenceType.MONTHLY, month_day=31
    )

    freeze_today(date(2026, 4, 30))  # abril tem só 30 dias
    response = client.get("/api/v1/recurring-tasks", headers=auth_headers(user))

    body = next(item for item in response.json() if item["id"] == str(recurring_task.id))
    assert body["is_due_today"] is True


# --- PATCH /recurring-tasks/{id} — US4 -------------------------------------------


def test_update_title_only(client, make_user, make_recurring_task, auth_headers, freeze_today):
    user = make_user()
    freeze_today(date(2026, 8, 24))
    recurring_task = make_recurring_task(owner=user, title="Título antigo")

    response = client.patch(
        f"/api/v1/recurring-tasks/{recurring_task.id}",
        json={"title": "Título novo"},
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Título novo"
    assert response.json()["recurrence_type"] == "DAILY"


def test_update_does_not_affect_past_completions(
    client, make_user, make_recurring_task, auth_headers, freeze_today, db_session
):
    from app.models.recurring_task_completion import RecurringTaskCompletion

    user = make_user()
    freeze_today(date(2026, 8, 24))
    recurring_task = make_recurring_task(owner=user)
    client.post(f"/api/v1/recurring-tasks/{recurring_task.id}/completions", headers=auth_headers(user))

    client.patch(
        f"/api/v1/recurring-tasks/{recurring_task.id}",
        json={"title": "Novo título"},
        headers=auth_headers(user),
    )

    completion = (
        db_session.query(RecurringTaskCompletion)
        .filter(
            RecurringTaskCompletion.recurring_task_id == recurring_task.id,
            RecurringTaskCompletion.occurrence_date == date(2026, 8, 24),
        )
        .one_or_none()
    )
    assert completion is not None


def test_update_change_type_to_weekly_without_weekdays_returns_400(
    client, make_user, make_recurring_task, auth_headers, freeze_today
):
    user = make_user()
    freeze_today(date(2026, 8, 24))
    recurring_task = make_recurring_task(owner=user)

    response = client.patch(
        f"/api/v1/recurring-tasks/{recurring_task.id}",
        json={"recurrence_type": "WEEKLY"},
        headers=auth_headers(user),
    )

    assert response.status_code == 400


def test_update_change_type_weekly_to_daily_clears_weekdays(
    client, make_user, make_recurring_task, auth_headers, freeze_today
):
    from app.enums.recurrence_type import RecurrenceType

    user = make_user()
    freeze_today(date(2026, 8, 24))
    recurring_task = make_recurring_task(
        owner=user, recurrence_type=RecurrenceType.WEEKLY, weekdays=[0, 2, 4]
    )

    response = client.patch(
        f"/api/v1/recurring-tasks/{recurring_task.id}",
        json={"recurrence_type": "DAILY"},
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["recurrence_type"] == "DAILY"
    assert body["weekdays"] == []


# --- DELETE /recurring-tasks/{id} — US4 ------------------------------------------


def test_delete_removes_task_weekdays_and_completions(
    client, make_user, make_recurring_task, auth_headers, freeze_today, db_session
):
    from app.enums.recurrence_type import RecurrenceType
    from app.models.recurring_task import RecurringTask
    from app.models.recurring_task_completion import RecurringTaskCompletion
    from app.models.recurring_task_weekday import RecurringTaskWeekday

    user = make_user()
    freeze_today(date(2026, 8, 24))
    recurring_task = make_recurring_task(
        owner=user, recurrence_type=RecurrenceType.WEEKLY, weekdays=[0, 2, 4]
    )
    client.post(f"/api/v1/recurring-tasks/{recurring_task.id}/completions", headers=auth_headers(user))
    recurring_task_id = recurring_task.id

    response = client.delete(
        f"/api/v1/recurring-tasks/{recurring_task_id}", headers=auth_headers(user)
    )

    assert response.status_code == 204
    assert db_session.get(RecurringTask, recurring_task_id) is None
    assert (
        db_session.query(RecurringTaskWeekday)
        .filter(RecurringTaskWeekday.recurring_task_id == recurring_task_id)
        .count()
        == 0
    )
    assert (
        db_session.query(RecurringTaskCompletion)
        .filter(RecurringTaskCompletion.recurring_task_id == recurring_task_id)
        .count()
        == 0
    )


# --- Isolamento por dono (FR-011) -------------------------------------------------


@pytest.mark.parametrize(
    "make_request",
    [
        lambda client, id_, headers: client.patch(
            f"/api/v1/recurring-tasks/{id_}", json={"title": "X"}, headers=headers
        ),
        lambda client, id_, headers: client.delete(f"/api/v1/recurring-tasks/{id_}", headers=headers),
        lambda client, id_, headers: client.post(
            f"/api/v1/recurring-tasks/{id_}/completions", headers=headers
        ),
        lambda client, id_, headers: client.delete(
            f"/api/v1/recurring-tasks/{id_}/completions", headers=headers
        ),
    ],
)
def test_non_owner_gets_404_on_every_route(
    client, make_user, make_recurring_task, auth_headers, freeze_today, make_request
):
    owner = make_user()
    outsider = make_user(email="outsider-recurring@example.com")
    freeze_today(date(2026, 8, 24))
    recurring_task = make_recurring_task(owner=owner)

    response = make_request(client, recurring_task.id, auth_headers(outsider))

    assert response.status_code == 404


def test_patch_nonexistent_id_returns_404(client, make_user, auth_headers, freeze_today):
    user = make_user()
    freeze_today(date(2026, 8, 24))

    response = client.patch(
        f"/api/v1/recurring-tasks/{uuid.uuid4()}", json={"title": "X"}, headers=auth_headers(user)
    )

    assert response.status_code == 404
