import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, CreatedAtMixin


class RecurringTaskCompletion(Base, CreatedAtMixin):
    """Conclusão de uma ocorrência de Tarefa Fixa (research.md #2, data-model.md).
    A PRESENÇA de uma linha aqui para a data de hoje é o que decide se a tarefa
    está concluída hoje — nunca um único campo `is_done` sobrescrito. Marcar
    pendente de novo é um `DELETE` desta linha, não um `UPDATE`. `created_at`
    (herdado de `CreatedAtMixin`) é exposto como `completed_at` no schema —
    quando o registro foi de fato criado, distinto de `occurrence_date`."""

    __tablename__ = "recurring_task_completions"
    __table_args__ = (
        UniqueConstraint(
            "recurring_task_id",
            "occurrence_date",
            name="uq_recurring_task_completions_task_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    recurring_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recurring_tasks.id", ondelete="CASCADE"), nullable=False
    )
    occurrence_date: Mapped[date] = mapped_column(Date, nullable=False)
