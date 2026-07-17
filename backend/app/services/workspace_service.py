import uuid

from sqlalchemy.engine import Row

from app.core.exceptions import NotFoundError
from app.enums.workspace_role import WorkspaceRole
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate


class WorkspaceService:
    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        workspace_member_repository: WorkspaceMemberRepository,
    ) -> None:
        self.workspace_repository = workspace_repository
        self.workspace_member_repository = workspace_member_repository
        self.db = workspace_repository.db

    def create(self, data: WorkspaceCreate, owner_id: uuid.UUID) -> WorkspaceRead:
        """FR-012: o criador vira Owner na mesma transação da criação do
        workspace."""
        workspace = Workspace(name=data.name, description=data.description)
        workspace = self.workspace_repository.create(workspace)

        owner_membership = WorkspaceMember(
            workspace_id=workspace.id, user_id=owner_id, role=WorkspaceRole.OWNER
        )
        self.workspace_member_repository.create(owner_membership)

        self.db.commit()
        self.db.refresh(workspace)
        return self.to_read(workspace, WorkspaceRole.OWNER)

    def list_for_user(self, user_id: uuid.UUID) -> list[WorkspaceRead]:
        rows: list[Row[tuple[Workspace, WorkspaceRole]]] = self.workspace_repository.list_for_user(
            user_id
        )
        return [self.to_read(workspace, role) for workspace, role in rows]

    def get_by_id_or_404(self, workspace_id: uuid.UUID) -> Workspace:
        workspace = self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace não encontrado.")
        return workspace

    def update(
        self, workspace: Workspace, data: WorkspaceUpdate, my_role: WorkspaceRole
    ) -> WorkspaceRead:
        """FR-017: restrito ao Owner — já garantido pela dependency da rota
        (`require_workspace_owner`) antes deste método ser chamado."""
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(workspace, field, value)

        workspace = self.workspace_repository.update(workspace)
        self.db.commit()
        self.db.refresh(workspace)
        return self.to_read(workspace, my_role)

    def delete(self, workspace: Workspace) -> None:
        """FR-017: exclusão restrita ao Owner. Cascade de banco (`ON DELETE
        CASCADE`, já definido nas migrações da Fase 2) remove projetos,
        tarefas e dados relacionados. A etapa de remoção de arquivos físicos
        de anexos (contracts/workspaces.md) fica documentada como limitação
        desta fase — `AttachmentService` só existe na US10, e nenhum anexo
        pode existir antes dela."""
        self.workspace_repository.delete(workspace)
        self.db.commit()

    @staticmethod
    def to_read(workspace: Workspace, my_role: WorkspaceRole) -> WorkspaceRead:
        return WorkspaceRead(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            my_role=my_role,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
