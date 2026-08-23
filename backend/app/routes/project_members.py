import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.project_authorization import require_project_manage, require_project_visible
from app.models.project import Project
from app.repositories.project_member_repository import ProjectMemberRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.common import PaginatedResponse
from app.schemas.project_member import ProjectMemberCreate, ProjectMemberRead
from app.services.project_member_service import ProjectMemberService

router = APIRouter(prefix="/projects/{project_id}/members", tags=["project-members"])


def get_project_member_service(db: Session = Depends(get_db)) -> ProjectMemberService:
    return ProjectMemberService(
        ProjectMemberRepository(db),
        WorkspaceMemberRepository(db),
        UserRepository(db),
        TaskRepository(db),
    )


@router.get("", response_model=PaginatedResponse[ProjectMemberRead])
def list_project_members(
    project: Project = Depends(require_project_visible),
    service: ProjectMemberService = Depends(get_project_member_service),
) -> dict[str, object]:
    members = service.list_members(project.id)
    return {"items": members, "page": 1, "page_size": 20, "total": len(members)}


@router.post("", response_model=ProjectMemberRead, status_code=status.HTTP_201_CREATED)
def add_project_member(
    data: ProjectMemberCreate,
    project: Project = Depends(require_project_manage),
    service: ProjectMemberService = Depends(get_project_member_service),
) -> ProjectMemberRead:
    return service.add_member(project.id, project.workspace_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(
    user_id: uuid.UUID,
    project: Project = Depends(require_project_manage),
    service: ProjectMemberService = Depends(get_project_member_service),
) -> None:
    service.remove_member(project.id, user_id)
