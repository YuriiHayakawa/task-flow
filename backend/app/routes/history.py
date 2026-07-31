from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.task_authorization import require_task_visible
from app.models.task import Task
from app.repositories.task_history_repository import TaskHistoryRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.common import PaginatedResponse
from app.schemas.task_history import TaskHistoryEntryRead
from app.services.task_history_service import TaskHistoryService

router = APIRouter(prefix="/tasks/{task_id}/history", tags=["task-history"])

_DEFAULT_PAGE_SIZE = 20


def get_task_history_service(db: Session = Depends(get_db)) -> TaskHistoryService:
    return TaskHistoryService(TaskHistoryRepository(db), TaskRepository(db))


@router.get("", response_model=PaginatedResponse[TaskHistoryEntryRead])
def list_task_history(
    task: Task = Depends(require_task_visible),
    service: TaskHistoryService = Depends(get_task_history_service),
) -> dict[str, object]:
    # contracts/collaboration.md: "200 (lista paginada de TaskHistoryEntryRead...)"
    # — mesmo atalho de paginação já usado em Comments/Notifications (page=1,
    # sem paginação real em SQL), ordenado por changed_at descendente
    # (já garantido pelo repository).
    entries = service.list_history(task.id)
    return {
        "items": entries,
        "page": 1,
        "page_size": _DEFAULT_PAGE_SIZE,
        "total": len(entries),
    }
