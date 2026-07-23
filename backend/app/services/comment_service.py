import uuid

from app.core.exceptions import NotFoundError
from app.enums.notification_type import NotificationType
from app.models.comment import Comment
from app.models.notification import Notification
from app.models.task import Task
from app.repositories.comment_repository import CommentRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.task_member_repository import TaskMemberRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.comment import CommentCreate, CommentRead


class CommentService:
    """FR-027 a FR-029, FR-039 (US6). Segue o mesmo padrão de
    `TaskMemberService` (Fase 7): os métodos recebem `task_id` (não um
    `Task` pré-carregado pela rota) e resolvem tudo que precisam via
    repository — quem autoriza o chamador é a dependency da rota
    (`require_task_visible`/`require_task_participant`, Bloco 3), quem
    valida/computa regras de domínio sobre a tarefa/comentário/destinatários
    é este Service."""

    def __init__(
        self,
        comment_repository: CommentRepository,
        notification_repository: NotificationRepository,
        task_repository: TaskRepository,
        task_member_repository: TaskMemberRepository,
        user_repository: UserRepository,
    ) -> None:
        self.comment_repository = comment_repository
        self.notification_repository = notification_repository
        self.task_repository = task_repository
        self.task_member_repository = task_member_repository
        self.user_repository = user_repository
        self.db = comment_repository.db

    def _get_task_or_404(self, task_id: uuid.UUID) -> Task:
        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise NotFoundError("Tarefa não encontrada.")
        return task

    def list_comments(self, task_id: uuid.UUID) -> list[CommentRead]:
        """Autorização de leitura (`require_task_visible`) já ocorreu na
        rota — aqui só confirma que a tarefa existe (defesa em profundidade,
        mesmo padrão de `TaskMemberService`) e lista os comentários."""
        self._get_task_or_404(task_id)
        rows = self.comment_repository.list_by_task(task_id)
        return [CommentRead.model_validate(row, from_attributes=True) for row in rows]

    def create_comment(
        self, task_id: uuid.UUID, author_id: uuid.UUID, data: CommentCreate
    ) -> CommentRead:
        """research.md #19: comentário + notificações `NEW_COMMENT` na
        MESMA transação, um único `commit()`. O fluxo de persistência é
        explicitamente envolto em `try/except Exception: rollback(); raise`
        — qualquer falha (na criação do comentário, no cálculo de
        destinatários, na criação de uma notificação, ou no próprio
        `commit()`) reverte tudo e repropaga a exceção original, sem
        convertê-la (a tradução para erro de domínio, quando aplicável, é
        responsabilidade de quem chama, não deste método). O `rollback()`
        explícito também garante que a sessão continue utilizável para
        novas consultas depois da falha, em vez de ficar num estado de
        transação pendente."""
        task = self._get_task_or_404(task_id)
        author = self.user_repository.get_by_id(author_id)
        assert author is not None  # autenticado — garantido pela dependency da rota

        try:
            comment = Comment(task_id=task_id, author_id=author_id, content=data.content)
            self.comment_repository.create(comment)

            recipient_ids = self._resolve_notification_recipients(task, author_id)
            for recipient_id in recipient_ids:
                notification = Notification(
                    recipient_id=recipient_id,
                    task_id=task.id,
                    type=NotificationType.NEW_COMMENT,
                    title="Novo comentário",
                    message=f'{author.name} comentou na tarefa "{task.title}".',
                )
                self.notification_repository.create(notification)

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(comment)
        return CommentRead(
            id=comment.id,
            author_id=author.id,
            author_name=author.name,
            author_email=author.email,
            content=comment.content,
            created_at=comment.created_at,
        )

    def _resolve_notification_recipients(
        self, task: Task, author_id: uuid.UUID
    ) -> set[uuid.UUID]:
        """dashboard-and-notifications.md: destinatários de `NEW_COMMENT` são
        "participantes da tarefa (responsável + TaskMember, exceto o autor)".
        Nunca inclui o criador ou Owner/Admin apenas por essas posições
        (research.md #8) — só entram se também forem o responsável ou um
        `TaskMember` explícito. Um `set` deduplica naturalmente o caso de o
        responsável também ter uma linha explícita (dados legados).

        Tarefa pessoal: `workspace_id IS NULL`, o único participante possível
        é o criador (= responsável), que também é sempre o autor do
        comentário (única pessoa que enxerga/comenta uma tarefa pessoal) —
        o `set` resultante é vazio após excluir o autor, sem precisar de um
        `if` separado para esse caso (o próprio cálculo já produz o
        resultado correto)."""
        if task.workspace_id is None:
            return set()

        explicit_participant_ids = {
            row.user_id for row in self.task_member_repository.list_by_task(task.id)
        }
        return ({task.assignee_id} | explicit_participant_ids) - {author_id}
