"""Fase 16 (hardening) — atomicidade real de `TaskService.update`: a
mudança do campo + a(s) `Notification` `TASK_CHANGED` + a(s)
`TaskHistoryEntry` ocorrem todas na mesma transação (`try/except: rollback`
desde o Bloco 4 da Fase 13). Usa banco de verdade (não Fakes) porque "nada
foi persistido após rollback" só é verificável de forma convincente contra
uma transação real — mesmo padrão de SAVEPOINT de
`test_comment_service_atomicity.py` (Fase 8)."""

from app.enums.task_status import TaskStatus
from app.enums.workspace_role import WorkspaceRole
from app.models.notification import Notification
from app.models.task import Task
from app.models.task_history_entry import TaskHistoryEntry
from app.repositories.attachment_repository import AttachmentRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.project_member_repository import ProjectMemberRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_history_repository import TaskHistoryRepository
from app.repositories.task_member_repository import TaskMemberRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.task import TaskUpdate
from app.services.task_service import TaskService


def _build_service(db_session) -> TaskService:
    return TaskService(
        TaskRepository(db_session),
        ProjectRepository(db_session),
        WorkspaceMemberRepository(db_session),
        TaskMemberRepository(db_session),
        NotificationRepository(db_session),
        TaskHistoryRepository(db_session),
        AttachmentRepository(db_session),
        ProjectMemberRepository(db_session),
    )


def test_update_rolls_back_status_notification_and_history_on_failure(
    db_session, make_user, make_workspace, add_workspace_member, make_task, monkeypatch
):
    owner = make_user()
    participant = make_user(email="participant-task-atomicity@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace, status=TaskStatus.PENDING)
    from app.models.task_member import TaskMember

    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()
    task_id = task.id  # capturado ANTES do update() — o rollback interno do
    # Service (self.db.rollback(), de sessão inteira) desanexa objetos só
    # flushados/não commitados desta sessão (mesmo padrão de
    # test_comment_service_atomicity.py) — acessar atributos do objeto ORM
    # original DEPOIS do rollback pode levantar DetachedInstanceError.

    service = _build_service(db_session)

    def _failing_create(self: NotificationRepository, notification: Notification) -> Notification:
        raise RuntimeError("Falha simulada ao criar notificação TASK_CHANGED")

    monkeypatch.setattr(NotificationRepository, "create", _failing_create)

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
            service.update(task, TaskUpdate(status=TaskStatus.DONE), changed_by=owner.id)
    except RuntimeError:
        raised = True

    assert raised, "esperava a RuntimeError simulada propagando de update()"
    assert commit_calls["n"] == 0, "commit() NÃO deve ser chamado no caminho de falha"
    assert rollback_calls["n"] == 1, "rollback() MUST ser chamado exatamente uma vez"

    # Nota: `self.db.rollback()` do Service é um rollback de SESSÃO (não
    # escopado à SAVEPOINT do teste, mesma observação documentada em
    # test_comment_service_atomicity.py), então desfaz TUDO que ainda não
    # foi commitado nesta sessão, incluindo o próprio INSERT da `task`
    # (só flushado no setup, nunca commitado) — por isso não há um "estado
    # anterior da task" para reconferir aqui; o que importa é que nenhuma
    # escrita da transação com falha (notificação/histórico) sobreviveu.
    notifications = db_session.query(Notification).filter(Notification.task_id == task_id).all()
    history_entries = (
        db_session.query(TaskHistoryEntry).filter(TaskHistoryEntry.task_id == task_id).all()
    )
    assert notifications == [], "nenhuma notificação deveria ter sobrevivido ao rollback"
    assert history_entries == [], "nenhuma entrada de histórico deveria ter sobrevivido ao rollback"

    # Sessão continua reutilizável após a falha (mesmo padrão de
    # test_comment_service_atomicity.py) — uma escrita nova, sem relação
    # com a que falhou, precisa funcionar normalmente.
    monkeypatch.setattr(db_session, "commit", original_commit)
    monkeypatch.setattr(db_session, "rollback", original_rollback)

    new_owner = make_user(email="new-owner-task-atomicity@example.com")
    new_workspace = make_workspace(owner=new_owner, name="Workspace pós-rollback")
    new_task = make_task(creator=new_owner, workspace=new_workspace, status=TaskStatus.PENDING)

    updated = service.update(new_task, TaskUpdate(status=TaskStatus.DONE), changed_by=new_owner.id)

    assert updated.status == TaskStatus.DONE
    new_history_entries = (
        db_session.query(TaskHistoryEntry).filter(TaskHistoryEntry.task_id == new_task.id).all()
    )
    assert len(new_history_entries) == 1


def test_update_success_persists_status_notification_and_history_together(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    """Contraprova: sem falha simulada, tudo é persistido corretamente na
    mesma transação — confirma que o SAVEPOINT do teste anterior não
    mascara um bug onde nada nunca persiste."""
    owner = make_user()
    participant = make_user(email="participant-task-atomicity-success@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=participant, role=WorkspaceRole.MEMBER)
    task = make_task(creator=owner, workspace=workspace, status=TaskStatus.PENDING)
    from app.models.task_member import TaskMember

    db_session.add(TaskMember(task_id=task.id, user_id=participant.id))
    db_session.flush()

    service = _build_service(db_session)

    service.update(task, TaskUpdate(status=TaskStatus.DONE), changed_by=owner.id)

    reloaded_task = db_session.get(Task, task.id)
    assert reloaded_task.status == TaskStatus.DONE
    assert reloaded_task.completed_at is not None

    notifications = db_session.query(Notification).filter(Notification.task_id == task.id).all()
    history_entries = (
        db_session.query(TaskHistoryEntry).filter(TaskHistoryEntry.task_id == task.id).all()
    )
    assert len(notifications) == 1
    assert notifications[0].recipient_id == participant.id
    assert len(history_entries) == 1
    assert history_entries[0].field_changed == "status"
