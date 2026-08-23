import uuid

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.enums.workspace_role import WorkspaceRole
from app.models.project import Project
from app.models.user import User
from app.repositories.project_member_repository import ProjectMemberRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository


def require_project_visible(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    """Fórmula de acesso a projeto (data-model.md, 003-membros-projeto):
    Owner do workspace SEMPRE acessa; qualquer outra pessoa precisa ser
    `ProjectMember` explícito. `404` — nunca `403` — para quem não tem
    acesso, mesma convenção de `require_task_visible` (nunca confirma a
    existência do projeto a quem não tem acesso).

    Usada por rotas de projeto sem `workspace_id` no path
    (`/projects/{id}/...`), mesmo motivo de `task_authorization.py` existir
    separado de `authorization.py`."""
    project = ProjectRepository(db).get_by_id(project_id)
    if project is None:
        raise NotFoundError("Projeto não encontrado.")

    role = WorkspaceMemberRepository(db).get_role(project.workspace_id, current_user.id)
    if role is None:
        raise NotFoundError("Projeto não encontrado.")

    if role == WorkspaceRole.OWNER:
        return project

    if ProjectMemberRepository(db).is_member(project.id, current_user.id):
        return project

    raise NotFoundError("Projeto não encontrado.")


def require_project_manage(
    project: Project = Depends(require_project_visible),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    """FR-004: editar/excluir o projeto e gerenciar sua lista de membros
    exige role `OWNER`/`ADMIN` no workspace, ALÉM do acesso já garantido por
    `require_project_visible` — como essa dependency já exige "Owner OU
    membro explícito", um Admin que não é membro do projeto nunca chega
    aqui (recebe `404` antes), implementando "Admin só gerencia projeto do
    qual já participa" sem nenhum caso especial adicional (research.md
    #5)."""
    role = WorkspaceMemberRepository(db).get_role(project.workspace_id, current_user.id)
    if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        raise ForbiddenError("Apenas o Owner ou um Admin do workspace podem executar esta ação.")
    return project
