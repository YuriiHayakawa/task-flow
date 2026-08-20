from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.dependencies.task_authorization import require_recurring_task_owner
from app.models.recurring_task import RecurringTask
from app.models.user import User
from app.repositories.recurring_task_repository import RecurringTaskRepository
from app.schemas.recurring_task import RecurringTaskCreate, RecurringTaskRead, RecurringTaskUpdate
from app.services.recurring_task_service import RecurringTaskService

router = APIRouter(prefix="/recurring-tasks", tags=["recurring-tasks"])


def get_recurring_task_service(db: Session = Depends(get_db)) -> RecurringTaskService:
    return RecurringTaskService(RecurringTaskRepository(db))


@router.post("", response_model=RecurringTaskRead, status_code=status.HTTP_201_CREATED)
def create_recurring_task(
    data: RecurringTaskCreate,
    current_user: User = Depends(get_current_user),
    service: RecurringTaskService = Depends(get_recurring_task_service),
) -> RecurringTaskRead:
    return service.create(current_user.id, data)


@router.get("", response_model=list[RecurringTaskRead])
def list_recurring_tasks(
    current_user: User = Depends(get_current_user),
    service: RecurringTaskService = Depends(get_recurring_task_service),
) -> list[RecurringTaskRead]:
    # contracts/recurring-tasks.md: sem paginação (volume esperado baixo por
    # usuário), mesmo padrão de Checklist/Attachments em 001-taskflow-mvp.
    return service.list_for_owner(current_user.id)


@router.patch("/{recurring_task_id}", response_model=RecurringTaskRead)
def update_recurring_task(
    data: RecurringTaskUpdate,
    recurring_task: RecurringTask = Depends(require_recurring_task_owner),
    service: RecurringTaskService = Depends(get_recurring_task_service),
) -> RecurringTaskRead:
    return service.update(recurring_task.id, data)


@router.delete("/{recurring_task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_task(
    recurring_task: RecurringTask = Depends(require_recurring_task_owner),
    service: RecurringTaskService = Depends(get_recurring_task_service),
) -> None:
    service.delete(recurring_task.id)


@router.post("/{recurring_task_id}/completions", response_model=RecurringTaskRead, status_code=status.HTTP_201_CREATED)
def complete_recurring_task_today(
    recurring_task: RecurringTask = Depends(require_recurring_task_owner),
    service: RecurringTaskService = Depends(get_recurring_task_service),
) -> RecurringTaskRead:
    return service.complete_today(recurring_task.id)


@router.delete("/{recurring_task_id}/completions", response_model=RecurringTaskRead)
def uncomplete_recurring_task_today(
    recurring_task: RecurringTask = Depends(require_recurring_task_owner),
    service: RecurringTaskService = Depends(get_recurring_task_service),
) -> RecurringTaskRead:
    return service.uncomplete_today(recurring_task.id)
