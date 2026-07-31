import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.task_authorization import require_task_participant, require_task_visible
from app.models.task import Task
from app.repositories.checklist_item_repository import ChecklistItemRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.checklist_item import ChecklistItemCreate, ChecklistItemRead, ChecklistItemUpdate
from app.services.checklist_item_service import ChecklistItemService

router = APIRouter(prefix="/tasks/{task_id}/checklist", tags=["checklist"])


def get_checklist_service(db: Session = Depends(get_db)) -> ChecklistItemService:
    return ChecklistItemService(ChecklistItemRepository(db), TaskRepository(db))


@router.get("", response_model=list[ChecklistItemRead])
def list_checklist_items(
    task: Task = Depends(require_task_visible),
    service: ChecklistItemService = Depends(get_checklist_service),
) -> list[ChecklistItemRead]:
    # contracts/collaboration.md: "200 (lista de ChecklistItemRead...)" — sem
    # paginação ("volume esperado baixo por tarefa"), mesmo padrão de
    # Task Members (Fase 7).
    return service.list_items(task.id)


@router.post("", response_model=ChecklistItemRead, status_code=status.HTTP_201_CREATED)
def create_checklist_item(
    data: ChecklistItemCreate,
    task: Task = Depends(require_task_participant),
    service: ChecklistItemService = Depends(get_checklist_service),
) -> ChecklistItemRead:
    return service.create_item(task.id, data)


@router.patch("/{item_id}", response_model=ChecklistItemRead)
def update_checklist_item(
    item_id: uuid.UUID,
    data: ChecklistItemUpdate,
    task: Task = Depends(require_task_participant),
    service: ChecklistItemService = Depends(get_checklist_service),
) -> ChecklistItemRead:
    return service.update_item(task.id, item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_checklist_item(
    item_id: uuid.UUID,
    task: Task = Depends(require_task_participant),
    service: ChecklistItemService = Depends(get_checklist_service),
) -> None:
    service.delete_item(task.id, item_id)
