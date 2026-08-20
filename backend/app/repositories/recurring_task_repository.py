import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recurring_task import RecurringTask
from app.models.recurring_task_completion import RecurringTaskCompletion
from app.models.recurring_task_weekday import RecurringTaskWeekday


class RecurringTaskRepository:
    """Acesso a dados de `RecurringTask`/`RecurringTaskWeekday`/
    `RecurringTaskCompletion` — nenhuma regra de negócio aqui (Constitution
    III). Cálculo de ocorrência, validação e commit são responsabilidade de
    `RecurringTaskService`."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, recurring_task: RecurringTask) -> RecurringTask:
        self.db.add(recurring_task)
        self.db.flush()
        return recurring_task

    def get_by_id(self, recurring_task_id: uuid.UUID) -> RecurringTask | None:
        return self.db.get(RecurringTask, recurring_task_id)

    def list_by_owner(self, owner_id: uuid.UUID) -> list[RecurringTask]:
        """Ordenado por `created_at` asc + `id` asc (desempate determinístico) —
        mesmo padrão de `ChecklistItemRepository.list_by_task`."""
        stmt = (
            select(RecurringTask)
            .where(RecurringTask.owner_id == owner_id)
            .order_by(RecurringTask.created_at.asc(), RecurringTask.id.asc())
        )
        return list(self.db.scalars(stmt))

    def update(self, recurring_task: RecurringTask) -> RecurringTask:
        self.db.flush()
        return recurring_task

    def delete(self, recurring_task: RecurringTask) -> None:
        self.db.delete(recurring_task)
        self.db.flush()

    def list_weekdays(self, recurring_task_id: uuid.UUID) -> list[int]:
        stmt = (
            select(RecurringTaskWeekday.weekday)
            .where(RecurringTaskWeekday.recurring_task_id == recurring_task_id)
            .order_by(RecurringTaskWeekday.weekday.asc())
        )
        return list(self.db.scalars(stmt))

    def set_weekdays(self, recurring_task_id: uuid.UUID, weekdays: list[int]) -> None:
        """Substitui por completo o conjunto de dias da semana — mais simples
        e menos propenso a erro do que calcular um diff (volume por tarefa é
        no máximo 7 linhas)."""
        stmt = select(RecurringTaskWeekday).where(
            RecurringTaskWeekday.recurring_task_id == recurring_task_id
        )
        for existing in self.db.scalars(stmt):
            self.db.delete(existing)
        self.db.flush()

        for weekday in weekdays:
            self.db.add(
                RecurringTaskWeekday(recurring_task_id=recurring_task_id, weekday=weekday)
            )
        self.db.flush()

    def get_completion(
        self, recurring_task_id: uuid.UUID, occurrence_date: date
    ) -> RecurringTaskCompletion | None:
        stmt = select(RecurringTaskCompletion).where(
            RecurringTaskCompletion.recurring_task_id == recurring_task_id,
            RecurringTaskCompletion.occurrence_date == occurrence_date,
        )
        return self.db.scalars(stmt).first()

    def create_completion(
        self, recurring_task_id: uuid.UUID, occurrence_date: date
    ) -> RecurringTaskCompletion:
        completion = RecurringTaskCompletion(
            recurring_task_id=recurring_task_id, occurrence_date=occurrence_date
        )
        self.db.add(completion)
        self.db.flush()
        return completion

    def delete_completion(self, completion: RecurringTaskCompletion) -> None:
        self.db.delete(completion)
        self.db.flush()
