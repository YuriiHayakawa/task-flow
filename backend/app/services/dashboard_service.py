import uuid

from app.core.exceptions import BusinessRuleViolationError
from app.repositories.project_member_repository import ProjectMemberRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.dashboard import DashboardCounts, DashboardSummary
from app.utils.timezone import today_in_app_timezone


class DashboardService:
    def __init__(
        self,
        task_repository: TaskRepository,
        workspace_member_repository: WorkspaceMemberRepository,
        project_member_repository: ProjectMemberRepository,
    ) -> None:
        self.task_repository = task_repository
        self.workspace_member_repository = workspace_member_repository
        self.project_member_repository = project_member_repository

    def get_summary(
        self,
        user_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        personal_only: bool = False,
    ) -> DashboardSummary:
        """FR-047 a FR-050: combina tarefas pessoais do usuário com as dos
        workspaces dos quais participa (T065 — união ativada agora que
        `WorkspaceMember` existe; `TaskRepository.count_by_status` não
        precisou de nenhuma alteração, exatamente como planejado na Fase 4).

        Escopo opcional (`workspace_id`/`project_id`/`personal_only`) — não
        previsto pela spec original (US2), adicionado a pedido do produto
        para permitir alternar entre um resumo combinado e um resumo restrito
        a um único workspace, projeto, ou só às tarefas pessoais. No máximo
        um dos três MUST ser informado por vez; a autorização de acesso ao
        workspace/projeto não precisa de checagem própria aqui — filtrar por
        um workspace/projeto do qual o usuário não é membro já não retorna
        nada, porque `count_by_status` aplica o filtro sobre a mesma
        visibilidade (`visible`) que já restringe aos workspaces do próprio
        usuário."""
        scope_count = sum([workspace_id is not None, project_id is not None, personal_only])
        if scope_count > 1:
            raise BusinessRuleViolationError(
                "Informe no máximo um filtro de escopo (workspace, projeto ou pessoal) por vez."
            )

        workspace_ids = self.workspace_member_repository.list_workspace_ids_for_user(user_id)
        # 003-membros-projeto: mesma correção de `TaskService.search` — sem
        # isso, tarefas de projetos restritos aos quais o usuário não tem
        # acesso continuariam contadas aqui (research.md #3).
        owner_workspace_ids = self.workspace_member_repository.list_owned_workspace_ids_for_user(
            user_id
        )
        member_project_ids = self.project_member_repository.list_project_ids_for_user(user_id)
        counts = self.task_repository.count_by_status(
            creator_id=user_id,
            workspace_ids=workspace_ids,
            owner_workspace_ids=owner_workspace_ids,
            member_project_ids=member_project_ids,
            today=today_in_app_timezone(),
            scope_workspace_id=workspace_id,
            scope_project_id=project_id,
            personal_only=personal_only,
        )
        return DashboardSummary(counts=DashboardCounts(**counts))
