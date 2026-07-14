from fastapi import Depends

from app.core.exceptions import ForbiddenError
from app.dependencies.auth import get_current_user
from app.models.user import User


def require_system_admin(current_user: User = Depends(get_current_user)) -> User:
    """Ser System Admin é uma propriedade da plataforma, desacoplada de qualquer
    role de workspace (FR-044) — esta dependency não concede nenhum acesso além
    das rotas administrativas explicitamente protegidas por ela."""
    if not current_user.is_system_admin:
        raise ForbiddenError("Apenas o System Admin pode executar esta ação.")
    return current_user
