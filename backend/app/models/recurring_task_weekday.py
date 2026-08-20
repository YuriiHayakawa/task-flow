import uuid

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RecurringTaskWeekday(Base):
    """Um dia da semana selecionado para uma Tarefa Fixa `WEEKLY` — tabela filha,
    não bitmask/array (research.md #1). `weekday` segue `date.weekday()` do
    Python: `0 = segunda` ... `6 = domingo`."""

    __tablename__ = "recurring_task_weekdays"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_recurring_task_weekdays_range"),
        UniqueConstraint(
            "recurring_task_id", "weekday", name="uq_recurring_task_weekdays_task_weekday"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    recurring_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recurring_tasks.id", ondelete="CASCADE"), nullable=False
    )
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
