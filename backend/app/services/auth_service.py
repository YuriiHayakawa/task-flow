from app.core.config import settings
from app.core.exceptions import AccountDisabledError, ConflictError, InvalidCredentialsError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate


class AuthService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository
        self.db = user_repository.db

    def register(self, data: UserCreate) -> User:
        """FR-001: e-mail único (case-insensitive, research.md #10) + hash bcrypt
        (research.md #3). A normalização para lowercase é responsabilidade deste
        Service, não do Schema (research.md #10)."""
        email = data.email.lower()
        if self.user_repository.get_by_email(email) is not None:
            raise ConflictError("Este e-mail já está cadastrado.")

        user = User(name=data.name, email=email, password_hash=hash_password(data.password))
        user = self.user_repository.create(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def login(self, data: LoginRequest) -> TokenResponse:
        """FR-002/FR-004: verifica a senha antes de checar `is_active`, para não
        abrir uma via de enumeração adicional (research.md #1). `ACCOUNT_DISABLED`
        (403) é sempre distinto de `INVALID_CREDENTIALS` (401)."""
        user = self.user_repository.get_by_email(data.email.lower())
        if user is None or not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError("E-mail ou senha inválidos.")

        if not user.is_active:
            raise AccountDisabledError("Esta conta está desativada.")

        access_token = create_access_token(str(user.id))
        return TokenResponse(
            access_token=access_token,
            expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        )
