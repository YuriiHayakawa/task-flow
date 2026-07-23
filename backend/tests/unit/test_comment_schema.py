"""T081 [US6] — validação isolada do schema `CommentCreate` (Pydantic puro,
sem banco): normalização de espaços, rejeição de conteúdo vazio/só espaços,
ausência de `task_id`/`author_id` no corpo."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas.comment import CommentCreate


def test_valid_content_accepted() -> None:
    comment = CommentCreate(content="Isso é um comentário válido.")

    assert comment.content == "Isso é um comentário válido."


def test_content_with_surrounding_whitespace_is_stripped() -> None:
    comment = CommentCreate(content="   comentário com espaços   ")

    assert comment.content == "comentário com espaços"


def test_empty_content_rejected() -> None:
    with pytest.raises(ValidationError):
        CommentCreate(content="")


def test_whitespace_only_content_rejected() -> None:
    with pytest.raises(ValidationError):
        CommentCreate(content="     ")


def test_tabs_and_newlines_only_content_rejected() -> None:
    with pytest.raises(ValidationError):
        CommentCreate(content="\t\n  \n")


def test_task_id_in_body_is_ignored_not_a_field() -> None:
    """`task_id`/`author_id` nunca são campos do schema — vêm do path e do
    usuário autenticado, respectivamente (mesmo padrão de `ProjectCreate`
    para `workspace_id`). Enviá-los no corpo é inofensivo: são ignorados
    pelo Pydantic (comportamento padrão já usado em todo o projeto, nenhum
    schema usa `extra=\"forbid\"`) e nunca lidos pelo Service."""
    comment = CommentCreate.model_validate(
        {
            "content": "Texto válido",
            "task_id": str(uuid.uuid4()),
            "author_id": str(uuid.uuid4()),
        }
    )

    assert comment.content == "Texto válido"
    assert not hasattr(comment, "task_id")
    assert not hasattr(comment, "author_id")
