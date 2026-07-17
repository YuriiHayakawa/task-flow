from typing import Generic, TypeVar

from pydantic import BaseModel

ItemT = TypeVar("ItemT")


class PaginatedResponse(BaseModel, Generic[ItemT]):
    """Envelope de listagem padrão (contracts/_conventions.md — Paginação)."""

    items: list[ItemT]
    page: int
    page_size: int
    total: int
