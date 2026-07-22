import uuid

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.enums.workspace_role import WorkspaceRole
from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.project import ProjectCreate, ProjectUpdate

logger = get_logger(__name__)


class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        workspace_member_repository: WorkspaceMemberRepository,
        task_repository: TaskRepository,
    ) -> None:
        self.project_repository = project_repository
        self.workspace_member_repository = workspace_member_repository
        self.task_repository = task_repository
        self.db = project_repository.db

    def create(self, workspace_id: uuid.UUID, data: ProjectCreate) -> Project:
        """FR-020: criação restrita a Owner/Admin do workspace — já garantido
        pela dependency da rota (`require_workspace_admin_or_owner`);
        `workspace_id` vem exclusivamente do path, nunca do corpo."""
        project = Project(workspace_id=workspace_id, name=data.name, description=data.description)
        project = self.project_repository.create(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def list_by_workspace(self, workspace_id: uuid.UUID) -> list[Project]:
        """FR-022: visível a qualquer membro do workspace — já garantido por
        `require_workspace_member` na rota."""
        return self.project_repository.list_by_workspace(workspace_id)

    def get_by_id_or_404(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Project:
        """`GET/PATCH/DELETE /projects/{project_id}` (contracts/projects-and-
        tasks.md) não têm `workspace_id` no path — diferente das rotas
        aninhadas em `/workspaces/{workspace_id}/...`, a autorização não pode
        vir de uma dependency de rota resolvida automaticamente pelo path, e é
        resolvida aqui: primeiro localiza o projeto, depois confirma
        membership no workspace ao qual ele pertence. `404` (não `403`) para
        quem não é membro — nunca confirma a existência do projeto a quem não
        tem acesso (contracts/_conventions.md, nota de segurança)."""
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Projeto não encontrado.")

        role = self.workspace_member_repository.get_role(project.workspace_id, user_id)
        if role is None:
            raise NotFoundError("Projeto não encontrado.")

        return project

    def _require_admin_or_owner(self, project: Project, user_id: uuid.UUID) -> None:
        """Refinamento #7: só Owner/Admin editam/excluem projeto — Member tem
        visibilidade (já validada por `get_by_id_or_404`) mas não a ação."""
        role = self.workspace_member_repository.get_role(project.workspace_id, user_id)
        if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
            raise ForbiddenError(
                "Apenas o Owner ou um Admin do workspace podem executar esta ação."
            )

    def update(self, project_id: uuid.UUID, user_id: uuid.UUID, data: ProjectUpdate) -> Project:
        """FR-020/refinamento #7: `workspace_id` do projeto nunca é alterável
        por aqui (fora de `ProjectUpdate` — não há como "mover" um projeto
        entre workspaces); só `name`/`description`, e só os campos enviados."""
        project = self.get_by_id_or_404(project_id, user_id)
        self._require_admin_or_owner(project, user_id)

        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(project, field, value)

        project = self.project_repository.update(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Refinamento #6 (data-model.md): exclusão restrita a Owner/Admin,
        nunca um cascade "cego". `ON DELETE SET NULL` (banco) desvincula as
        tarefas do projeto na MESMA transação da exclusão — nenhuma `Task` é
        removida, nenhuma `TaskHistoryEntry` é gerada (fora do escopo de
        FR-041). `count_by_project` é usado exclusivamente para o log
        estruturado abaixo — nunca como pré-condição: a exclusão nunca é
        contada e então condicionada, é sempre permitida a quem tem a role."""
        project = self.get_by_id_or_404(project_id, user_id)
        self._require_admin_or_owner(project, user_id)

        workspace_id = project.workspace_id
        affected_tasks = self.task_repository.count_by_project(project_id)

        self.project_repository.delete(project)
        self.db.commit()

        logger.info(
            "Projeto excluído: project_id=%s workspace_id=%s autor=%s tarefas_desvinculadas=%d",
            project_id,
            workspace_id,
            user_id,
            affected_tasks,
        )
