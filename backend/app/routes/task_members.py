import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.task_authorization import require_task_editor, require_task_visible
from app.models.task import Task
from app.repositories.task_member_repository import TaskMemberRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.task_member import TaskMemberCreate, TaskMemberRead
from app.services.task_member_service import TaskMemberService

router = APIRouter(prefix="/tasks/{task_id}/members", tags=["task-members"])


def get_task_member_service(db: Session = Depends(get_db)) -> TaskMemberService:
    return TaskMemberService(
        TaskMemberRepository(db), TaskRepository(db), WorkspaceMemberRepository(db), UserRepository(db)
    )


@router.get("", response_model=list[TaskMemberRead])
def list_task_members(
    task: Task = Depends(require_task_visible),
    service: TaskMemberService = Depends(get_task_member_service),
) -> list[TaskMemberRead]:
    # contracts/projects-and-tasks.md: "200 (lista de TaskMemberRead...)" —
    # sem "paginada" (ao contrário do equivalente em Workspace Members) —
    # envelope de paginação deliberadamente não usado aqui.
    return service.list_members(task.id)


@router.post("", response_model=TaskMemberRead, status_code=status.HTTP_201_CREATED)
def add_task_member(
    data: TaskMemberCreate,
    task: Task = Depends(require_task_editor),
    service: TaskMemberService = Depends(get_task_member_service),
) -> TaskMemberRead:
    return service.add_member(task.id, data.user_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_task_member(
    user_id: uuid.UUID,
    task: Task = Depends(require_task_editor),
    service: TaskMemberService = Depends(get_task_member_service),
) -> None:
    service.remove_member(task.id, user_id)
