import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums.recurrence_type import RecurrenceType


class RecurringTaskCreate(BaseModel):
    """Corpo de `POST /api/v1/recurring-tasks` (contracts/recurring-tasks.md).
    `weekdays`/`month_day` são estruturalmente opcionais aqui (Pydantic não
    expressa "obrigatório só quando X") — a exigência cruzada por
    `recurrence_type` (semanal exige `weekdays` não vazio; mensal exige
    `month_day`) é reforçada em `RecurringTaskService`, nunca só aqui
    (Constitution IV)."""

    title: str = Field(min_length=1, max_length=255)
    recurrence_type: RecurrenceType
    weekdays: list[int] = Field(default_factory=list)
    month_day: int | None = Field(default=None, ge=1, le=31)


class RecurringTaskUpdate(BaseModel):
    """Corpo de `PATCH /api/v1/recurring-tasks/{id}` — todos os campos
    opcionais (atualização parcial); trocar `recurrence_type` substitui os
    campos específicos do tipo anterior (`RecurringTaskService.update`)."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    recurrence_type: RecurrenceType | None = None
    weekdays: list[int] | None = None
    month_day: int | None = Field(default=None, ge=1, le=31)


class RecurringTaskRead(BaseModel):
    """`weekdays`/`month_day` sempre presentes na resposta (lista vazia /
    `null` quando não se aplicam ao tipo). `is_due_today`/`completed_today`
    são derivados, nunca persistidos (data-model.md, "Cálculo de
    ocorrência")."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    recurrence_type: RecurrenceType
    weekdays: list[int]
    month_day: int | None
    is_due_today: bool
    completed_today: bool
    created_at: datetime
    updated_at: datetime
