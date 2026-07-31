import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies.admin import require_system_admin
from app.dependencies.db import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.admin import UserStatusUpdate
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserRead
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin/users", tags=["admin"])


def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    return AdminService(UserRepository(db))


@router.get("", response_model=PaginatedResponse[UserRead])
def list_users(
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin: User = Depends(require_system_admin),
    service: AdminService = Depends(get_admin_service),
) -> dict[str, object]:
    # contracts/auth-and-users.md: nenhum parâmetro workspace_id/project_id/
    # task_id existe aqui — o System Admin não tem rota de acesso a esses
    # recursos por meio desta API (FR-044/FR-046).
    users, total = service.list_users(is_active=is_active, page=page, page_size=page_size)
    return {"items": users, "page": page, "page_size": page_size, "total": total}


@router.patch("/{user_id}/status", response_model=UserRead)
def update_user_status(
    user_id: uuid.UUID,
    data: UserStatusUpdate,
    _admin: User = Depends(require_system_admin),
    service: AdminService = Depends(get_admin_service),
) -> User:
    return service.set_user_active(user_id, data.is_active)
