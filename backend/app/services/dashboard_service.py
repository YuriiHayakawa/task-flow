import uuid

from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.dashboard import DashboardCounts, DashboardSummary
from app.utils.timezone import today_in_app_timezone


class DashboardService:
    def __init__(
        self, task_repository: TaskRepository, workspace_member_repository: WorkspaceMemberRepository
    ) -> None:
        self.task_repository = task_repository
        self.workspace_member_repository = workspace_member_repository

    def get_summary(self, user_id: uuid.UUID) -> DashboardSummary:
        """FR-047 a FR-050: combina tarefas pessoais do usuário com as dos
        workspaces dos quais participa (T065 — união ativada agora que
        `WorkspaceMember` existe; `TaskRepository.count_by_status` não
        precisou de nenhuma alteração, exatamente como planejado na Fase 4)."""
        workspace_ids = self.workspace_member_repository.list_workspace_ids_for_user(user_id)
        counts = self.task_repository.count_by_status(
            creator_id=user_id,
            workspace_ids=workspace_ids,
            today=today_in_app_timezone(),
        )
        return DashboardSummary(counts=DashboardCounts(**counts))
