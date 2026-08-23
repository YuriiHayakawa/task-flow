import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.models.user import User
from app.repositories.project_member_repository import ProjectMemberRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(
        TaskRepository(db), WorkspaceMemberRepository(db), ProjectMemberRepository(db)
    )


@router.get("", response_model=DashboardSummary)
def get_dashboard(
    workspace_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    personal_only: bool = False,
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummary:
    return service.get_summary(
        current_user.id,
        workspace_id=workspace_id,
        project_id=project_id,
        personal_only=personal_only,
    )
