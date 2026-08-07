import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _validate_email_shape(value: str) -> str:
    value = value.strip()
    if "@" not in value or value.startswith("@") or value.endswith("@"):
        raise ValueError("E-mail inválido.")
    return value


class UserCreate(BaseModel):
    """Corpo de `POST /api/v1/auth/register` (contracts/auth-and-users.md)."""

    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email_shape(cls, value: str) -> str:
        return _validate_email_shape(value)


class UserUpdate(BaseModel):
    """Corpo de `PATCH /api/v1/users/me` (contracts/auth-and-users.md).

    `extra="forbid"` é uma exceção DELIBERADA ao padrão do resto do projeto
    (que ignora campos desconhecidos, ex.: `ProjectCreate`/`CommentCreate`)
    — exigência literal do contrato: "campos não reconhecidos são
    rejeitados com 422, não silenciosamente ignorados" (FR-054 — senha,
    foto e exclusão de conta MUST NOT ser aceitas por este endpoint)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email_shape(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_email_shape(value)

    @model_validator(mode="after")
    def at_least_one_field_provided(self) -> "UserUpdate":
        """Contrato: "ambos opcionais, ao menos um obrigatório"."""
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar (name ou email).")
        return self


class UserRead(BaseModel):
    """Nunca expõe `password_hash` (Constitution: Schemas).

    `is_system_admin` exposto aqui (Fase 17, frontend) para que o cliente
    saiba se deve exibir a rota/seção exclusiva de System Admin — mesmo
    padrão já usado para `is_active`: sempre lido do banco a cada resposta,
    nunca embutido no JWT (`core/security.py`)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    is_active: bool
    is_system_admin: bool
    created_at: datetime


class UserLookupRead(BaseModel):
    """Corpo de resposta de `GET /api/v1/users/lookup`
    (contracts/auth-and-users.md) — projeção mínima e não sensível (sem
    `is_active`/`is_system_admin`), usada só para resolver um e-mail em
    `user_id` no fluxo de "adicionar membro" de um workspace
    (`POST /workspaces/{id}/members` exige `user_id`, não e-mail)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
