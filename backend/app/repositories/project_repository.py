import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project


class ProjectRepository:
    """Acesso a dados de `Project` — nenhuma regra de negócio aqui (Constitution III)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, project: Project) -> Project:
        self.db.add(project)
        self.db.flush()
        return project

    def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        return self.db.get(Project, project_id)

    def list_by_workspace(self, workspace_id: uuid.UUID) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def update(self, project: Project) -> Project:
        self.db.flush()
        return project

    def delete(self, project: Project) -> None:
        self.db.delete(project)
        self.db.flush()
