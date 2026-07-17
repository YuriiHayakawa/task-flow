import uuid

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.enums.workspace_role import WorkspaceRole
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


class WorkspaceRepository:
    """Acesso a dados de `Workspace` — nenhuma regra de negócio aqui (Constitution III)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, workspace: Workspace) -> Workspace:
        self.db.add(workspace)
        self.db.flush()
        return workspace

    def get_by_id(self, workspace_id: uuid.UUID) -> Workspace | None:
        return self.db.get(Workspace, workspace_id)

    def list_for_user(self, user_id: uuid.UUID) -> list[Row[tuple[Workspace, WorkspaceRole]]]:
        """Workspaces dos quais o usuário é membro (qualquer role), com a role
        do próprio usuário já resolvida na mesma consulta (evita N+1)."""
        stmt = (
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.desc())
        )
        return list(self.db.execute(stmt).all())

    def update(self, workspace: Workspace) -> Workspace:
        self.db.flush()
        return workspace

    def delete(self, workspace: Workspace) -> None:
        self.db.delete(workspace)
        self.db.flush()
