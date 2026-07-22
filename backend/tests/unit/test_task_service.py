"""T039 [US1] — testes unitários das invariantes de tarefa pessoal em
`TaskService`, isolados do banco via um repository em memória (Fake)."""

import uuid

import pytest

from app.core.exceptions import BusinessRuleViolationError, ForbiddenError
from app.enums.task_status import TaskStatus
from app.enums.workspace_role import WorkspaceRole
from app.models.project import Project
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.task_service import TaskService


class _FakeSession:
    def commit(self) -> None:
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

    def list_personal_by_creator(self, creator_id: uuid.UUID) -> list[Task]:
        return [
            task
            for task in self.tasks.values()
            if task.creator_id == creator_id and task.workspace_id is None
        ]

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


@pytest.fixture()
def project_repo() -> FakeProjectRepository:
    return FakeProjectRepository()


@pytest.fixture()
def member_repo() -> FakeWorkspaceMemberRepository:
    return FakeWorkspaceMemberRepository()


@pytest.fixture()
def task_service(
    project_repo: FakeProjectRepository, member_repo: FakeWorkspaceMemberRepository
) -> TaskService:
    return TaskService(FakeTaskRepository(), project_repo, member_repo)


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

    updated = task_service.update(task, TaskUpdate(status=TaskStatus.DONE))

    assert updated.status == TaskStatus.DONE
    assert updated.completed_at is not None


def test_update_reopen_clears_completed_at(task_service: TaskService) -> None:
    creator_id = uuid.uuid4()
    task = task_service.create(TaskCreate(title="Tarefa"), creator_id=creator_id)
    task_service.update(task, TaskUpdate(status=TaskStatus.DONE))

    updated = task_service.update(task, TaskUpdate(status=TaskStatus.PENDING))

    assert updated.status == TaskStatus.PENDING
    assert updated.completed_at is None


def test_update_rejects_reassigning_personal_task(task_service: TaskService) -> None:
    creator_id = uuid.uuid4()
    other_id = uuid.uuid4()
    task = task_service.create(TaskCreate(title="Tarefa"), creator_id=creator_id)

    with pytest.raises(BusinessRuleViolationError):
        task_service.update(task, TaskUpdate(assignee_id=other_id))


def test_update_rejects_workspace_conversion(task_service: TaskService) -> None:
    creator_id = uuid.uuid4()
    task = task_service.create(TaskCreate(title="Tarefa"), creator_id=creator_id)

    with pytest.raises(BusinessRuleViolationError):
        task_service.update(task, TaskUpdate(workspace_id=uuid.uuid4()))
