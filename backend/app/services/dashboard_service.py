import uuid

from app.repositories.task_repository import TaskRepository
from app.schemas.dashboard import DashboardCounts, DashboardSummary
from app.utils.timezone import today_in_app_timezone


class DashboardService:
    def __init__(self, task_repository: TaskRepository) -> None:
        self.task_repository = task_repository

    def get_summary(self, user_id: uuid.UUID) -> DashboardSummary:
        """FR-047 a FR-050: combina tarefas pessoais do usuário com as dos
        workspaces dos quais participa. `workspace_ids` fica vazio até a
        US3/US4 introduzirem `WorkspaceMember` — a união é ativada em T065
        passando a lista real para `TaskRepository.count_by_status`, sem
        exigir alteração nesta função nem na consulta."""
        workspace_ids: list[uuid.UUID] = []
        counts = self.task_repository.count_by_status(
            creator_id=user_id,
            workspace_ids=workspace_ids,
            today=today_in_app_timezone(),
        )
        return DashboardSummary(counts=DashboardCounts(**counts))
