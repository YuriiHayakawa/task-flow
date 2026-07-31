import uuid
from datetime import datetime, timezone

from app.core.exceptions import NotFoundError
from app.models.checklist_item import ChecklistItem
from app.models.task import Task
from app.repositories.checklist_item_repository import ChecklistItemRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.checklist_item import ChecklistItemCreate, ChecklistItemRead, ChecklistItemUpdate


class ChecklistItemService:
    """FR-035/FR-036 (US9). Mesmo padrão de `CommentService`/`TaskMemberService`
    (Fases 7/8): os métodos recebem `task_id` (não um `Task` pré-carregado
    pela rota) e resolvem tudo via repository — quem autoriza o chamador é a
    dependency da rota (`require_task_visible`/`require_task_participant`)."""

    def __init__(
        self,
        checklist_item_repository: ChecklistItemRepository,
        task_repository: TaskRepository,
    ) -> None:
        self.checklist_item_repository = checklist_item_repository
        self.task_repository = task_repository
        self.db = checklist_item_repository.db

    def _get_task_or_404(self, task_id: uuid.UUID) -> Task:
        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise NotFoundError("Tarefa não encontrada.")
        return task

    def _get_item_or_404(self, task_id: uuid.UUID, item_id: uuid.UUID) -> ChecklistItem:
        """Escopado por `task_id` E `item_id` juntos (via `get_by_task_and_id`)
        — um item de outra tarefa nunca é encontrado, mesmo com o `item_id`
        certo, evitando manipulação cruzada entre tarefas."""
        item = self.checklist_item_repository.get_by_task_and_id(task_id, item_id)
        if item is None:
            raise NotFoundError("Item de checklist não encontrado.")
        return item

    def list_items(self, task_id: uuid.UUID) -> list[ChecklistItemRead]:
        self._get_task_or_404(task_id)
        items = self.checklist_item_repository.list_by_task(task_id)
        return [ChecklistItemRead.model_validate(item, from_attributes=True) for item in items]

    def create_item(self, task_id: uuid.UUID, data: ChecklistItemCreate) -> ChecklistItemRead:
        self._get_task_or_404(task_id)

        item = ChecklistItem(task_id=task_id, description=data.description)
        self.checklist_item_repository.create(item)
        self.db.commit()
        self.db.refresh(item)
        return ChecklistItemRead.model_validate(item, from_attributes=True)

    def update_item(
        self, task_id: uuid.UUID, item_id: uuid.UUID, data: ChecklistItemUpdate
    ) -> ChecklistItemRead:
        """`is_done: true` preenche `completed_at` só na transição
        pendente→concluído (mesmo padrão de `TaskService.update` para
        `status = DONE`) — marcar concluído um item já concluído não
        atualiza o timestamp original; `false` sempre limpa."""
        self._get_task_or_404(task_id)
        item = self._get_item_or_404(task_id, item_id)

        if data.is_done and not item.is_done:
            item.completed_at = datetime.now(timezone.utc)
        elif not data.is_done and item.is_done:
            item.completed_at = None
        item.is_done = data.is_done

        self.checklist_item_repository.update(item)
        self.db.commit()
        self.db.refresh(item)
        return ChecklistItemRead.model_validate(item, from_attributes=True)

    def delete_item(self, task_id: uuid.UUID, item_id: uuid.UUID) -> None:
        self._get_task_or_404(task_id)
        item = self._get_item_or_404(task_id, item_id)

        self.checklist_item_repository.delete(item)
        self.db.commit()
