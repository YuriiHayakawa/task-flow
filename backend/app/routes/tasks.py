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
from app.repositories.notification_repository import NotificationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_history_repository import TaskHistoryRepository
from app.repositories.task_member_repository import TaskMemberRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.common import PaginatedResponse
from app.schemas.task import TaskCreate, TaskRead, TaskSearchParams, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(
        TaskRepository(db),
        ProjectRepository(db),
        WorkspaceMemberRepository(db),
        TaskMemberRepository(db),
        NotificationRepository(db),
        TaskHistoryRepository(db),
    )


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> Task:
    return service.create(data, creator_id=current_user.id)


@router.get("", response_model=PaginatedResponse[TaskRead])
def list_tasks(
    params: TaskSearchParams = Depends(),
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> dict[str, object]:
    """FR-055 a FR-059 (US8): endpoint central de listagem — tarefas
    pessoais do próprio usuário + tarefas de todos os workspaces dos quais
    participa, com busca/filtros/ordenação combináveis e paginação real."""
    tasks, total = service.search(current_user.id, params)
    return {"items": tasks, "page": params.page, "page_size": params.page_size, "total": total}


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task: Task = Depends(require_task_visible)) -> Task:
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    task: Task = Depends(require_task_editor),
    service: TaskService = Depends(get_task_service),
) -> Task:
    return service.update(task, data, changed_by=current_user.id)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task: Task = Depends(require_task_delete),
    service: TaskService = Depends(get_task_service),
) -> None:
    service.delete(task)
