from pydantic import BaseModel


class UserStatusUpdate(BaseModel):
    """Corpo de `PATCH /api/v1/admin/users/{user_id}/status`
    (contracts/auth-and-users.md) — não altera nome/e-mail (fora do escopo
    do System Admin, FR-045); resposta reaproveita `UserRead` (já existe)."""

    is_active: bool
