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
