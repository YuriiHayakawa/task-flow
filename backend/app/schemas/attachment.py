import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentRead(BaseModel):
    """`uploaded_by_id`/`uploaded_by_name`/`uploaded_by_email` achatados —
    mesmo padrão de `CommentRead`/`TaskMemberRead` (o contrato original lista
    apenas `uploaded_by`, decisão documentada no relatório da Fase 12).

    Não existe `AttachmentCreate`: o corpo de `POST` é `multipart/form-data`
    com apenas o arquivo (contracts/collaboration.md) — sem outros campos de
    formulário, tratado diretamente via `UploadFile` na rota, sem Schema
    Pydantic de entrada."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_by_id: uuid.UUID
    uploaded_by_name: str
    uploaded_by_email: str
    created_at: datetime
