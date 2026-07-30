"""T083 [US6] — testes unitários de `CommentService`: destinatários de
`NEW_COMMENT`, dedup, tarefa pessoal, transação única. Isolado do banco via
repositories em memória (Fake), no mesmo padrão de
`tests/unit/test_task_member_service.py`."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from app.core.exceptions import NotFoundError
from app.enums.notification_type import NotificationType
from app.models.comment import Comment
from app.models.notification import Notification
from app.models.task import Task
from app.models.user import User
from app.schemas.comment import CommentCreate
from app.services.comment_service import CommentService


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rollback_called = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rollback_called = True

    def refresh(self, _obj: object) -> None:
        pass


@dataclass
class _FakeCommentRow:
    id: uuid.UUID
    author_id: uuid.UUID
    author_name: str
    author_email: str
    content: str
    created_at: datetime


@dataclass
class _FakeTaskMemberRow:
    user_id: uuid.UUID


class FakeTaskRepository:
    def __init__(self) -> None:
        self.db = _FakeSession()
        self.tasks: dict[uuid.UUID, Task] = {}

    def seed(
        self,
        *,
        creator_id: uuid.UUID,
        assignee_id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        title: str = "Tarefa",
    ) -> Task:
        task = Task(
            id=uuid.uuid4(),
            title=title,
            creator_id=creator_id,
            assignee_id=assignee_id or creator_id,
            workspace_id=workspace_id,
        )
        self.tasks[task.id] = task
        return task

    def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        return self.tasks.get(task_id)


class FakeTaskMemberRepository:
    def __init__(self) -> None:
        self.members: dict[uuid.UUID, set[uuid.UUID]] = {}

    def seed(self, task_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.members.setdefault(task_id, set()).add(user_id)

    def list_by_task(self, task_id: uuid.UUID) -> list[_FakeTaskMemberRow]:
        return [_FakeTaskMemberRow(user_id=uid) for uid in self.members.get(task_id, set())]


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}

    def seed(self, user_id: uuid.UUID, name: str = "User", email: str = "user@example.com") -> User:
        user = User(
            id=user_id, name=name, email=email, password_hash="x", is_active=True, is_system_admin=False
        )
        self.users[user_id] = user
        return user

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.users.get(user_id)


class FakeCommentRepository:
    def __init__(self) -> None:
        self.db = _FakeSession()
        self.comments: dict[uuid.UUID, list[Comment]] = {}

    def create(self, comment: Comment) -> Comment:
        comment.id = comment.id or uuid.uuid4()
        comment.created_at = datetime.now(timezone.utc)
        self.comments.setdefault(comment.task_id, []).append(comment)
        return comment

    def list_by_task(self, task_id: uuid.UUID) -> list[_FakeCommentRow]:
        rows = []
        for comment in self.comments.get(task_id, []):
            rows.append(
                _FakeCommentRow(
                    id=comment.id,
                    author_id=comment.author_id,
                    author_name=f"Autor {comment.author_id}",
                    author_email="autor@example.com",
                    content=comment.content,
                    created_at=comment.created_at,
                )
            )
        return rows


class FakeNotificationRepository:
    def __init__(self) -> None:
        self.db = _FakeSession()
        self.notifications: list[Notification] = []
        self.fail_on_call_number: int | None = None
        self._call_count = 0

    def create(self, notification: Notification) -> Notification:
        self._call_count += 1
        if self.fail_on_call_number is not None and self._call_count == self.fail_on_call_number:
            raise RuntimeError("Falha simulada na criação da notificação")
        notification.id = uuid.uuid4()
        notification.created_at = datetime.now(timezone.utc)
        notification.is_read = False
        self.notifications.append(notification)
        return notification


@pytest.fixture()
def task_repo() -> FakeTaskRepository:
    return FakeTaskRepository()


@pytest.fixture()
def task_member_repo() -> FakeTaskMemberRepository:
    return FakeTaskMemberRepository()


@pytest.fixture()
def user_repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture()
def comment_repo() -> FakeCommentRepository:
    return FakeCommentRepository()


@pytest.fixture()
def notification_repo() -> FakeNotificationRepository:
    return FakeNotificationRepository()


@pytest.fixture()
def service(
    comment_repo: FakeCommentRepository,
    notification_repo: FakeNotificationRepository,
    task_repo: FakeTaskRepository,
    task_member_repo: FakeTaskMemberRepository,
    user_repo: FakeUserRepository,
) -> CommentService:
    return CommentService(comment_repo, notification_repo, task_repo, task_member_repo, user_repo)


# --- list_comments ------------------------------------------------------------


def test_list_comments_empty(service, task_repo, user_repo) -> None:
    creator_id = uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id)
    user_repo.seed(creator_id)

    assert service.list_comments(task.id) == []


def test_list_comments_multiple_preserves_order_and_flattened_fields(
    service, task_repo, comment_repo, user_repo
) -> None:
    creator_id = uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=uuid.uuid4())
    user_repo.seed(creator_id)
    comment_repo.create(Comment(task_id=task.id, author_id=creator_id, content="Primeiro"))
    comment_repo.create(Comment(task_id=task.id, author_id=creator_id, content="Segundo"))

    result = service.list_comments(task.id)

    assert [c.content for c in result] == ["Primeiro", "Segundo"]
    assert result[0].author_id == creator_id
    assert result[0].author_name is not None
    assert result[0].author_email is not None


def test_list_comments_does_not_commit_or_notify(
    service, task_repo, comment_repo, notification_repo, user_repo
) -> None:
    creator_id = uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id)
    user_repo.seed(creator_id)
    comment_repo.create(Comment(task_id=task.id, author_id=creator_id, content="X"))

    service.list_comments(task.id)

    assert comment_repo.db.committed is False
    assert notification_repo.notifications == []


def test_list_comments_nonexistent_task_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.list_comments(uuid.uuid4())


# --- create_comment: básico ---------------------------------------------------


def test_create_comment_valid(service, task_repo, user_repo) -> None:
    creator_id = uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id)
    user_repo.seed(creator_id, name="Criador", email="criador@example.com")

    result = service.create_comment(task.id, creator_id, CommentCreate(content="Olá pessoal"))

    assert result.content == "Olá pessoal"
    assert result.author_id == creator_id
    assert result.author_name == "Criador"
    assert result.created_at is not None


def test_create_comment_personal_task_zero_notifications(
    service, task_repo, notification_repo, user_repo
) -> None:
    creator_id = uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=None)
    user_repo.seed(creator_id)

    service.create_comment(task.id, creator_id, CommentCreate(content="Comentário pessoal"))

    assert notification_repo.notifications == []


def test_create_comment_nonexistent_task_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.create_comment(uuid.uuid4(), uuid.uuid4(), CommentCreate(content="X"))


# --- create_comment: destinatários de NEW_COMMENT -----------------------------


def test_create_comment_assignee_receives_notification(
    service, task_repo, notification_repo, user_repo
) -> None:
    workspace_id = uuid.uuid4()
    creator_id, assignee_id, author_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id)
    user_repo.seed(author_id, name="Autor")

    service.create_comment(task.id, author_id, CommentCreate(content="Comentário"))

    recipients = {n.recipient_id for n in notification_repo.notifications}
    assert recipients == {assignee_id}


def test_create_comment_assignee_author_receives_nothing(
    service, task_repo, notification_repo, user_repo
) -> None:
    workspace_id = uuid.uuid4()
    creator_id, assignee_id = uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id)
    user_repo.seed(assignee_id, name="Responsável")

    service.create_comment(task.id, assignee_id, CommentCreate(content="Comentando na própria"))

    assert notification_repo.notifications == []


def test_create_comment_explicit_task_member_receives_notification(
    service, task_repo, task_member_repo, notification_repo, user_repo
) -> None:
    workspace_id = uuid.uuid4()
    creator_id, assignee_id, participant_id, author_id = (
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4(),
    )
    task = task_repo.seed(creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id)
    task_member_repo.seed(task.id, participant_id)
    user_repo.seed(author_id, name="Autor")

    service.create_comment(task.id, author_id, CommentCreate(content="Comentário"))

    recipients = {n.recipient_id for n in notification_repo.notifications}
    assert recipients == {assignee_id, participant_id}


def test_create_comment_multiple_participants_one_notification_each(
    service, task_repo, task_member_repo, notification_repo, user_repo
) -> None:
    workspace_id = uuid.uuid4()
    creator_id, assignee_id, p1, p2, author_id = (
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4(),
    )
    task = task_repo.seed(creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id)
    task_member_repo.seed(task.id, p1)
    task_member_repo.seed(task.id, p2)
    user_repo.seed(author_id)

    service.create_comment(task.id, author_id, CommentCreate(content="Comentário"))

    recipient_ids = [n.recipient_id for n in notification_repo.notifications]
    assert sorted(recipient_ids) == sorted([assignee_id, p1, p2])
    assert len(recipient_ids) == len(set(recipient_ids))  # exatamente uma por recipient


def test_create_comment_dedupes_assignee_also_explicit_member(
    service, task_repo, task_member_repo, notification_repo, user_repo
) -> None:
    """Dados legados: o responsável também tem uma linha explícita de
    TaskMember — deve receber exatamente UMA notificação, não duas."""
    workspace_id = uuid.uuid4()
    creator_id, assignee_id, author_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id)
    task_member_repo.seed(task.id, assignee_id)  # mesmo user_id do assignee
    user_repo.seed(author_id)

    service.create_comment(task.id, author_id, CommentCreate(content="Comentário"))

    recipient_ids = [n.recipient_id for n in notification_repo.notifications]
    assert recipient_ids == [assignee_id]


def test_create_comment_author_excluded_via_explicit_membership(
    service, task_repo, task_member_repo, notification_repo, user_repo
) -> None:
    workspace_id = uuid.uuid4()
    creator_id, assignee_id, author_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id)
    task_member_repo.seed(task.id, author_id)  # autor também é participante explícito
    user_repo.seed(author_id)

    service.create_comment(task.id, author_id, CommentCreate(content="Comentário"))

    recipients = {n.recipient_id for n in notification_repo.notifications}
    assert author_id not in recipients
    assert recipients == {assignee_id}


def test_create_comment_owner_admin_not_participant_receives_nothing(
    service, task_repo, task_member_repo, notification_repo, user_repo
) -> None:
    """research.md #8: Owner/Admin não são participantes automáticos — não
    aparecem como destinatários salvo se também forem assignee/TaskMember.
    O `owner_id` aqui simplesmente NUNCA é adicionado como assignee nem como
    TaskMember, simulando um Owner sem participação."""
    workspace_id = uuid.uuid4()
    creator_id, assignee_id, owner_id, author_id = (
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4(),
    )
    task = task_repo.seed(creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id)
    user_repo.seed(author_id)

    service.create_comment(task.id, author_id, CommentCreate(content="Comentário"))

    recipients = {n.recipient_id for n in notification_repo.notifications}
    assert owner_id not in recipients
    assert recipients == {assignee_id}


def test_create_comment_removed_participant_receives_nothing(
    service, task_repo, task_member_repo, notification_repo, user_repo
) -> None:
    """Um participante que já foi removido (nunca chega a ser 'seedado' no
    fake, simulando remoção prévia) não recebe notificação — o cálculo lê o
    estado ATUAL de `task_member_repository.list_by_task`."""
    workspace_id = uuid.uuid4()
    creator_id, assignee_id, removed_id, author_id = (
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4(),
    )
    task = task_repo.seed(creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id)
    # removed_id nunca é adicionado ao task_member_repo — simula já ter sido removido
    user_repo.seed(author_id)

    service.create_comment(task.id, author_id, CommentCreate(content="Comentário"))

    recipients = {n.recipient_id for n in notification_repo.notifications}
    assert removed_id not in recipients


def test_create_comment_notification_type_and_fields(
    service, task_repo, notification_repo, user_repo
) -> None:
    workspace_id = uuid.uuid4()
    creator_id, assignee_id, author_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(
        creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id, title="Tarefa X"
    )
    user_repo.seed(author_id, name="Fulano")

    service.create_comment(task.id, author_id, CommentCreate(content="Comentário"))

    notification = notification_repo.notifications[0]
    assert notification.type == NotificationType.NEW_COMMENT
    assert notification.recipient_id == assignee_id
    assert notification.task_id == task.id
    assert notification.title == "Novo comentário"
    assert notification.message == 'Fulano comentou na tarefa "Tarefa X".'
    assert notification.is_read is False


def test_create_comment_single_commit(
    service, comment_repo, task_repo, notification_repo, user_repo
) -> None:
    workspace_id = uuid.uuid4()
    creator_id, assignee_id, author_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id)
    user_repo.seed(author_id)

    service.create_comment(task.id, author_id, CommentCreate(content="Comentário"))

    # comment_repo e notification_repo compartilham a mesma sessão fake
    # (injetada via CommentService.__init__ -> self.db = comment_repository.db)
    assert comment_repo.db.committed is True
    assert comment_repo.db.rollback_called is False


# --- create_comment: atomicidade (simulação de falha em memória) -------------


def test_create_comment_notification_failure_propagates_exception(
    service, task_repo, task_member_repo, notification_repo, comment_repo, user_repo
) -> None:
    """Confirma o tratamento transacional explícito de `create_comment`:
    `try/except Exception: self.db.rollback(); raise` — uma falha durante a
    criação de QUALQUER notificação propaga a exceção ORIGINAL (nenhuma
    conversão para outro tipo), chama `rollback()` e NUNCA chega a chamar
    `commit()`. Verificação de que nenhuma linha sobrevive de fato (com
    banco real) está em
    `tests/integration/test_comment_service_atomicity.py`."""
    workspace_id = uuid.uuid4()
    creator_id, assignee_id, p1, author_id = (
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4(),
    )
    task = task_repo.seed(creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id)
    task_member_repo.seed(task.id, p1)
    user_repo.seed(author_id)
    notification_repo.fail_on_call_number = 2  # falha na 2a notificação

    with pytest.raises(RuntimeError):
        service.create_comment(task.id, author_id, CommentCreate(content="Vai falhar"))

    assert comment_repo.db.committed is False, "commit() NÃO deve ser chamado no caminho de falha"
    assert comment_repo.db.rollback_called is True, "rollback() MUST ser chamado quando uma notificação falha"
