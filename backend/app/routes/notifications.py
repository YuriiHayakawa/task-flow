import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.common import PaginatedResponse
from app.schemas.notification import NotificationRead
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])

_DEFAULT_PAGE_SIZE = 20


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(NotificationRepository(db), TaskRepository(db))


@router.get("", response_model=PaginatedResponse[NotificationRead])
def list_notifications(
    is_read: bool | None = None,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict[str, object]:
    # contracts/dashboard-and-notifications.md: "paginação padrão" — mesmo
    # atalho (page=1, sem paginação real em SQL) já usado em Comments/Task
    # History, não a paginação real de Task Search.
    notifications = service.list_notifications(current_user.id, is_read)
    return {
        "items": notifications,
        "page": 1,
        "page_size": _DEFAULT_PAGE_SIZE,
        "total": len(notifications),
    }


@router.patch("/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict[str, int]:
    # Registrada ANTES de "/{notification_id}/read" — rota estática precisa
    # vir primeiro, senão "read-all" seria interpretado como um
    # `notification_id` pela rota dinâmica abaixo.
    updated = service.mark_all_as_read(current_user.id)
    return {"updated": updated}


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationRead:
    return service.mark_as_read(current_user.id, notification_id)
