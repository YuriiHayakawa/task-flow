import uuid

import jwt
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.exceptions import AccountDisabledError, NotAuthenticatedError
from app.core.security import decode_access_token
from app.dependencies.db import get_db
from app.models.user import User


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Decodifica o JWT e revalida `is_active` no banco a cada requisição — o JWT em
    si nunca é revogado antes de expirar; é essa revalidação que torna a desativação
    de conta efetiva de imediato (research.md #1)."""
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise NotAuthenticatedError("Autenticação necessária.")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise NotAuthenticatedError("Token inválido ou expirado.") from exc

    user = db.get(User, user_id)
    if user is None:
        raise NotAuthenticatedError("Token inválido ou expirado.")

    if not user.is_active:
        raise AccountDisabledError("Esta conta está desativada.")

    return user
