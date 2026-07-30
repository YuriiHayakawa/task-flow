from app.core.exceptions import ConflictError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate


class UserService:
    """FR-051 a FR-054 (US7)."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository
        self.db = user_repository.db

    def get_me(self, user: User) -> User:
        return user

    def update_me(self, user: User, data: UserUpdate) -> User:
        """FR-052/FR-053: `name` livre; `email` único (case-insensitive,
        research.md #10), normalizado para lowercase aqui — mesmo padrão de
        `AuthService.register` (normalização é responsabilidade do Service,
        nunca do Schema). `UserUpdate` já garante que ao menos um campo foi
        enviado e rejeita campos fora do MVP (senha/foto — FR-054)."""
        changes = data.model_dump(exclude_unset=True)

        if "email" in changes:
            new_email = changes["email"].lower()
            if self.user_repository.email_taken(new_email, exclude_user_id=user.id):
                raise ConflictError("Este e-mail já está em uso.")
            changes["email"] = new_email

        for field, value in changes.items():
            setattr(user, field, value)

        user = self.user_repository.update(user)
        self.db.commit()
        self.db.refresh(user)
        return user
