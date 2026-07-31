"""T039 [US1] — testes unitários das invariantes de tarefa pessoal em
`TaskService`, isolados do banco via um repository em memória (Fake).

T106 (US11, Fase 13): estende com testes de reatribuição de responsável em
tarefa de workspace (correção de bug encontrado na abertura da Fase 13) e de
geração de `Notification` tipo `TASK_CHANGED`."""

import uuid
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.core.exceptions import BusinessRuleViolationError, ForbiddenError
from app.enums.notification_type import NotificationType
from app.enums.task_status import TaskStatus
from app.enums.workspace_role import WorkspaceRole
from app.models.notification import Notification
from app.models.project import Project
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.task_service import TaskService


class _FakeSession:
    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def refresh(self, _obj: object) -> None:
        pass


class FakeTaskRepository:
    """Repository em memória — permite testar `TaskService` sem tocar no banco."""

    def __init__(self) -> None:
        self.db = _FakeSession()
        self.tasks: dict[uuid.UUID, Task] = {}

    def create(self, task: Task) -> Task:
        task.id = uuid.uuid4()
        self.tasks[task.id] = task
        return task

    def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        return self.tasks.get(task_id)

    def update(self, task: Task) -> Task:
        return task


class FakeProjectRepository:
    """T072 (US4) — permite testar a derivação de workspace a partir de
    projeto sem tocar no banco."""

    def __init__(self) -> None:
        self.projects: dict[uuid.UUID, Project] = {}

    def seed(self, workspace_id: uuid.UUID) -> Project:
        project = Project(id=uuid.uuid4(), workspace_id=workspace_id, name="Projeto", description=None)
        self.projects[project.id] = project
        return project

    def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        return self.projects.get(project_id)


class FakeWorkspaceMemberRepository:
    """T072 (US4) — permite testar a validação de membership de criador/
    responsável sem tocar no banco."""

    def __init__(self) -> None:
        self.roles: dict[tuple[uuid.UUID, uuid.UUID], WorkspaceRole] = {}

    def seed(self, workspace_id: uuid.UUID, user_id: uuid.UUID, role: WorkspaceRole) -> None:
        self.roles[(workspace_id, user_id)] = role

    def get_role(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> WorkspaceRole | None:
        return self.roles.get((workspace_id, user_id))


class FakeTaskMemberRepository:
    """T106 (US11) — permite testar a resolução de destinatários de
    `TASK_CHANGED` (participantes explícitos) sem tocar no banco."""

    def __init__(self) -> None:
        self.members: dict[uuid.UUID, list[uuid.UUID]] = {}

    def seed(self, task_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.members.setdefault(task_id, []).append(user_id)

    def list_by_task(self, task_id: uuid.UUID) -> list[SimpleNamespace]:
        return [SimpleNamespace(user_id=user_id) for user_id in self.members.get(task_id, [])]


class FakeNotificationRepository:
    """T106 (US11) — captura as `Notification` criadas por `TaskService.update`
    sem tocar no banco."""

    def __init__(self) -> None:
        self.notifications: list[Notification] = []

    def create(self, notification: Notification) -> Notification:
        self.notifications.append(notification)
        return notification


@pytest.fixture()
def project_repo() -> FakeProjectRepository:
    return FakeProjectRepository()


@pytest.fixture()
def member_repo() -> FakeWorkspaceMemberRepository:
    return FakeWorkspaceMemberRepository()


@pytest.fixture()
def task_member_repo() -> FakeTaskMemberRepository:
    return FakeTaskMemberRepository()


@pytest.fixture()
def notification_repo() -> FakeNotificationRepository:
    return FakeNotificationRepository()


@pytest.fixture()
def task_service(
    project_repo: FakeProjectRepository,
    member_repo: FakeWorkspaceMemberRepository,
    task_member_repo: FakeTaskMemberRepository,
    notification_repo: FakeNotificationRepository,
) -> TaskService:
    return TaskService(FakeTaskRepository(), project_repo, member_repo, task_member_repo, notification_repo)


def test_create_personal_task_forces_assignee_to_creator(task_service: TaskService) -> None:
    creator_id = uuid.uuid4()

    task = task_service.create(TaskCreate(title="Tarefa pessoal"), creator_id=creator_id)

    assert task.assignee_id == creator_id
    assert task.creator_id == creator_id
    assert task.workspace_id is None


def test_create_personal_task_rejects_different_assignee(task_service: TaskService) -> None:
    creator_id = uuid.uuid4()
    other_id = uuid.uuid4()

    with pytest.raises(BusinessRuleViolationError):
        task_service.create(
            TaskCreate(title="Tarefa pessoal", assignee_id=other_id), creator_id=creator_id
        )


def test_create_rejects_nonexistent_project(task_service: TaskService) -> None:
    """T072 (US4): antes, `project_id` sem `workspace_id` era rejeitado
    incondicionalmente; agora o workspace é derivado do projeto — um
    `project_id` que não existe vira `403` (mesma postura de segurança usada
    para workspace inexistente, contracts/projects-and-tasks.md)."""
    with pytest.raises(ForbiddenError):
        task_service.create(
            TaskCreate(title="Tarefa", project_id=uuid.uuid4()), creator_id=uuid.uuid4()
        )


def test_create_derives_workspace_from_project(
    task_service: TaskService, project_repo: FakeProjectRepository, member_repo: FakeWorkspaceMemberRepository
) -> None:
    creator_id = uuid.uuid4()
    project = project_repo.seed(workspace_id=uuid.uuid4())
    member_repo.seed(project.workspace_id, creator_id, WorkspaceRole.MEMBER)

    task = task_service.create(
        TaskCreate(title="Tarefa de projeto", project_id=project.id), creator_id=creator_id
    )

    assert task.workspace_id == project.workspace_id
    assert task.project_id == project.id
    assert task.assignee_id == creator_id


def test_create_rejects_creator_not_member_of_workspace(task_service: TaskService) -> None:
    with pytest.raises(ForbiddenError):
        task_service.create(
            TaskCreate(title="Tarefa", workspace_id=uuid.uuid4()), creator_id=uuid.uuid4()
        )


def test_create_rejects_project_workspace_mismatch(
    task_service: TaskService, project_repo: FakeProjectRepository, member_repo: FakeWorkspaceMemberRepository
) -> None:
    creator_id = uuid.uuid4()
    project = project_repo.seed(workspace_id=uuid.uuid4())
    member_repo.seed(project.workspace_id, creator_id, WorkspaceRole.MEMBER)

    with pytest.raises(BusinessRuleViolationError):
        task_service.create(
            TaskCreate(title="Tarefa", project_id=project.id, workspace_id=uuid.uuid4()),
            creator_id=creator_id,
        )


def test_create_rejects_assignee_not_member_of_workspace(
    task_service: TaskService, member_repo: FakeWorkspaceMemberRepository
) -> None:
    creator_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    member_repo.seed(workspace_id, creator_id, WorkspaceRole.MEMBER)

    with pytest.raises(BusinessRuleViolationError):
        task_service.create(
            TaskCreate(title="Tarefa", workspace_id=workspace_id, assignee_id=uuid.uuid4()),
            creator_id=creator_id,
        )


def test_create_accepts_assignee_member_of_workspace(
    task_service: TaskService, member_repo: FakeWorkspaceMemberRepository
) -> None:
    creator_id = uuid.uuid4()
    assignee_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    member_repo.seed(workspace_id, creator_id, WorkspaceRole.MEMBER)
    member_repo.seed(workspace_id, assignee_id, WorkspaceRole.MEMBER)

    task = task_service.create(
        TaskCreate(title="Tarefa", workspace_id=workspace_id, assignee_id=assignee_id),
        creator_id=creator_id,
    )

    assert task.assignee_id == assignee_id


def test_update_status_to_done_sets_completed_at(task_service: TaskService) -> None:
    creator_id = uuid.uuid4()
    task = task_service.create(TaskCreate(title="Tarefa"), creator_id=creator_id)

    updated = task_service.update(task, TaskUpdate(status=TaskStatus.DONE), changed_by=creator_id)

    assert updated.status == TaskStatus.DONE
    assert updated.completed_at is not None


def test_update_reopen_clears_completed_at(task_service: TaskService) -> None:
    creator_id = uuid.uuid4()
    task = task_service.create(TaskCreate(title="Tarefa"), creator_id=creator_id)
    task_service.update(task, TaskUpdate(status=TaskStatus.DONE), changed_by=creator_id)

    updated = task_service.update(task, TaskUpdate(status=TaskStatus.PENDING), changed_by=creator_id)

    assert updated.status == TaskStatus.PENDING
    assert updated.completed_at is None


def test_update_rejects_reassigning_personal_task(task_service: TaskService) -> None:
    creator_id = uuid.uuid4()
    other_id = uuid.uuid4()
    task = task_service.create(TaskCreate(title="Tarefa"), creator_id=creator_id)

    with pytest.raises(BusinessRuleViolationError):
        task_service.update(task, TaskUpdate(assignee_id=other_id), changed_by=creator_id)


def test_update_rejects_workspace_conversion(task_service: TaskService) -> None:
    creator_id = uuid.uuid4()
    task = task_service.create(TaskCreate(title="Tarefa"), creator_id=creator_id)

    with pytest.raises(BusinessRuleViolationError):
        task_service.update(task, TaskUpdate(workspace_id=uuid.uuid4()), changed_by=creator_id)


# --- T106: correção do bug de reatribuição em tarefa de workspace --------------


def test_update_reassigns_workspace_task_to_valid_member(
    task_service: TaskService, member_repo: FakeWorkspaceMemberRepository
) -> None:
    """Antes da correção (Fase 13), esta reatribuição era incorretamente
    rejeitada pela regra de tarefa pessoal, aplicada de forma incondicional."""
    creator_id = uuid.uuid4()
    other_member_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    member_repo.seed(workspace_id, creator_id, WorkspaceRole.OWNER)
    member_repo.seed(workspace_id, other_member_id, WorkspaceRole.MEMBER)
    task = task_service.create(
        TaskCreate(title="Tarefa", workspace_id=workspace_id), creator_id=creator_id
    )

    updated = task_service.update(
        task, TaskUpdate(assignee_id=other_member_id), changed_by=creator_id
    )

    assert updated.assignee_id == other_member_id


def test_update_rejects_reassigning_workspace_task_to_non_member(
    task_service: TaskService, member_repo: FakeWorkspaceMemberRepository
) -> None:
    creator_id = uuid.uuid4()
    non_member_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    member_repo.seed(workspace_id, creator_id, WorkspaceRole.OWNER)
    task = task_service.create(
        TaskCreate(title="Tarefa", workspace_id=workspace_id), creator_id=creator_id
    )

    with pytest.raises(BusinessRuleViolationError):
        task_service.update(task, TaskUpdate(assignee_id=non_member_id), changed_by=creator_id)


# --- T106: notificação TASK_CHANGED --------------------------------------------


def test_update_status_change_notifies_participant_except_changed_by(
    task_service: TaskService,
    member_repo: FakeWorkspaceMemberRepository,
    task_member_repo: FakeTaskMemberRepository,
    notification_repo: FakeNotificationRepository,
) -> None:
    creator_id = uuid.uuid4()
    participant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    member_repo.seed(workspace_id, creator_id, WorkspaceRole.OWNER)
    member_repo.seed(workspace_id, participant_id, WorkspaceRole.MEMBER)
    task = task_service.create(
        TaskCreate(title="Tarefa", workspace_id=workspace_id), creator_id=creator_id
    )
    task_member_repo.seed(task.id, participant_id)

    task_service.update(task, TaskUpdate(status=TaskStatus.IN_PROGRESS), changed_by=creator_id)

    assert len(notification_repo.notifications) == 1
    notification = notification_repo.notifications[0]
    assert notification.recipient_id == participant_id
    assert notification.type == NotificationType.TASK_CHANGED
    assert notification.task_id == task.id


def test_update_does_not_notify_the_author_of_the_change(
    task_service: TaskService, member_repo: FakeWorkspaceMemberRepository, notification_repo
) -> None:
    creator_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    member_repo.seed(workspace_id, creator_id, WorkspaceRole.OWNER)
    task = task_service.create(
        TaskCreate(title="Tarefa", workspace_id=workspace_id), creator_id=creator_id
    )

    task_service.update(task, TaskUpdate(priority="HIGH"), changed_by=creator_id)

    assert notification_repo.notifications == []


def test_update_untracked_field_change_generates_no_notification(
    task_service: TaskService,
    member_repo: FakeWorkspaceMemberRepository,
    task_member_repo: FakeTaskMemberRepository,
    notification_repo: FakeNotificationRepository,
) -> None:
    creator_id = uuid.uuid4()
    participant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    member_repo.seed(workspace_id, creator_id, WorkspaceRole.OWNER)
    member_repo.seed(workspace_id, participant_id, WorkspaceRole.MEMBER)
    task = task_service.create(
        TaskCreate(title="Tarefa", workspace_id=workspace_id), creator_id=creator_id
    )
    task_member_repo.seed(task.id, participant_id)

    task_service.update(task, TaskUpdate(title="Novo título"), changed_by=creator_id)

    assert notification_repo.notifications == []


def test_update_personal_task_change_generates_no_notification(
    task_service: TaskService, notification_repo: FakeNotificationRepository
) -> None:
    creator_id = uuid.uuid4()
    task = task_service.create(TaskCreate(title="Tarefa pessoal"), creator_id=creator_id)

    task_service.update(task, TaskUpdate(status=TaskStatus.DONE), changed_by=creator_id)

    assert notification_repo.notifications == []


def test_update_reassignment_notifies_both_old_and_new_assignee(
    task_service: TaskService,
    member_repo: FakeWorkspaceMemberRepository,
    notification_repo: FakeNotificationRepository,
) -> None:
    creator_id = uuid.uuid4()
    old_assignee_id = uuid.uuid4()
    new_assignee_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    member_repo.seed(workspace_id, creator_id, WorkspaceRole.OWNER)
    member_repo.seed(workspace_id, old_assignee_id, WorkspaceRole.MEMBER)
    member_repo.seed(workspace_id, new_assignee_id, WorkspaceRole.MEMBER)
    task = task_service.create(
        TaskCreate(title="Tarefa", workspace_id=workspace_id, assignee_id=old_assignee_id),
        creator_id=creator_id,
    )

    task_service.update(task, TaskUpdate(assignee_id=new_assignee_id), changed_by=creator_id)

    recipients = {n.recipient_id for n in notification_repo.notifications}
    assert recipients == {old_assignee_id, new_assignee_id}


def test_update_no_change_to_tracked_fields_value_generates_no_notification(
    task_service: TaskService,
    member_repo: FakeWorkspaceMemberRepository,
    task_member_repo: FakeTaskMemberRepository,
    notification_repo: FakeNotificationRepository,
) -> None:
    """Reenviar o mesmo valor já vigente não é uma "mudança" — não gera
    notificação nem reseta `due_soon_notified_for`."""
    creator_id = uuid.uuid4()
    participant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    member_repo.seed(workspace_id, creator_id, WorkspaceRole.OWNER)
    member_repo.seed(workspace_id, participant_id, WorkspaceRole.MEMBER)
    task = task_service.create(
        TaskCreate(title="Tarefa", workspace_id=workspace_id, priority="MEDIUM"),
        creator_id=creator_id,
    )
    task_member_repo.seed(task.id, participant_id)

    task_service.update(task, TaskUpdate(priority="MEDIUM"), changed_by=creator_id)

    assert notification_repo.notifications == []


# --- T106: reset de due_soon_notified_for --------------------------------------


def test_update_due_date_change_resets_due_soon_notified_for(task_service: TaskService) -> None:
    creator_id = uuid.uuid4()
    task = task_service.create(
        TaskCreate(title="Tarefa", due_date=date.today()), creator_id=creator_id
    )
    task.due_soon_notified_for = task.due_date  # simula já notificado

    updated = task_service.update(
        task, TaskUpdate(due_date=date.today() + timedelta(days=5)), changed_by=creator_id
    )

    assert updated.due_soon_notified_for is None


def test_update_due_date_unchanged_does_not_reset_due_soon_notified_for(
    task_service: TaskService,
) -> None:
    creator_id = uuid.uuid4()
    due_date = date.today()
    task = task_service.create(TaskCreate(title="Tarefa", due_date=due_date), creator_id=creator_id)
    task.due_soon_notified_for = due_date

    updated = task_service.update(task, TaskUpdate(due_date=due_date), changed_by=creator_id)

    assert updated.due_soon_notified_for == due_date
