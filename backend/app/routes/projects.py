import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.authorization import require_workspace_admin_or_owner, require_workspace_member
from app.dependencies.db import get_db
from app.enums.workspace_role import WorkspaceRole
from app.models.project import Project
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.common import PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project_service import ProjectService

# Sem prefix único: este módulo cobre tanto rotas aninhadas em
# `/workspaces/{workspace_id}/projects` quanto `/projects/{project_id}`
# (contracts/projects-and-tasks.md) — as segundas não têm `workspace_id` no
# path, então não compartilham prefixo com as primeiras.
router = APIRouter(tags=["projects"])

_DEFAULT_PAGE_SIZE = 20


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(ProjectRepository(db), WorkspaceMemberRepository(db), TaskRepository(db))


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    workspace_id: uuid.UUID,
    data: ProjectCreate,
    _role: WorkspaceRole = Depends(require_workspace_admin_or_owner),
    service: ProjectService = Depends(get_project_service),
) -> Project:
    return service.create(workspace_id, data)


@router.get("/workspaces/{workspace_id}/projects", response_model=PaginatedResponse[ProjectRead])
def list_projects(
    workspace_id: uuid.UUID,
    _role: WorkspaceRole = Depends(require_workspace_member),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, object]:
    projects = service.list_by_workspace(workspace_id)
    return {"items": projects, "page": 1, "page_size": _DEFAULT_PAGE_SIZE, "total": len(projects)}


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> Project:
    # Sem `workspace_id` no path (ao contrário das rotas acima), a
    # autorização não pode vir de uma dependency resolvida automaticamente —
    # `ProjectService.get_by_id_or_404` resolve membership internamente.
    return service.get_by_id_or_404(project_id, current_user.id)


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> Project:
    return service.update(project_id, current_user.id, data)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> None:
    service.delete(project_id, current_user.id)
