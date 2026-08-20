"""T011/T015/T018 [US1/US2/US3] — testes unitários de
`RecurringTaskService._is_occurrence` (data-model.md, "Cálculo de
ocorrência") — função estática, sem necessidade de banco/sessão."""

from datetime import date

from app.enums.recurrence_type import RecurrenceType
from app.services.recurring_task_service import RecurringTaskService

_is_occurrence = RecurringTaskService._is_occurrence


# --- DAILY -----------------------------------------------------------------


def test_daily_is_always_occurrence():
    assert _is_occurrence(RecurrenceType.DAILY, [], None, date(2026, 3, 17)) is True
    assert _is_occurrence(RecurrenceType.DAILY, [], None, date(2026, 12, 25)) is True


# --- WEEKLY ------------------------------------------------------------------


def test_weekly_is_occurrence_only_on_selected_weekdays():
    # segunda(0), quarta(2), sexta(4)
    weekdays = [0, 2, 4]
    monday = date(2026, 8, 24)  # segunda-feira
    tuesday = date(2026, 8, 25)  # terça-feira
    wednesday = date(2026, 8, 26)  # quarta-feira

    assert _is_occurrence(RecurrenceType.WEEKLY, weekdays, None, monday) is True
    assert _is_occurrence(RecurrenceType.WEEKLY, weekdays, None, wednesday) is True
    assert _is_occurrence(RecurrenceType.WEEKLY, weekdays, None, tuesday) is False


def test_weekly_with_no_weekdays_never_occurrence():
    # Estado inconsistente que _validate_recurrence_fields impede de existir
    # via API, mas a função em si é defensiva.
    assert _is_occurrence(RecurrenceType.WEEKLY, [], None, date(2026, 8, 24)) is False


# --- MONTHLY -------------------------------------------------------------------


def test_monthly_is_occurrence_on_configured_day():
    assert _is_occurrence(RecurrenceType.MONTHLY, [], 10, date(2026, 3, 10)) is True
    assert _is_occurrence(RecurrenceType.MONTHLY, [], 10, date(2026, 3, 9)) is False
    assert _is_occurrence(RecurrenceType.MONTHLY, [], 10, date(2026, 3, 11)) is False


def test_monthly_day_31_falls_back_to_last_day_of_shorter_month():
    """research.md #3 — abril tem 30 dias; dia 31 configurado cai no dia 30."""
    assert _is_occurrence(RecurrenceType.MONTHLY, [], 31, date(2026, 4, 30)) is True
    assert _is_occurrence(RecurrenceType.MONTHLY, [], 31, date(2026, 4, 29)) is False
    # Mês com 31 dias: continua caindo no dia 31 normalmente.
    assert _is_occurrence(RecurrenceType.MONTHLY, [], 31, date(2026, 5, 31)) is True


def test_monthly_day_31_in_february_non_leap_year():
    """2026 não é bissexto (2026 / 4 não é inteiro) — fevereiro tem 28 dias."""
    assert _is_occurrence(RecurrenceType.MONTHLY, [], 31, date(2026, 2, 28)) is True
    assert _is_occurrence(RecurrenceType.MONTHLY, [], 31, date(2026, 2, 27)) is False


def test_monthly_day_31_in_february_leap_year():
    """2028 é bissexto (2028 / 4 = 507) — fevereiro tem 29 dias."""
    assert _is_occurrence(RecurrenceType.MONTHLY, [], 31, date(2028, 2, 29)) is True
    assert _is_occurrence(RecurrenceType.MONTHLY, [], 31, date(2028, 2, 28)) is False
