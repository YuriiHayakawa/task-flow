import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Acesso a dados de `User` — nenhuma regra de negócio aqui (Constitution III)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def get_by_email(self, email: str) -> User | None:
        """Comparação case-insensitive — reforça o índice funcional
        `ux_users_email_lower` (research.md #10) na camada de aplicação."""
        stmt = select(User).where(func.lower(User.email) == email.lower())
        return self.db.scalars(stmt).first()

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def update(self, user: User) -> User:
        self.db.flush()
        return user

    def email_taken(self, email: str, exclude_user_id: uuid.UUID) -> bool:
        """Comparação case-insensitive (research.md #10), excluindo o
        próprio usuário — sem isso, ninguém conseguiria salvar seu perfil
        mudando só o nome, ou reenviar o próprio e-mail sem alterá-lo."""
        stmt = select(User.id).where(
            func.lower(User.email) == email.lower(), User.id != exclude_user_id
        )
        return self.db.scalars(stmt).first() is not None

    def list_all(
        self, *, is_active: bool | None, page: int, page_size: int
    ) -> tuple[list[User], int]:
        """FR-043 (US13): listagem paginada de toda a base de usuários da
        plataforma (não amarrada a nenhum workspace). Paginação real
        (`LIMIT`/`OFFSET` + `COUNT` separado) — mesmo padrão de
        `TaskRepository.search` (US8): volume potencialmente grande, sem o
        limite natural dos sub-recursos de uma única tarefa. Ordenado por
        `created_at asc, id asc` (cadastro mais antigo primeiro; desempate
        determinístico) — ordem não definida pelo contrato, decisão
        documentada aqui."""
        base_query = select(User)
        count_query = select(func.count()).select_from(User)
        if is_active is not None:
            base_query = base_query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        total = self.db.scalar(count_query) or 0
        stmt = (
            base_query.order_by(User.created_at.asc(), User.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.scalars(stmt))
        return items, total
