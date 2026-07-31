import uuid
from pathlib import Path

from app.core.exceptions import BusinessRuleViolationError, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.enums.workspace_role import WorkspaceRole
from app.models.attachment import Attachment
from app.models.task import Task
from app.models.user import User
from app.repositories.attachment_repository import AttachmentRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.attachment import AttachmentRead
from app.utils import file_storage

logger = get_logger(__name__)


class AttachmentService:
    """FR-037/FR-038 (US10). Mesmo padrão de `CommentService`/
    `ChecklistItemService`: os métodos recebem `task_id` (não um `Task`
    pré-carregado pela rota) e resolvem tudo via repository — quem autoriza
    visibilidade/colaboração é a dependency da rota (`require_task_visible`/
    `require_task_participant`). A autorização de `delete_attachment`
    (uploader OU Owner/Admin do workspace) é resolvida aqui, e não por uma
    dependency de rota, pois depende do `uploaded_by_id` do anexo específico
    — dado inexistente até o registro ser carregado (decisão documentada no
    relatório de abertura da Fase 12)."""

    def __init__(
        self,
        attachment_repository: AttachmentRepository,
        task_repository: TaskRepository,
        workspace_member_repository: WorkspaceMemberRepository,
    ) -> None:
        self.attachment_repository = attachment_repository
        self.task_repository = task_repository
        self.workspace_member_repository = workspace_member_repository
        self.db = attachment_repository.db

    def _get_task_or_404(self, task_id: uuid.UUID) -> Task:
        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise NotFoundError("Tarefa não encontrada.")
        return task

    def _get_attachment_or_404(self, task_id: uuid.UUID, attachment_id: uuid.UUID) -> Attachment:
        """Escopado por `task_id` E `attachment_id` juntos (via
        `get_by_task_and_id`) — um anexo de outra tarefa nunca é encontrado,
        mesmo com o `attachment_id` certo."""
        attachment = self.attachment_repository.get_by_task_and_id(task_id, attachment_id)
        if attachment is None:
            raise NotFoundError("Anexo não encontrado.")
        return attachment

    def list_attachments(self, task_id: uuid.UUID) -> list[AttachmentRead]:
        self._get_task_or_404(task_id)
        rows = self.attachment_repository.list_by_task(task_id)
        return [AttachmentRead.model_validate(row, from_attributes=True) for row in rows]

    def create_attachment(
        self,
        task_id: uuid.UUID,
        uploader: User,
        *,
        original_filename: str,
        content_type: str,
        content: bytes,
    ) -> AttachmentRead:
        """Valida tipo/tamanho **antes** de gravar em disco
        (contracts/collaboration.md). Grava o arquivo físico antes do
        `commit()` do registro — se o commit falhar depois, o pior cenário
        possível é um arquivo físico órfão sem registro correspondente, que
        é o único tipo de inconsistência considerada segura/reconciliável
        (research.md #12), nunca o inverso (registro apontando para nada)."""
        self._get_task_or_404(task_id)

        size_bytes = len(content)
        if not file_storage.is_content_type_allowed(content_type):
            raise BusinessRuleViolationError(f"Tipo de arquivo não permitido: {content_type}.")
        if not file_storage.is_size_allowed(size_bytes):
            raise BusinessRuleViolationError("Tamanho do arquivo excede o máximo permitido.")

        storage_filename = file_storage.generate_storage_filename(original_filename)
        storage_path = file_storage.save_file(content, storage_filename)

        attachment = Attachment(
            task_id=task_id,
            uploaded_by_id=uploader.id,
            original_filename=original_filename,
            storage_path=storage_path,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        self.attachment_repository.create(attachment)
        self.db.commit()
        self.db.refresh(attachment)

        return AttachmentRead(
            id=attachment.id,
            original_filename=attachment.original_filename,
            content_type=attachment.content_type,
            size_bytes=attachment.size_bytes,
            uploaded_by_id=uploader.id,
            uploaded_by_name=uploader.name,
            uploaded_by_email=uploader.email,
            created_at=attachment.created_at,
        )

    def get_download_target(self, task_id: uuid.UUID, attachment_id: uuid.UUID) -> tuple[Path, str, str]:
        """Retorna `(caminho_absoluto, original_filename, content_type)` para
        a rota montar a resposta de download com `Content-Disposition`
        (contracts/collaboration.md) — o nome original nunca é usado para
        localizar o arquivo, só para exibição."""
        self._get_task_or_404(task_id)
        attachment = self._get_attachment_or_404(task_id, attachment_id)
        file_path = file_storage.resolve_storage_path(attachment.storage_path)
        return file_path, attachment.original_filename, attachment.content_type

    def delete_attachment(
        self, task_id: uuid.UUID, attachment_id: uuid.UUID, requesting_user: User
    ) -> None:
        """Fluxo de exclusão controlada (research.md #12, refinamento #7):
        (1) localizar anexo; (2) autorizar (uploader OU Owner/Admin do
        workspace da tarefa — tarefa pessoal não tem workspace, então só o
        uploader pode remover); (3) excluir o registro em transação e
        `commit()`; (4) remover o arquivo físico somente após o commit ter
        sucesso; (5) se a remoção física falhar, logar `ERROR` sem falhar a
        resposta — o registro já foi removido com sucesso, que é o estado
        autoritativo."""
        task = self._get_task_or_404(task_id)
        attachment = self._get_attachment_or_404(task_id, attachment_id)

        is_uploader = attachment.uploaded_by_id == requesting_user.id
        is_workspace_admin = False
        if task.workspace_id is not None:
            role = self.workspace_member_repository.get_role(task.workspace_id, requesting_user.id)
            is_workspace_admin = role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN)

        if not (is_uploader or is_workspace_admin):
            raise ForbiddenError("Você não tem permissão para remover este anexo.")

        storage_path = attachment.storage_path
        self.attachment_repository.delete(attachment)
        self.db.commit()

        try:
            file_storage.delete_file(storage_path)
        except OSError:
            logger.error(
                "Falha ao remover arquivo físico de anexo excluído: "
                "task_id=%s attachment_id=%s storage_path=%s",
                task_id,
                attachment_id,
                storage_path,
            )
