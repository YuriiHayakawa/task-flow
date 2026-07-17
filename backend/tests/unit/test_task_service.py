"""T039 [US1] — testes unitários das invariantes de tarefa pessoal em
`TaskService`, isolados do banco via um repository em memória (Fake)."""

import uuid

import pytest

from app.core.exceptions import BusinessRuleViolationError
from app.enums.task_status import TaskStatus
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


@pytest.fixture()
def task_service() -> TaskService:
    return TaskService(FakeTaskRepository())


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


def test_create_rejects_project_without_workspace(task_service: TaskService) -> None:
    with pytest.raises(BusinessRuleViolationError):
        task_service.create(
            TaskCreate(title="Tarefa", project_id=uuid.uuid4()), creator_id=uuid.uuid4()
        )


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
