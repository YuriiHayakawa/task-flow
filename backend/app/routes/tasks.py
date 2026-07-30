from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.dependencies.task_authorization import (
    require_task_delete,
    require_task_editor,
    require_task_visible,
)
from app.models.task import Task
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.common import PaginatedResponse
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])

_DEFAULT_PAGE_SIZE = 20


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(TaskRepository(db), ProjectRepository(db), WorkspaceMemberRepository(db))


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> Task:
    return service.create(data, creator_id=current_user.id)


@router.get("", response_model=PaginatedResponse[TaskRead])
def list_tasks(
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> dict[str, object]:
    """Fase 3 (US1): apenas tarefas pessoais do próprio usuário. A união com
    tarefas de workspace permanece para a US8 (T090/T091) — não é ampliada
    nesta fase (US5/T079), por escopo explícito. O envelope paginado já
    segue contracts/_conventions.md para não exigir mudança de formato
    depois."""
    tasks = service.list_personal_tasks(current_user.id)
    return {"items": tasks, "page": 1, "page_size": _DEFAULT_PAGE_SIZE, "total": len(tasks)}


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task: Task = Depends(require_task_visible)) -> Task:
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    data: TaskUpdate,
    task: Task = Depends(require_task_editor),
    service: TaskService = Depends(get_task_service),
) -> Task:
    return service.update(task, data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task: Task = Depends(require_task_delete),
    service: TaskService = Depends(get_task_service),
) -> None:
    service.delete(task)
