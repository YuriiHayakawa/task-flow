import uuid

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    BusinessRuleViolationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.enums.workspace_role import WorkspaceRole
from app.models.workspace_member import WorkspaceMember
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceRead
from app.schemas.workspace_member import WorkspaceMemberCreate, WorkspaceMemberRead
from app.services.workspace_service import WorkspaceService


class WorkspaceMemberService:
    def __init__(
        self,
        workspace_member_repository: WorkspaceMemberRepository,
        workspace_repository: WorkspaceRepository,
        user_repository: UserRepository,
        task_repository: TaskRepository,
    ) -> None:
        self.workspace_member_repository = workspace_member_repository
        self.workspace_repository = workspace_repository
        self.user_repository = user_repository
        self.task_repository = task_repository
        self.db = workspace_member_repository.db

    def list_members(self, workspace_id: uuid.UUID) -> list[WorkspaceMemberRead]:
        rows = self.workspace_member_repository.list_by_workspace(workspace_id)
        return [WorkspaceMemberRead.model_validate(row, from_attributes=True) for row in rows]

    def add_member(
        self, workspace_id: uuid.UUID, data: WorkspaceMemberCreate
    ) -> WorkspaceMemberRead:
        """FR-016: Owner/Admin adicionam Members (autorização já garantida
        pela dependency da rota); `role` restrito a MEMBER pelo Schema."""
        user = self.user_repository.get_by_id(data.user_id)
        if user is None:
            raise BusinessRuleViolationError("Usuário não encontrado.")

        if self.workspace_member_repository.get_role(workspace_id, data.user_id) is not None:
            raise ConflictError("Este usuário já é membro do workspace.")

        member = WorkspaceMember(workspace_id=workspace_id, user_id=data.user_id, role=data.role)
        member = self.workspace_member_repository.create(member)
        self.db.commit()
        self.db.refresh(member)

        return WorkspaceMemberRead(
            user_id=user.id, name=user.name, email=user.email, role=member.role, joined_at=member.created_at
        )

    def update_role(
        self, workspace_id: uuid.UUID, target_user_id: uuid.UUID, new_role: WorkspaceRole
    ) -> WorkspaceMemberRead:
        """FR-014/FR-019: só o Owner chega aqui (dependency da rota). O Owner
        nunca é um alvo válido desta operação — `transfer-ownership` é a
        única via para isso."""
        current_role = self.workspace_member_repository.get_role(workspace_id, target_user_id)
        if current_role is None:
            raise NotFoundError("Membro não encontrado neste workspace.")
        if current_role == WorkspaceRole.OWNER:
            raise ForbiddenError(
                "Não é possível alterar a role do Owner por esta operação — use /transfer-ownership."
            )

        member = self.workspace_member_repository.get_member_for_update(workspace_id, target_user_id)
        assert member is not None  # já confirmado por get_role acima, na mesma transação
        member.role = new_role
        member = self.workspace_member_repository.update(member)
        self.db.commit()
        self.db.refresh(member)

        user = self.user_repository.get_by_id(target_user_id)
        assert user is not None
        return WorkspaceMemberRead(
            user_id=user.id, name=user.name, email=user.email, role=member.role, joined_at=member.created_at
        )

    def remove_member(
        self, workspace_id: uuid.UUID, target_user_id: uuid.UUID, caller_role: WorkspaceRole
    ) -> None:
        """FR-015/FR-016/FR-019: a rota exige no mínimo Owner **ou** Admin
        (`require_workspace_admin_or_owner`); aqui refinamos a regra —
        remover um Member é permitido a Owner/Admin, mas remover um Admin é
        exclusivo do Owner. O Owner nunca é removível por aqui. FR-024/FR-025:
        bloqueia se o membro for responsável por tarefas ativas no workspace,
        até reatribuição."""
        role = self.workspace_member_repository.get_role(workspace_id, target_user_id)
        if role is None:
            raise NotFoundError("Membro não encontrado neste workspace.")
        if role == WorkspaceRole.OWNER:
            raise ForbiddenError(
                "O Owner não pode ser removido — transfira a titularidade antes de sair."
            )
        if role == WorkspaceRole.ADMIN and caller_role != WorkspaceRole.OWNER:
            raise ForbiddenError("Apenas o Owner pode remover um Admin do workspace.")

        active_tasks = self.task_repository.list_active_by_assignee_in_workspace(
            workspace_id, target_user_id
        )
        if active_tasks:
            raise ConflictError(
                "Este membro é responsável por tarefas ativas neste workspace — "
                "reatribua-as antes de removê-lo.",
                details=[{"task_id": str(task.id), "title": task.title} for task in active_tasks],
            )

        member = self.workspace_member_repository.get_member_for_update(workspace_id, target_user_id)
        assert member is not None
        self.workspace_member_repository.delete(member)
        self.db.commit()

    def transfer_ownership(
        self, workspace_id: uuid.UUID, current_owner_id: uuid.UUID, new_owner_user_id: uuid.UUID
    ) -> WorkspaceRead:
        """research.md #20: bloqueio pessimista duplo (`SELECT ... FOR
        UPDATE`) na linha do Owner atual e na do membro-alvo, com
        reconfirmação sob o lock de que quem chamou ainda é o Owner —
        serializa transferências concorrentes; o índice único parcial
        `ux_workspace_members_one_owner` é a garantia final de banco."""
        owner_member = self.workspace_member_repository.get_owner_for_update(workspace_id)
        if owner_member is None or owner_member.user_id != current_owner_id:
            # A titularidade mudou entre a autorização da rota e a obtenção do
            # lock (corrida com outra transferência concorrente) — nunca agir
            # sobre um estado desatualizado.
            raise ConflictError(
                "A titularidade deste workspace mudou; recarregue e tente novamente."
            )

        target_member = self.workspace_member_repository.get_member_for_update(
            workspace_id, new_owner_user_id
        )
        if target_member is None:
            raise BusinessRuleViolationError("O novo Owner deve já ser membro do workspace.")

        # O índice único parcial `ux_workspace_members_one_owner` não é
        # postergável (DEFERRABLE) — cada UPDATE é checado imediatamente. Por
        # isso a rebaixada do Owner atual precisa ser flushada ISOLADAMENTE
        # antes de sequer atribuir o novo OWNER: se as duas atribuições forem
        # feitas antes do primeiro flush, o unit-of-work do SQLAlchemy pode
        # ordenar as duas UPDATEs em qualquer ordem (não necessariamente a
        # ordem de atribuição), e promover o candidato antes de rebaixar o
        # atual violaria o índice mesmo sem nenhuma concorrência real.
        owner_member.role = WorkspaceRole.ADMIN
        self.workspace_member_repository.update(owner_member)

        target_member.role = WorkspaceRole.OWNER
        self.workspace_member_repository.update(target_member)

        try:
            self.db.commit()
        except IntegrityError:
            # Última linha de defesa (research.md #20): o índice único parcial
            # `ux_workspace_members_one_owner` pegou uma corrida que o lock
            # pessimista não evitou (ex.: duas transações que travaram a MESMA
            # linha do Owner antes de qualquer uma comitar). Trata como o mesmo
            # conflito de concorrência já documentado, nunca como erro 500.
            self.db.rollback()
            raise ConflictError(
                "A titularidade deste workspace mudou; recarregue e tente novamente."
            ) from None

        workspace = self.workspace_repository.get_by_id(workspace_id)
        assert workspace is not None  # não pode ter sido excluído: a transação acima o travou
        return WorkspaceService.to_read(workspace, WorkspaceRole.ADMIN)
