import uuid

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AdminService:
    """FR-043 a FR-046 (US13). Deliberadamente a única dependência é
    `UserRepository` — nenhuma referência a `WorkspaceRepository`/
    `ProjectRepository`/`TaskRepository` em lugar algum desta classe. Essa
    ausência estrutural é a própria garantia de que ser System Admin não
    concede, por si só, acesso a workspaces/projetos/tarefas (FR-044/045)."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository
        self.db = user_repository.db

    def list_users(
        self, *, is_active: bool | None, page: int, page_size: int
    ) -> tuple[list[User], int]:
        return self.user_repository.list_all(is_active=is_active, page=page, page_size=page_size)

    def set_user_active(self, user_id: uuid.UUID, is_active: bool) -> User:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado.")

        user.is_active = is_active
        user = self.user_repository.update(user)
        self.db.commit()
        self.db.refresh(user)
        return user
