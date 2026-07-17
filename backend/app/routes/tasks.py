import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.models.task import Task
from app.models.user import User
from app.repositories.task_repository import TaskRepository
from app.schemas.common import PaginatedResponse
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])

_DEFAULT_PAGE_SIZE = 20


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(TaskRepository(db))


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
    tarefas de workspace chega na US3/US4 (T065/T073); busca/filtros/ordenação
    chegam na US8 (T090/T091) — o envelope paginado já segue
    contracts/_conventions.md para não exigir mudança de formato depois."""
    tasks = service.list_personal_tasks(current_user.id)
    return {"items": tasks, "page": 1, "page_size": _DEFAULT_PAGE_SIZE, "total": len(tasks)}


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> Task:
    return service.get_personal_task_or_404(task_id, current_user.id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> Task:
    # Fase 3 (US1): autorização simplificada (só o criador acessa sua tarefa
    # pessoal). Substituída por require_task_editor/require_task_delete na US5
    # (T079), quando tarefas de workspace também precisarem passar por aqui.
    task = service.get_personal_task_or_404(task_id, current_user.id)
    return service.update(task, data)
