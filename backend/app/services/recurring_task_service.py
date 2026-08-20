import calendar
import uuid
from datetime import date

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.enums.recurrence_type import RecurrenceType
from app.models.recurring_task import RecurringTask
from app.repositories.recurring_task_repository import RecurringTaskRepository
from app.schemas.recurring_task import RecurringTaskCreate, RecurringTaskRead, RecurringTaskUpdate
from app.utils.timezone import today_in_app_timezone


class RecurringTaskService:
    """FR-001 a FR-014 (002-tarefas-fixas). Concentra toda a regra de negócio:
    validação cruzada por tipo de recorrência, cálculo de ocorrência
    (`_is_occurrence`, único ponto para os 3 tipos — data-model.md) e o
    modelo de conclusão por data (research.md #2 — presença de uma linha em
    `recurring_task_completions` para hoje é o que decide concluída/pendente,
    nunca um campo único sobrescrito)."""

    def __init__(self, recurring_task_repository: RecurringTaskRepository) -> None:
        self.recurring_task_repository = recurring_task_repository
        self.db = recurring_task_repository.db

    def _get_or_404(self, recurring_task_id: uuid.UUID) -> RecurringTask:
        recurring_task = self.recurring_task_repository.get_by_id(recurring_task_id)
        if recurring_task is None:
            raise NotFoundError("Tarefa fixa não encontrada.")
        return recurring_task

    def _validate_recurrence_fields(
        self, recurrence_type: RecurrenceType, weekdays: list[int], month_day: int | None
    ) -> None:
        """FR-002/FR-003: reforça a exigência cruzada por tipo no Service,
        nunca só no schema (Constitution IV)."""
        if recurrence_type == RecurrenceType.WEEKLY and not weekdays:
            raise BusinessRuleViolationError(
                "Uma tarefa fixa semanal precisa de ao menos um dia da semana selecionado."
            )
        if recurrence_type == RecurrenceType.MONTHLY and month_day is None:
            raise BusinessRuleViolationError(
                "Uma tarefa fixa mensal precisa de um dia do mês selecionado."
            )

    @staticmethod
    def _is_occurrence(
        recurrence_type: RecurrenceType,
        weekdays: list[int],
        month_day: int | None,
        target_date: date,
    ) -> bool:
        """FR-004 — único ponto que calcula se `target_date` é uma ocorrência
        da tarefa fixa, para os 3 tipos de recorrência (data-model.md,
        "Cálculo de ocorrência"). Nunca persistido."""
        if recurrence_type == RecurrenceType.DAILY:
            return True
        if recurrence_type == RecurrenceType.WEEKLY:
            return target_date.weekday() in weekdays
        # MONTHLY (research.md #3): cai no último dia do mês quando o mês
        # corrente não tem o dia configurado (ex.: dia 31 em abril).
        assert month_day is not None  # garantido por _validate_recurrence_fields
        last_day_of_month = calendar.monthrange(target_date.year, target_date.month)[1]
        return target_date.day == min(month_day, last_day_of_month)

    def _to_read(self, recurring_task: RecurringTask, today: date) -> RecurringTaskRead:
        weekdays = self.recurring_task_repository.list_weekdays(recurring_task.id)
        is_due_today = self._is_occurrence(
            recurring_task.recurrence_type, weekdays, recurring_task.month_day, today
        )
        completed_today = is_due_today and (
            self.recurring_task_repository.get_completion(recurring_task.id, today) is not None
        )
        return RecurringTaskRead(
            id=recurring_task.id,
            title=recurring_task.title,
            recurrence_type=recurring_task.recurrence_type,
            weekdays=weekdays,
            month_day=recurring_task.month_day,
            is_due_today=is_due_today,
            completed_today=completed_today,
            created_at=recurring_task.created_at,
            updated_at=recurring_task.updated_at,
        )

    def list_for_owner(self, owner_id: uuid.UUID) -> list[RecurringTaskRead]:
        today = today_in_app_timezone()
        recurring_tasks = self.recurring_task_repository.list_by_owner(owner_id)
        return [self._to_read(recurring_task, today) for recurring_task in recurring_tasks]

    def create(self, owner_id: uuid.UUID, data: RecurringTaskCreate) -> RecurringTaskRead:
        weekdays = data.weekdays if data.recurrence_type == RecurrenceType.WEEKLY else []
        month_day = data.month_day if data.recurrence_type == RecurrenceType.MONTHLY else None
        self._validate_recurrence_fields(data.recurrence_type, weekdays, month_day)

        recurring_task = RecurringTask(
            owner_id=owner_id,
            title=data.title,
            recurrence_type=data.recurrence_type,
            month_day=month_day,
        )
        self.recurring_task_repository.create(recurring_task)
        if weekdays:
            self.recurring_task_repository.set_weekdays(recurring_task.id, weekdays)
        self.db.commit()
        self.db.refresh(recurring_task)
        return self._to_read(recurring_task, today_in_app_timezone())

    def update(
        self, recurring_task_id: uuid.UUID, data: RecurringTaskUpdate
    ) -> RecurringTaskRead:
        """FR-008: editar não afeta conclusões passadas (`recurring_task_
        completions` nunca é tocada aqui). Trocar `recurrence_type` (ou
        `weekdays`/`month_day` isoladamente) sempre recalcula os campos do
        tipo resultante a partir do que foi enviado nesta chamada — nunca
        mistura campos de um tipo antigo com o novo."""
        recurring_task = self._get_or_404(recurring_task_id)
        changes = data.model_dump(exclude_unset=True)

        if "title" in changes:
            recurring_task.title = changes["title"]

        if "recurrence_type" in changes or "weekdays" in changes or "month_day" in changes:
            new_recurrence_type = changes.get("recurrence_type", recurring_task.recurrence_type)
            weekdays = (
                changes.get(
                    "weekdays", self.recurring_task_repository.list_weekdays(recurring_task.id)
                )
                if new_recurrence_type == RecurrenceType.WEEKLY
                else []
            )
            month_day = (
                changes.get("month_day", recurring_task.month_day)
                if new_recurrence_type == RecurrenceType.MONTHLY
                else None
            )
            self._validate_recurrence_fields(new_recurrence_type, weekdays, month_day)

            recurring_task.recurrence_type = new_recurrence_type
            recurring_task.month_day = month_day
            self.recurring_task_repository.set_weekdays(recurring_task.id, weekdays)

        self.recurring_task_repository.update(recurring_task)
        self.db.commit()
        self.db.refresh(recurring_task)
        return self._to_read(recurring_task, today_in_app_timezone())

    def delete(self, recurring_task_id: uuid.UUID) -> None:
        """FR-009: `ON DELETE CASCADE` remove `recurring_task_weekdays`/
        `recurring_task_completions` — nenhum passo manual adicional aqui."""
        recurring_task = self._get_or_404(recurring_task_id)
        self.recurring_task_repository.delete(recurring_task)
        self.db.commit()

    def complete_today(self, recurring_task_id: uuid.UUID) -> RecurringTaskRead:
        """FR-005/FR-006: marca a ocorrência de hoje como concluída — `400`
        se hoje não for ocorrência desta tarefa fixa. Idempotente: chamar de
        novo no mesmo dia não cria uma segunda linha."""
        recurring_task = self._get_or_404(recurring_task_id)
        today = today_in_app_timezone()
        weekdays = self.recurring_task_repository.list_weekdays(recurring_task.id)
        if not self._is_occurrence(
            recurring_task.recurrence_type, weekdays, recurring_task.month_day, today
        ):
            raise BusinessRuleViolationError("Hoje não é uma ocorrência desta tarefa fixa.")

        if self.recurring_task_repository.get_completion(recurring_task.id, today) is None:
            self.recurring_task_repository.create_completion(recurring_task.id, today)
            self.db.commit()
        return self._to_read(recurring_task, today)

    def uncomplete_today(self, recurring_task_id: uuid.UUID) -> RecurringTaskRead:
        """Desmarca a ocorrência de hoje — idempotente: chamar quando já
        está pendente não é erro."""
        recurring_task = self._get_or_404(recurring_task_id)
        today = today_in_app_timezone()
        existing = self.recurring_task_repository.get_completion(recurring_task.id, today)
        if existing is not None:
            self.recurring_task_repository.delete_completion(existing)
            self.db.commit()
        return self._to_read(recurring_task, today)
