import uuid

from app.core.logging import get_logger
from app.enums.workspace_role import WorkspaceRole
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.repositories.project_member_repository import ProjectMemberRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

logger = get_logger(__name__)


class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        workspace_member_repository: WorkspaceMemberRepository,
        task_repository: TaskRepository,
        project_member_repository: ProjectMemberRepository,
    ) -> None:
        self.project_repository = project_repository
        self.workspace_member_repository = workspace_member_repository
        self.task_repository = task_repository
        self.project_member_repository = project_member_repository
        self.db = project_repository.db

    def create(self, workspace_id: uuid.UUID, data: ProjectCreate, creator_id: uuid.UUID) -> ProjectRead:
        """FR-020: criação restrita a Owner/Admin do workspace — já garantido
        pela dependency da rota (`require_workspace_admin_or_owner`);
        `workspace_id` vem exclusivamente do path, nunca do corpo.

        003-membros-projeto/FR-003: quem cria vira o primeiro `ProjectMember`
        na mesma transação — mesmo padrão de `WorkspaceService.create` com o
        `WorkspaceMember(OWNER)`."""
        project = Project(workspace_id=workspace_id, name=data.name, description=data.description)
        project = self.project_repository.create(project)

        membership = ProjectMember(project_id=project.id, user_id=creator_id)
        self.project_member_repository.create(membership)

        self.db.commit()
        self.db.refresh(project)
        return self.to_read(project, is_member=True)

    def list_by_workspace(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> list[ProjectRead]:
        """FR-022 (inalterado): visível a qualquer membro do workspace — já
        garantido por `require_workspace_member` na rota.

        003-membros-projeto/FR-006: a partir de agora, "visível" não
        significa mais "todos veem todos" — `OWNER`/`ADMIN` continuam vendo
        a listagem completa (Admin precisa saber o que existe para poder
        gerenciar, mesmo sem abrir o conteúdo, com `is_member=False` nos que
        não participa); `MEMBER` só vê os projetos dos quais é membro
        explícito."""
        role = self.workspace_member_repository.get_role(workspace_id, user_id)
        projects = self.project_repository.list_by_workspace(workspace_id)

        if role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
            member_project_ids = set(
                self.project_member_repository.list_project_ids_for_user(user_id)
            )
            is_always_member = role == WorkspaceRole.OWNER
            return [
                self.to_read(
                    project, is_member=is_always_member or project.id in member_project_ids
                )
                for project in projects
            ]

        member_project_ids = set(self.project_member_repository.list_project_ids_for_user(user_id))
        return [
            self.to_read(project, is_member=True)
            for project in projects
            if project.id in member_project_ids
        ]

    def is_member(self, project: Project, user_id: uuid.UUID) -> bool:
        """Fórmula de acesso a projeto (data-model.md, 003-membros-projeto):
        Owner do workspace sempre tem acesso; qualquer outra pessoa precisa
        ser `ProjectMember` explícito."""
        role = self.workspace_member_repository.get_role(project.workspace_id, user_id)
        if role == WorkspaceRole.OWNER:
            return True
        return self.project_member_repository.is_member(project.id, user_id)

    @staticmethod
    def to_read(project: Project, is_member: bool) -> ProjectRead:
        return ProjectRead(
            id=project.id,
            workspace_id=project.workspace_id,
            name=project.name,
            description=project.description,
            is_member=is_member,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    def update(self, project: Project, data: ProjectUpdate) -> Project:
        """FR-020/refinamento #7: `workspace_id` do projeto nunca é alterável
        por aqui (fora de `ProjectUpdate` — não há como "mover" um projeto
        entre workspaces); só `name`/`description`, e só os campos enviados.

        003-membros-projeto: autorização (acesso ao projeto + role Owner/
        Admin) já garantida por inteiro pela dependency da rota
        (`require_project_manage`) — `project` chega aqui já resolvido e
        autorizado, mesmo padrão de `TaskService.update` recebendo a `Task`
        já validada por `require_task_editor`."""
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(project, field, value)

        project = self.project_repository.update(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, project: Project) -> None:
        """Refinamento #6 (data-model.md): exclusão restrita a Owner/Admin,
        nunca um cascade "cego". `ON DELETE SET NULL` (banco) desvincula as
        tarefas do projeto na MESMA transação da exclusão — nenhuma `Task` é
        removida, nenhuma `TaskHistoryEntry` é gerada (fora do escopo de
        FR-041). `count_by_project` é usado exclusivamente para o log
        estruturado abaixo — nunca como pré-condição: a exclusão nunca é
        contada e então condicionada, é sempre permitida a quem tem a role
        (garantida pela dependency da rota, `require_project_manage`)."""
        project_id = project.id
        workspace_id = project.workspace_id
        affected_tasks = self.task_repository.count_by_project(project_id)

        self.project_repository.delete(project)
        self.db.commit()

        logger.info(
            "Projeto excluído: project_id=%s workspace_id=%s tarefas_desvinculadas=%d",
            project_id,
            workspace_id,
            affected_tasks,
        )
