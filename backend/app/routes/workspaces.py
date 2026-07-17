import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.authorization import require_workspace_member, require_workspace_owner
from app.dependencies.db import get_db
from app.enums.workspace_role import WorkspaceRole
from app.models.user import User
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.common import PaginatedResponse
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate
from app.schemas.workspace_member import TransferOwnershipRequest
from app.services.workspace_member_service import WorkspaceMemberService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def get_workspace_service(db: Session = Depends(get_db)) -> WorkspaceService:
    return WorkspaceService(WorkspaceRepository(db), WorkspaceMemberRepository(db))


def get_workspace_member_service(db: Session = Depends(get_db)) -> WorkspaceMemberService:
    return WorkspaceMemberService(
        WorkspaceMemberRepository(db), WorkspaceRepository(db), UserRepository(db), TaskRepository(db)
    )


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(
    data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceRead:
    return service.create(data, owner_id=current_user.id)


@router.get("", response_model=PaginatedResponse[WorkspaceRead])
def list_workspaces(
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> dict[str, object]:
    workspaces = service.list_for_user(current_user.id)
    return {"items": workspaces, "page": 1, "page_size": 20, "total": len(workspaces)}


@router.get("/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(
    workspace_id: uuid.UUID,
    my_role: WorkspaceRole = Depends(require_workspace_member),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceRead:
    workspace = service.get_by_id_or_404(workspace_id)
    return service.to_read(workspace, my_role)


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
def update_workspace(
    workspace_id: uuid.UUID,
    data: WorkspaceUpdate,
    my_role: WorkspaceRole = Depends(require_workspace_owner),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceRead:
    workspace = service.get_by_id_or_404(workspace_id)
    return service.update(workspace, data, my_role)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: uuid.UUID,
    _my_role: WorkspaceRole = Depends(require_workspace_owner),
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    workspace = service.get_by_id_or_404(workspace_id)
    service.delete(workspace)


@router.post("/{workspace_id}/transfer-ownership", response_model=WorkspaceRead)
def transfer_ownership(
    workspace_id: uuid.UUID,
    data: TransferOwnershipRequest,
    current_user: User = Depends(get_current_user),
    _my_role: WorkspaceRole = Depends(require_workspace_owner),
    member_service: WorkspaceMemberService = Depends(get_workspace_member_service),
) -> WorkspaceRead:
    return member_service.transfer_ownership(workspace_id, current_user.id, data.new_owner_user_id)
