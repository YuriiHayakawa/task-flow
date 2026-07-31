import uuid
from pathlib import Path

from app.core.config import settings

_MAX_EXTENSION_LENGTH = 10


def is_content_type_allowed(content_type: str) -> bool:
    """FR-037/contracts/collaboration.md: valida contra
    `ATTACHMENTS_ALLOWED_CONTENT_TYPES` (config) antes de gravar em disco."""
    return content_type in settings.attachments_allowed_content_types_list


def is_size_allowed(size_bytes: int) -> bool:
    """Valida contra `ATTACHMENTS_MAX_SIZE_BYTES` (config) antes de gravar em
    disco."""
    return size_bytes <= settings.ATTACHMENTS_MAX_SIZE_BYTES


def generate_storage_filename(original_filename: str) -> str:
    """Nome de armazenamento gerado via UUID (research.md #12 — prevenção de
    path traversal): o nome nunca deriva do `original_filename` além de sua
    extensão, e mesmo essa é sanitizada (somente caracteres alfanuméricos e
    o ponto, tamanho limitado) antes de ser anexada ao UUID. `storage_path`
    persistido em `Attachment` é sempre este nome de arquivo isolado, nunca
    um caminho absoluto — resolvido contra `ATTACHMENTS_DIR` em tempo de
    leitura/escrita, nunca antes."""
    suffix = Path(original_filename).suffix.lower()
    safe_suffix = "".join(char for char in suffix if char.isalnum() or char == ".")
    safe_suffix = safe_suffix[:_MAX_EXTENSION_LENGTH]
    return f"{uuid.uuid4()}{safe_suffix}"


def resolve_storage_path(storage_filename: str) -> Path:
    return Path(settings.ATTACHMENTS_DIR) / storage_filename


def save_file(content: bytes, storage_filename: str) -> str:
    """Grava `content` em `ATTACHMENTS_DIR/storage_filename` e retorna o
    `storage_path` a persistir em `Attachment` (apenas o nome do arquivo,
    nunca um caminho absoluto)."""
    directory = Path(settings.ATTACHMENTS_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    resolve_storage_path(storage_filename).write_bytes(content)
    return storage_filename


def delete_file(storage_path: str) -> None:
    """Remove o arquivo físico correspondente. Chamado pelo
    `AttachmentService` somente **após** o `commit()` do registro no banco
    ter sucesso (research.md #12) — qualquer falha aqui é responsabilidade
    do chamador logar, nunca desta função."""
    resolve_storage_path(storage_path).unlink(missing_ok=True)
