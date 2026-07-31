import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.dependencies.task_authorization import require_task_participant, require_task_visible
from app.models.task import Task
from app.models.user import User
from app.repositories.attachment_repository import AttachmentRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.attachment import AttachmentRead
from app.services.attachment_service import AttachmentService

router = APIRouter(prefix="/tasks/{task_id}/attachments", tags=["attachments"])


def get_attachment_service(db: Session = Depends(get_db)) -> AttachmentService:
    return AttachmentService(
        AttachmentRepository(db), TaskRepository(db), WorkspaceMemberRepository(db)
    )


@router.get("", response_model=list[AttachmentRead])
def list_attachments(
    task: Task = Depends(require_task_visible),
    service: AttachmentService = Depends(get_attachment_service),
) -> list[AttachmentRead]:
    # contracts/collaboration.md: "200 (lista de AttachmentRead...)" — sem
    # paginação (volume esperado baixo por tarefa), mesmo padrão de
    # Checklist/Task Members.
    return service.list_attachments(task.id)


@router.post("", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    task: Task = Depends(require_task_participant),
    service: AttachmentService = Depends(get_attachment_service),
) -> AttachmentRead:
    content = await file.read()
    return service.create_attachment(
        task.id,
        current_user,
        original_filename=file.filename or "arquivo",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )


@router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: uuid.UUID,
    task: Task = Depends(require_task_visible),
    service: AttachmentService = Depends(get_attachment_service),
) -> FileResponse:
    # baixar é uma forma de leitura (contracts/collaboration.md) —
    # `require_task_visible`, não `require_task_participant`.
    file_path, original_filename, content_type = service.get_download_target(task.id, attachment_id)
    return FileResponse(path=file_path, filename=original_filename, media_type=content_type)


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    task: Task = Depends(require_task_visible),
    service: AttachmentService = Depends(get_attachment_service),
) -> None:
    # autorização uploader-ou-Owner/Admin resolvida dentro do Service (não
    # há `workspace_id` no path para reaproveitar `require_workspace_admin_
    # or_owner` como dependency — decisão documentada no relatório da Fase 12).
    service.delete_attachment(task.id, attachment_id, current_user)
