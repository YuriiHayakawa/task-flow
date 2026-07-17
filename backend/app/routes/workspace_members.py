import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.authorization import (
    require_workspace_admin_or_owner,
    require_workspace_member,
    require_workspace_owner,
)
from app.dependencies.db import get_db
from app.enums.workspace_role import WorkspaceRole
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.common import PaginatedResponse
from app.schemas.workspace_member import (
    WorkspaceMemberCreate,
    WorkspaceMemberRead,
    WorkspaceMemberRoleUpdate,
)
from app.services.workspace_member_service import WorkspaceMemberService

router = APIRouter(prefix="/workspaces/{workspace_id}/members", tags=["workspace-members"])


def get_workspace_member_service(db: Session = Depends(get_db)) -> WorkspaceMemberService:
    return WorkspaceMemberService(
        WorkspaceMemberRepository(db), WorkspaceRepository(db), UserRepository(db), TaskRepository(db)
    )


@router.get("", response_model=PaginatedResponse[WorkspaceMemberRead])
def list_members(
    workspace_id: uuid.UUID,
    _role: WorkspaceRole = Depends(require_workspace_member),
    service: WorkspaceMemberService = Depends(get_workspace_member_service),
) -> dict[str, object]:
    members = service.list_members(workspace_id)
    return {"items": members, "page": 1, "page_size": 20, "total": len(members)}


@router.post("", response_model=WorkspaceMemberRead, status_code=status.HTTP_201_CREATED)
def add_member(
    workspace_id: uuid.UUID,
    data: WorkspaceMemberCreate,
    _role: WorkspaceRole = Depends(require_workspace_admin_or_owner),
    service: WorkspaceMemberService = Depends(get_workspace_member_service),
) -> WorkspaceMemberRead:
    return service.add_member(workspace_id, data)


@router.patch("/{user_id}/role", response_model=WorkspaceMemberRead)
def update_member_role(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    data: WorkspaceMemberRoleUpdate,
    _role: WorkspaceRole = Depends(require_workspace_owner),
    service: WorkspaceMemberService = Depends(get_workspace_member_service),
) -> WorkspaceMemberRead:
    return service.update_role(workspace_id, user_id, data.role)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    caller_role: WorkspaceRole = Depends(require_workspace_admin_or_owner),
    service: WorkspaceMemberService = Depends(get_workspace_member_service),
) -> None:
    service.remove_member(workspace_id, user_id, caller_role)
