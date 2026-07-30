import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class CommentCreate(BaseModel):
    """Corpo de `POST /api/v1/tasks/{task_id}/comments`
    (contracts/collaboration.md) — `task_id` vem do path, `author_id` vem do
    usuário autenticado; nenhum dos dois é aceito no corpo.

    Sem limite máximo de tamanho: `Comment.content` é `Text` (sem
    constraint de comprimento no Model/migração) e nenhum documento define
    um limite — não inventado aqui."""

    content: str

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        """FR-029: rejeita vazio ou apenas espaços — a checagem ocorre
        DEPOIS do `strip()` (um `Field(min_length=1)` sozinho aceitaria uma
        string só de espaços, já que seu comprimento bruto não é zero)."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("O conteúdo do comentário não pode ser vazio.")
        return stripped


class CommentRead(BaseModel):
    """`author_id`/`author_name`/`author_email` achatados — mesmo padrão de
    `WorkspaceMemberRead`/`TaskMemberRead`, não um objeto aninhado."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_id: uuid.UUID
    author_name: str
    author_email: str
    content: str
    created_at: datetime
