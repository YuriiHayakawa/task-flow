import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.checklist_item import ChecklistItem


class ChecklistItemRepository:
    """Acesso a dados de `ChecklistItem` — nenhuma regra de negócio aqui
    (Constitution III). Autorização (visibilidade/participação) e commit são
    responsabilidade do `ChecklistService`."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, item: ChecklistItem) -> ChecklistItem:
        self.db.add(item)
        self.db.flush()
        return item

    def list_by_task(self, task_id: uuid.UUID) -> list[ChecklistItem]:
        """Ordenado por `created_at` asc + `id` asc (desempate
        determinístico) — o contrato não define ordem explicitamente; sem
        paginação (volume esperado baixo por tarefa, contracts/collaboration.md)."""
        stmt = (
            select(ChecklistItem)
            .where(ChecklistItem.task_id == task_id)
            .order_by(ChecklistItem.created_at.asc(), ChecklistItem.id.asc())
        )
        return list(self.db.scalars(stmt))

    def get_by_task_and_id(
        self, task_id: uuid.UUID, item_id: uuid.UUID
    ) -> ChecklistItem | None:
        """Escopado por `task_id` E `item_id` juntos — nunca só `item_id`,
        para que um `task_id` autorizado não permita manipular um item que
        pertence a outra tarefa."""
        stmt = select(ChecklistItem).where(
            ChecklistItem.task_id == task_id, ChecklistItem.id == item_id
        )
        return self.db.scalars(stmt).first()

    def update(self, item: ChecklistItem) -> ChecklistItem:
        self.db.flush()
        return item

    def delete(self, item: ChecklistItem) -> None:
        self.db.delete(item)
        self.db.flush()
