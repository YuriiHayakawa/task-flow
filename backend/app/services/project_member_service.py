import uuid

from app.core.exceptions import BusinessRuleViolationError, ConflictError, NotFoundError
from app.models.project_member import ProjectMember
from app.repositories.project_member_repository import ProjectMemberRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.project_member import ProjectMemberCreate, ProjectMemberRead


class ProjectMemberService:
    def __init__(
        self,
        project_member_repository: ProjectMemberRepository,
        workspace_member_repository: WorkspaceMemberRepository,
        user_repository: UserRepository,
        task_repository: TaskRepository,
    ) -> None:
        self.project_member_repository = project_member_repository
        self.workspace_member_repository = workspace_member_repository
        self.user_repository = user_repository
        self.task_repository = task_repository
        self.db = project_member_repository.db

    def list_members(self, project_id: uuid.UUID) -> list[ProjectMemberRead]:
        rows = self.project_member_repository.list_by_project(project_id)
        return [ProjectMemberRead.model_validate(row, from_attributes=True) for row in rows]

    def add_member(
        self, project_id: uuid.UUID, workspace_id: uuid.UUID, data: ProjectMemberCreate
    ) -> ProjectMemberRead:
        """FR-002: `user_id` MUST já ser membro do workspace do projeto —
        sem isso, não faz sentido conceder acesso a um projeto pra alguém
        que nem está no workspace. FR-004/FR-005: autorização (Owner, ou
        Admin já membro do projeto) já garantida pela dependency da rota
        (`require_project_manage`)."""
        user = self.user_repository.get_by_id(data.user_id)
        if user is None:
            raise BusinessRuleViolationError("Usuário não encontrado.")

        if self.workspace_member_repository.get_role(workspace_id, data.user_id) is None:
            raise BusinessRuleViolationError(
                "Esta pessoa precisa ser membro do workspace antes de ser adicionada ao projeto."
            )

        if self.project_member_repository.is_member(project_id, data.user_id):
            raise ConflictError("Este usuário já é membro do projeto.")

        member = ProjectMember(project_id=project_id, user_id=data.user_id)
        member = self.project_member_repository.create(member)
        self.db.commit()
        self.db.refresh(member)

        return ProjectMemberRead(
            user_id=user.id, name=user.name, email=user.email, joined_at=member.created_at
        )

    def remove_member(self, project_id: uuid.UUID, target_user_id: uuid.UUID) -> None:
        """FR-010: recusa a remoção enquanto a pessoa tiver tarefas ativas
        (status != DONE) atribuídas a ela DENTRO DESTE PROJETO
        especificamente — mesmo padrão de
        `WorkspaceMemberService.remove_member` (FR-024/FR-025)."""
        member = self.project_member_repository.get_by_project_and_user(project_id, target_user_id)
        if member is None:
            raise NotFoundError("Membro não encontrado neste projeto.")

        active_tasks = self.task_repository.list_active_by_assignee_in_project(
            project_id, target_user_id
        )
        if active_tasks:
            raise ConflictError(
                "Este membro é responsável por tarefas ativas neste projeto — "
                "reatribua-as antes de removê-lo.",
                details=[{"task_id": str(task.id), "title": task.title} for task in active_tasks],
            )

        self.project_member_repository.delete(member)
        self.db.commit()
