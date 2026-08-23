import uuid

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.models.project_member import ProjectMember
from app.models.user import User


class ProjectMemberRepository:
    """Acesso a dados de `ProjectMember` — nenhuma regra de negócio aqui
    (Constitution III)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, member: ProjectMember) -> ProjectMember:
        self.db.add(member)
        self.db.flush()
        return member

    def get_by_project_and_user(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> ProjectMember | None:
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
        return self.db.scalars(stmt).first()

    def is_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return self.get_by_project_and_user(project_id, user_id) is not None

    def list_by_project(self, project_id: uuid.UUID) -> list[Row]:
        """Junta com `User` para trazer `name`/`email` numa única consulta
        (evita N+1) — mesmo padrão de `WorkspaceMemberRepository.
        list_by_workspace`. `created_at` sai rotulado como `joined_at`."""
        stmt = (
            select(
                ProjectMember.user_id,
                User.name,
                User.email,
                ProjectMember.created_at.label("joined_at"),
            )
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at)
        )
        return list(self.db.execute(stmt).all())

    def list_project_ids_for_user(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """Usado pela fórmula de acesso (data-model.md, research.md #2) em
        todos os pontos de enforcement — `ProjectService.list_by_workspace`/
        `get_by_id_or_404`, `TaskRepository.search`/`count_by_status`,
        `require_task_visible`."""
        stmt = select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
        return list(self.db.scalars(stmt))

    def delete(self, member: ProjectMember) -> None:
        self.db.delete(member)
        self.db.flush()
