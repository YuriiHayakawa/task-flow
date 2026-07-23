"""T083 [US6] — atomicidade real (research.md #19): comentário + notificações
`NEW_COMMENT` na mesma transação. Usa banco de verdade (não Fakes) porque
"nada foi persistido após rollback" só é verificável de forma convincente
contra uma transação real — segue o mesmo padrão de SAVEPOINT
(`db_session.begin_nested()`) já usado em `test_workspace_ownership.py`
(Fase 5) para testar uma falha esperada sem perturbar a transação externa da
fixture `db_session`."""

from app.enums.workspace_role import WorkspaceRole
from app.models.comment import Comment
from app.models.notification import Notification
from app.models.task_member import TaskMember
from app.repositories.comment_repository import CommentRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.task_member_repository import TaskMemberRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.comment import CommentCreate
from app.services.comment_service import CommentService


def test_create_comment_rolls_back_everything_on_notification_failure(
    db_session,
    make_user,
    make_workspace,
    add_workspace_member,
    make_task,
    monkeypatch,
):
    owner = make_user()
    assignee = make_user(email="assignee-atomicity@example.com")
    participant = make_user(email="participant-atomicity@example.com")
    author = make_user(email="author-atomicity@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=author, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)
    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()
    # 2 destinatários esperados: assignee + participant (author é o próprio
    # autor do comentário, excluído do cálculo de destinatários).

    service = CommentService(
        CommentRepository(db_session),
        NotificationRepository(db_session),
        TaskRepository(db_session),
        TaskMemberRepository(db_session),
        UserRepository(db_session),
    )

    call_count = {"n": 0}
    original_create = NotificationRepository.create

    def _failing_create(self: NotificationRepository, notification: Notification) -> Notification:
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("Falha simulada na segunda notificação")
        return original_create(self, notification)

    monkeypatch.setattr(NotificationRepository, "create", _failing_create)

    # Espiona commit()/rollback() da sessão REAL, sem substituir o
    # comportamento (chama o método original) — confirma 1/2 e 6 do pedido:
    # rollback() chamado, commit() nunca chamado no caminho de falha.
    commit_calls = {"n": 0}
    rollback_calls = {"n": 0}
    original_commit = db_session.commit
    original_rollback = db_session.rollback

    def _tracked_commit() -> None:
        commit_calls["n"] += 1
        original_commit()

    def _tracked_rollback() -> None:
        rollback_calls["n"] += 1
        original_rollback()

    monkeypatch.setattr(db_session, "commit", _tracked_commit)
    monkeypatch.setattr(db_session, "rollback", _tracked_rollback)

    raised = False
    try:
        with db_session.begin_nested():
            service.create_comment(task.id, author.id, CommentCreate(content="Vai falhar"))
    except RuntimeError:
        raised = True

    assert raised, "esperava a RuntimeError simulada propagando de create_comment"
    assert call_count["n"] == 2, "esperava a falha exatamente na 2a notificação"
    assert commit_calls["n"] == 0, "commit() NÃO deve ser chamado no caminho de falha"
    assert rollback_calls["n"] == 1, "rollback() MUST ser chamado exatamente uma vez"

    comments = db_session.query(Comment).filter(Comment.task_id == task.id).all()
    notifications = db_session.query(Notification).filter(Notification.task_id == task.id).all()
    assert comments == [], "nenhum comentário deveria ter sobrevivido ao rollback"
    assert notifications == [], "nenhuma notificação deveria ter sobrevivido ao rollback"

    # Sessão continua reutilizável após a falha: uma escrita totalmente NOVA,
    # sem relação com o que falhou, precisa funcionar normalmente — sem
    # levantar erro de transação pendente/quebrada. Nota: `self.db.rollback()`
    # do Service é um rollback de SESSÃO (não escopado à SAVEPOINT do teste),
    # então ele desfaz TUDO que ainda não foi commitado nesta sessão,
    # incluindo o setup feito acima (owner/assignee/participant/author/
    # workspace/task) — por isso o teste recria tudo do zero aqui, em vez de
    # supor que o setup anterior sobreviveu (não deveria, e não sobrevive).
    monkeypatch.setattr(db_session, "commit", original_commit)
    monkeypatch.setattr(db_session, "rollback", original_rollback)

    new_owner = make_user(email="new-owner-after-rollback@example.com")
    new_assignee = make_user(email="new-assignee-after-rollback@example.com")
    new_author = make_user(email="new-author-after-rollback@example.com")
    new_workspace = make_workspace(owner=new_owner, name="Workspace pós-rollback")
    add_workspace_member(workspace=new_workspace, user=new_assignee, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=new_workspace, user=new_author, role=WorkspaceRole.MEMBER)
    new_task = make_task(creator=new_owner, assignee=new_assignee, workspace=new_workspace)

    result = service.create_comment(
        new_task.id, new_author.id, CommentCreate(content="Sessão continua funcionando")
    )

    assert result.content == "Sessão continua funcionando"
    new_notifications = (
        db_session.query(Notification).filter(Notification.task_id == new_task.id).all()
    )
    assert len(new_notifications) == 1
    assert new_notifications[0].recipient_id == new_assignee.id


def test_create_comment_success_persists_comment_and_all_notifications(
    db_session, make_user, make_workspace, add_workspace_member, make_task, monkeypatch
):
    """Contraprova do teste acima: sem falha simulada, tudo é persistido
    corretamente na mesma transação (confirma que o SAVEPOINT do teste
    anterior não mascara um bug onde nada nunca persiste) — e confirma
    exatamente 1 commit / 0 rollback no caminho de sucesso (ponto 6)."""
    owner = make_user()
    assignee = make_user(email="assignee-success@example.com")
    author = make_user(email="author-success@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=assignee, role=WorkspaceRole.MEMBER)
    add_workspace_member(workspace=workspace, user=author, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, assignee=assignee, workspace=workspace)

    service = CommentService(
        CommentRepository(db_session),
        NotificationRepository(db_session),
        TaskRepository(db_session),
        TaskMemberRepository(db_session),
        UserRepository(db_session),
    )

    commit_calls = {"n": 0}
    rollback_calls = {"n": 0}
    original_commit = db_session.commit
    original_rollback = db_session.rollback

    def _tracked_commit() -> None:
        commit_calls["n"] += 1
        original_commit()

    def _tracked_rollback() -> None:
        rollback_calls["n"] += 1
        original_rollback()

    monkeypatch.setattr(db_session, "commit", _tracked_commit)
    monkeypatch.setattr(db_session, "rollback", _tracked_rollback)

    service.create_comment(task.id, author.id, CommentCreate(content="Comentário de sucesso"))

    assert commit_calls["n"] == 1, "caminho de sucesso deve executar exatamente um commit"
    assert rollback_calls["n"] == 0

    comments = db_session.query(Comment).filter(Comment.task_id == task.id).all()
    notifications = db_session.query(Notification).filter(Notification.task_id == task.id).all()
    assert len(comments) == 1
    assert len(notifications) == 1
    assert notifications[0].recipient_id == assignee.id
