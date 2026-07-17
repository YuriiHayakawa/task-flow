import uuid

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.enums.workspace_role import WorkspaceRole
from app.models.user import User
from app.repositories.workspace_member_repository import WorkspaceMemberRepository


def require_workspace_member(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceRole:
    """FR-020/FR-022: qualquer role visualiza. `404` (não `403`) para
    não-membros — nunca confirma a existência do workspace a quem não tem
    acesso (contracts/_conventions.md, nota de segurança)."""
    role = WorkspaceMemberRepository(db).get_role(workspace_id, current_user.id)
    if role is None:
        raise NotFoundError("Workspace não encontrado.")
    return role


def require_workspace_admin_or_owner(
    role: WorkspaceRole = Depends(require_workspace_member),
) -> WorkspaceRole:
    """FR-016/FR-020: Owner e Admin — Member recebe 403 (já é membro, logo
    tem visibilidade; só a ação específica é proibida)."""
    if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        raise ForbiddenError("Apenas o Owner ou um Admin do workspace podem executar esta ação.")
    return role


def require_workspace_owner(
    role: WorkspaceRole = Depends(require_workspace_member),
) -> WorkspaceRole:
    """FR-014/FR-017/FR-019: exclusivo do Owner."""
    if role != WorkspaceRole.OWNER:
        raise ForbiddenError("Apenas o Owner do workspace pode executar esta ação.")
    return role
