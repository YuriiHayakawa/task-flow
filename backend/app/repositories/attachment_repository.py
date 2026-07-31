import uuid

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.models.task import Task
from app.models.user import User


class AttachmentRepository:
    """Acesso a dados de `Attachment` — nenhuma regra de negócio aqui
    (Constitution III). Autorização, validação de tipo/tamanho e o fluxo de
    exclusão controlada (banco primeiro, disco depois) são responsabilidade
    do `AttachmentService`."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, attachment: Attachment) -> Attachment:
        self.db.add(attachment)
        self.db.flush()
        return attachment

    def list_by_task(self, task_id: uuid.UUID) -> list[Row]:
        """Junta com `User` para trazer `name`/`email` de quem enviou em uma
        única consulta (evita N+1) — mesmo padrão de `CommentRepository`.
        Ordenado por `created_at` asc + `id` asc (desempate determinístico;
        sem paginação — volume esperado baixo por tarefa,
        contracts/collaboration.md)."""
        stmt = (
            select(
                Attachment.id,
                Attachment.original_filename,
                Attachment.content_type,
                Attachment.size_bytes,
                Attachment.uploaded_by_id,
                User.name.label("uploaded_by_name"),
                User.email.label("uploaded_by_email"),
                Attachment.created_at,
            )
            .join(User, User.id == Attachment.uploaded_by_id)
            .where(Attachment.task_id == task_id)
            .order_by(Attachment.created_at.asc(), Attachment.id.asc())
        )
        return list(self.db.execute(stmt).all())

    def get_by_task_and_id(
        self, task_id: uuid.UUID, attachment_id: uuid.UUID
    ) -> Attachment | None:
        """Escopado por `task_id` E `attachment_id` juntos — nunca só
        `attachment_id` (mesmo padrão de `ChecklistItemRepository`), para que
        um `task_id` autorizado não permita acessar/remover um anexo que
        pertence a outra tarefa."""
        stmt = select(Attachment).where(
            Attachment.task_id == task_id, Attachment.id == attachment_id
        )
        return self.db.scalars(stmt).first()

    def delete(self, attachment: Attachment) -> None:
        self.db.delete(attachment)
        self.db.flush()

    def list_storage_paths_by_task(self, task_id: uuid.UUID) -> list[str]:
        """Fase 16 (hardening) — usado por `TaskService.delete` para coletar
        os caminhos físicos de todos os anexos da tarefa **antes** do
        cascade de banco remover os registros (research.md #12, passo 1:
        "localizar todos os anexos físicos afetados antes de qualquer
        alteração no banco"). Só os caminhos — a limpeza física não precisa
        do restante do modelo."""
        stmt = select(Attachment.storage_path).where(Attachment.task_id == task_id)
        return list(self.db.scalars(stmt))

    def list_storage_paths_by_workspace(self, workspace_id: uuid.UUID) -> list[str]:
        """Idem, para `WorkspaceService.delete` — `Attachment` não tem
        `workspace_id` diretamente, por isso o JOIN com `Task`."""
        stmt = (
            select(Attachment.storage_path)
            .join(Task, Task.id == Attachment.task_id)
            .where(Task.workspace_id == workspace_id)
        )
        return list(self.db.scalars(stmt))
