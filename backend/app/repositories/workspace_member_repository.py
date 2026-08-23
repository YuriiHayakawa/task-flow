import uuid

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.enums.workspace_role import WorkspaceRole
from app.models.user import User
from app.models.workspace_member import WorkspaceMember


class WorkspaceMemberRepository:
    """Acesso a dados de `WorkspaceMember` — nenhuma regra de negócio aqui
    (Constitution III). O bloqueio pessimista (`SELECT ... FOR UPDATE`) vive
    aqui como detalhe de acesso a dados; a decisão de QUANDO usá-lo é do
    Service (research.md #20)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, member: WorkspaceMember) -> WorkspaceMember:
        self.db.add(member)
        self.db.flush()
        return member

    def get_role(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> WorkspaceRole | None:
        stmt = select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id
        )
        return self.db.scalars(stmt).first()

    def get_owner_for_update(self, workspace_id: uuid.UUID) -> WorkspaceMember | None:
        """Trava a linha do Owner atual do workspace (research.md #20) —
        serializa transferências de titularidade concorrentes no mesmo
        workspace, sem bloquear operações não relacionadas."""
        stmt = (
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.role == WorkspaceRole.OWNER)
            .with_for_update()
        )
        return self.db.scalars(stmt).first()

    def get_member_for_update(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        stmt = (
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id)
            .with_for_update()
        )
        return self.db.scalars(stmt).first()

    def list_by_workspace(self, workspace_id: uuid.UUID) -> list[Row]:
        """Junta com `User` para trazer `name`/`email` em uma única consulta
        (evita N+1); `created_at` já sai rotulado como `joined_at`, o nome de
        campo exposto por `WorkspaceMemberRead` (contracts/workspaces.md)."""
        stmt = (
            select(
                WorkspaceMember.user_id,
                User.name,
                User.email,
                WorkspaceMember.role,
                WorkspaceMember.created_at.label("joined_at"),
            )
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.created_at)
        )
        return list(self.db.execute(stmt).all())

    def list_workspace_ids_for_user(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """Usado pelo `DashboardService` (T065) para ativar a união com
        tarefas de workspace nas contagens do dashboard."""
        stmt = select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
        return list(self.db.scalars(stmt))

    def list_owned_workspace_ids_for_user(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """Variante de `list_workspace_ids_for_user` filtrada a
        `role == OWNER` — usada pela fórmula de acesso a projeto (003-
        membros-projeto, research.md #2): o Owner de um workspace sempre
        acessa todos os projetos dele, mesmo sem ser `ProjectMember`
        explícito."""
        stmt = select(WorkspaceMember.workspace_id).where(
            WorkspaceMember.user_id == user_id, WorkspaceMember.role == WorkspaceRole.OWNER
        )
        return list(self.db.scalars(stmt))

    def update(self, member: WorkspaceMember) -> WorkspaceMember:
        self.db.flush()
        return member

    def delete(self, member: WorkspaceMember) -> None:
        self.db.delete(member)
        self.db.flush()
