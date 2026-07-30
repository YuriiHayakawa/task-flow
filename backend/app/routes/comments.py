from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.dependencies.task_authorization import require_task_participant, require_task_visible
from app.models.task import Task
from app.models.user import User
from app.repositories.comment_repository import CommentRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.task_member_repository import TaskMemberRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.common import PaginatedResponse
from app.services.comment_service import CommentService

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["comments"])

_DEFAULT_PAGE_SIZE = 20


def get_comment_service(db: Session = Depends(get_db)) -> CommentService:
    return CommentService(
        CommentRepository(db),
        NotificationRepository(db),
        TaskRepository(db),
        TaskMemberRepository(db),
        UserRepository(db),
    )


@router.get("", response_model=PaginatedResponse[CommentRead])
def list_comments(
    task: Task = Depends(require_task_visible),
    service: CommentService = Depends(get_comment_service),
) -> dict[str, object]:
    # contracts/collaboration.md: "200 (lista paginada de CommentRead...)" —
    # ao contrário de Task Members, aqui o contrato diz "paginada" — mesmo
    # envelope/atalho (page=1, sem paginação real em SQL) já usado em
    # workspaces/projects/workspace-members.
    #
    # `CommentService.list_comments` refaz uma consulta de existência da
    # tarefa (`_get_task_or_404`) mesmo esta rota já tendo obtido a tarefa
    # autorizada via `require_task_visible` — consulta redundante conhecida
    # e aceita (mesmo trade-off já assumido em `TaskMemberService`, T083):
    # o Service permanece seguro/testável quando chamado diretamente, sem
    # depender de a rota já ter carregado a tarefa.
    comments = service.list_comments(task.id)
    return {"items": comments, "page": 1, "page_size": _DEFAULT_PAGE_SIZE, "total": len(comments)}


@router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def create_comment(
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    task: Task = Depends(require_task_participant),
    service: CommentService = Depends(get_comment_service),
) -> CommentRead:
    return service.create_comment(task.id, current_user.id, data)
