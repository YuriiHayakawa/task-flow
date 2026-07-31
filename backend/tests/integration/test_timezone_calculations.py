"""T116 — cálculo de "hoje"/"atrasada"/"vencendo hoje" usando `APP_TIMEZONE`,
com data/hora controlada próxima à virada de dia em UTC vs.
`America/Sao_Paulo` (plan.md, seção Testes, refinamento #14).

Sem isso, uma tarefa com prazo "hoje" na timezone configurada poderia
aparecer incorretamente como "atrasada" (ou vice-versa) nas poucas horas em
que a data em UTC já virou mas a data em `America/Sao_Paulo` (UTC-3) ainda
não — ou o oposto, dependendo do lado da virada."""

from datetime import date, datetime
from datetime import timezone as dt_timezone

import pytest

from app.utils import timezone as timezone_module


class _FrozenDateTime(datetime):
    """Sobrescreve `datetime.now()` para simular um instante fixo próximo à
    virada de dia UTC — 01:30 UTC de 15/01/2026 é 22:30 de 14/01/2026 em
    America/Sao_Paulo (UTC-3): a data "de hoje" diverge entre as duas
    timezones nesse instante exato, o cenário que este teste cobre."""

    @classmethod
    def now(cls, tz=None):
        base = datetime(2026, 1, 15, 1, 30, tzinfo=dt_timezone.utc)
        return base.astimezone(tz) if tz is not None else base


@pytest.fixture()
def frozen_near_utc_midnight(monkeypatch):
    monkeypatch.setattr(timezone_module, "datetime", _FrozenDateTime)


def test_today_in_app_timezone_uses_configured_timezone_not_utc(frozen_near_utc_midnight):
    """No instante congelado, UTC já está em 15/01, mas America/Sao_Paulo
    (`APP_TIMEZONE` padrão) ainda está em 14/01 — o resultado MUST seguir a
    timezone configurada, nunca UTC puro."""
    assert timezone_module.today_in_app_timezone() == date(2026, 1, 14)


def test_dashboard_classifies_task_due_today_using_app_timezone(
    client, make_user, make_task, auth_headers, frozen_near_utc_midnight
):
    """Sem o cálculo correto de timezone, uma tarefa com `due_date=14/01`
    comparada a um "hoje" incorretamente calculado como 15/01 (UTC puro)
    apareceria como atrasada, não como vencendo hoje."""
    user = make_user()
    make_task(creator=user, due_date=date(2026, 1, 14))

    response = client.get("/api/v1/dashboard", headers=auth_headers(user))

    counts = response.json()["counts"]
    assert counts["due_today"] == 1
    assert counts["overdue"] == 0


def test_dashboard_classifies_task_overdue_using_app_timezone(
    client, make_user, make_task, auth_headers, frozen_near_utc_midnight
):
    """Prazo em 13/01 é realmente atrasado em qualquer uma das duas
    timezones no instante congelado — confirma que "atrasada" continua
    correta ao lado do caso de borda acima (não é um efeito colateral de
    sempre classificar tudo como "vencendo hoje")."""
    user = make_user()
    make_task(creator=user, due_date=date(2026, 1, 13))

    response = client.get("/api/v1/dashboard", headers=auth_headers(user))

    counts = response.json()["counts"]
    assert counts["overdue"] == 1
    assert counts["due_today"] == 0


def test_dashboard_classifies_future_task_as_neither_using_app_timezone(
    client, make_user, make_task, auth_headers, frozen_near_utc_midnight
):
    """Prazo em 16/01 é futuro em ambas as timezones — não deve aparecer
    como atrasada nem como vencendo hoje."""
    user = make_user()
    make_task(creator=user, due_date=date(2026, 1, 16))

    response = client.get("/api/v1/dashboard", headers=auth_headers(user))

    counts = response.json()["counts"]
    assert counts["overdue"] == 0
    assert counts["due_today"] == 0
