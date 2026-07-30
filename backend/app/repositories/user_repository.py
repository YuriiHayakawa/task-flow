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
