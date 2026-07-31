import uuid

from app.core.exceptions import NotFoundError
from app.models.task import Task
from app.repositories.task_history_repository import TaskHistoryRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.task_history import TaskHistoryEntryRead


class TaskHistoryService:
    """FR-041/FR-042 (US12). Mesmo padrão de `CommentService`/
    `ChecklistItemService`: o método recebe `task_id` (não um `Task`
    pré-carregado pela rota) e resolve tudo via repository — quem autoriza
    visibilidade é a dependency da rota (`require_task_visible`); a
    escrita de `TaskHistoryEntry` não pertence a este Service (é efeito
    colateral de `TaskService.update`, T110) — esta API é somente leitura."""

    def __init__(
        self, task_history_repository: TaskHistoryRepository, task_repository: TaskRepository
    ) -> None:
        self.task_history_repository = task_history_repository
        self.task_repository = task_repository

    def _get_task_or_404(self, task_id: uuid.UUID) -> Task:
        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise NotFoundError("Tarefa não encontrada.")
        return task

    def list_history(self, task_id: uuid.UUID) -> list[TaskHistoryEntryRead]:
        self._get_task_or_404(task_id)
        rows = self.task_history_repository.list_by_task(task_id)
        return [TaskHistoryEntryRead.model_validate(row, from_attributes=True) for row in rows]
