import uuid

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin
from app.enums.recurrence_type import RecurrenceType


class RecurringTask(Base, TimestampMixin):
    """Tarefa Fixa (rotina pessoal recorrente) — 002-tarefas-fixas. Pertence a um
    único usuário (`owner_id`), sem workspace/participantes/compartilhamento
    (FR-011, data-model.md). `month_day` só é preenchido quando
    `recurrence_type = MONTHLY` (data-model.md) — reforçado em
    `RecurringTaskService`, nunca só pelo `CHECK` abaixo (Constitution IV)."""

    __tablename__ = "recurring_tasks"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_recurring_tasks_title_not_blank"),
        CheckConstraint(
            "month_day IS NULL OR month_day BETWEEN 1 AND 31",
            name="ck_recurring_tasks_month_day_range",
        ),
        Index("ix_recurring_tasks_owner_id", "owner_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    recurrence_type: Mapped[RecurrenceType] = mapped_column(
        Enum(
            RecurrenceType,
            name="recurrence_type",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    month_day: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
