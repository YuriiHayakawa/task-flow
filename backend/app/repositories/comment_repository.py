import uuid

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.user import User


class CommentRepository:
    """Acesso a dados de `Comment` — nenhuma regra de negócio aqui
    (Constitution III). Autorização (visibilidade/participação),
    notificação e commit são responsabilidade do `CommentService`."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, comment: Comment) -> Comment:
        self.db.add(comment)
        self.db.flush()
        return comment

    def list_by_task(self, task_id: uuid.UUID) -> list[Row]:
        """Junta com `User` para trazer `name`/`email` do autor em uma única
        consulta (evita N+1); campos já saem rotulados como `author_name`/
        `author_email`, os nomes expostos por `CommentRead`. Ordena por
        `created_at` asc + `id` asc (desempate determinístico quando dois
        comentários têm o mesmo timestamp)."""
        stmt = (
            select(
                Comment.id,
                Comment.author_id,
                User.name.label("author_name"),
                User.email.label("author_email"),
                Comment.content,
                Comment.created_at,
            )
            .join(User, User.id == Comment.author_id)
            .where(Comment.task_id == task_id)
            .order_by(Comment.created_at.asc(), Comment.id.asc())
        )
        return list(self.db.execute(stmt).all())
