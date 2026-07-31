"""T094 [US9] — testes unitários de `ChecklistItemService`: transição de
`is_done`/`completed_at`, isolamento entre tarefas. Isolado do banco via
repositories em memória (Fake), no mesmo padrão de
`tests/unit/test_comment_service.py`."""

import uuid
from datetime import datetime, timezone

import pytest

from app.core.exceptions import NotFoundError
from app.models.checklist_item import ChecklistItem
from app.models.task import Task
from app.schemas.checklist_item import ChecklistItemCreate, ChecklistItemUpdate
from app.services.checklist_item_service import ChecklistItemService


class _FakeSession:
    def commit(self) -> None:
        pass

    def refresh(self, _obj: object) -> None:
        pass


class FakeTaskRepository:
    def __init__(self) -> None:
        self.db = _FakeSession()
        self.tasks: dict[uuid.UUID, Task] = {}

    def seed(self, *, creator_id: uuid.UUID) -> Task:
        task = Task(id=uuid.uuid4(), title="Tarefa", creator_id=creator_id, assignee_id=creator_id)
        self.tasks[task.id] = task
        return task

    def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        return self.tasks.get(task_id)


class FakeChecklistItemRepository:
    def __init__(self) -> None:
        self.db = _FakeSession()
        self.items: dict[uuid.UUID, ChecklistItem] = {}

    def seed(self, task_id: uuid.UUID, description: str = "Item", is_done: bool = False) -> ChecklistItem:
        item = ChecklistItem(id=uuid.uuid4(), task_id=task_id, description=description, is_done=is_done)
        item.created_at = datetime.now(timezone.utc)
        self.items[item.id] = item
        return item

    def create(self, item: ChecklistItem) -> ChecklistItem:
        item.id = item.id or uuid.uuid4()
        item.created_at = datetime.now(timezone.utc)
        if item.is_done is None:
            item.is_done = False  # simula o server_default do Model
        self.items[item.id] = item
        return item

    def list_by_task(self, task_id: uuid.UUID) -> list[ChecklistItem]:
        items = [item for item in self.items.values() if item.task_id == task_id]
        return sorted(items, key=lambda i: (i.created_at, i.id))

    def get_by_task_and_id(self, task_id: uuid.UUID, item_id: uuid.UUID) -> ChecklistItem | None:
        item = self.items.get(item_id)
        if item is None or item.task_id != task_id:
            return None
        return item

    def update(self, item: ChecklistItem) -> ChecklistItem:
        return item

    def delete(self, item: ChecklistItem) -> None:
        self.items.pop(item.id, None)


@pytest.fixture()
def task_repo() -> FakeTaskRepository:
    return FakeTaskRepository()


@pytest.fixture()
def checklist_repo() -> FakeChecklistItemRepository:
    return FakeChecklistItemRepository()


@pytest.fixture()
def service(
    checklist_repo: FakeChecklistItemRepository, task_repo: FakeTaskRepository
) -> ChecklistItemService:
    return ChecklistItemService(checklist_repo, task_repo)


# --- list_items ----------------------------------------------------------------


def test_list_items_empty(service, task_repo) -> None:
    task = task_repo.seed(creator_id=uuid.uuid4())

    assert service.list_items(task.id) == []


def test_list_items_multiple_preserves_order(service, task_repo, checklist_repo) -> None:
    task = task_repo.seed(creator_id=uuid.uuid4())
    checklist_repo.seed(task.id, description="Primeiro")
    checklist_repo.seed(task.id, description="Segundo")

    result = service.list_items(task.id)

    assert [item.description for item in result] == ["Primeiro", "Segundo"]


def test_list_items_nonexistent_task_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.list_items(uuid.uuid4())


# --- create_item -----------------------------------------------------------------


def test_create_item_valid(service, task_repo) -> None:
    task = task_repo.seed(creator_id=uuid.uuid4())

    result = service.create_item(task.id, ChecklistItemCreate(description="Novo item"))

    assert result.description == "Novo item"
    assert result.is_done is False
    assert result.completed_at is None


def test_create_item_nonexistent_task_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.create_item(uuid.uuid4(), ChecklistItemCreate(description="X"))


# --- update_item -----------------------------------------------------------------


def test_update_item_marks_done_sets_completed_at(service, task_repo, checklist_repo) -> None:
    task = task_repo.seed(creator_id=uuid.uuid4())
    item = checklist_repo.seed(task.id, is_done=False)

    result = service.update_item(task.id, item.id, ChecklistItemUpdate(is_done=True))

    assert result.is_done is True
    assert result.completed_at is not None


def test_update_item_already_done_does_not_change_completed_at(
    service, task_repo, checklist_repo
) -> None:
    task = task_repo.seed(creator_id=uuid.uuid4())
    item = checklist_repo.seed(task.id, is_done=True)
    original_completed_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    item.completed_at = original_completed_at

    result = service.update_item(task.id, item.id, ChecklistItemUpdate(is_done=True))

    assert result.completed_at == original_completed_at


def test_update_item_marks_pending_clears_completed_at(service, task_repo, checklist_repo) -> None:
    task = task_repo.seed(creator_id=uuid.uuid4())
    item = checklist_repo.seed(task.id, is_done=True)
    item.completed_at = datetime.now(timezone.utc)

    result = service.update_item(task.id, item.id, ChecklistItemUpdate(is_done=False))

    assert result.is_done is False
    assert result.completed_at is None


def test_update_item_nonexistent_item_raises_not_found(service, task_repo) -> None:
    task = task_repo.seed(creator_id=uuid.uuid4())

    with pytest.raises(NotFoundError):
        service.update_item(task.id, uuid.uuid4(), ChecklistItemUpdate(is_done=True))


def test_update_item_from_another_task_raises_not_found(service, task_repo, checklist_repo) -> None:
    task_1 = task_repo.seed(creator_id=uuid.uuid4())
    task_2 = task_repo.seed(creator_id=uuid.uuid4())
    item = checklist_repo.seed(task_1.id)

    with pytest.raises(NotFoundError):
        service.update_item(task_2.id, item.id, ChecklistItemUpdate(is_done=True))


def test_update_item_nonexistent_task_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.update_item(uuid.uuid4(), uuid.uuid4(), ChecklistItemUpdate(is_done=True))


# --- delete_item -----------------------------------------------------------------


def test_delete_item_removes_it(service, task_repo, checklist_repo) -> None:
    task = task_repo.seed(creator_id=uuid.uuid4())
    item = checklist_repo.seed(task.id)

    service.delete_item(task.id, item.id)

    assert checklist_repo.get_by_task_and_id(task.id, item.id) is None


def test_delete_item_nonexistent_raises_not_found(service, task_repo) -> None:
    task = task_repo.seed(creator_id=uuid.uuid4())

    with pytest.raises(NotFoundError):
        service.delete_item(task.id, uuid.uuid4())


def test_delete_item_from_another_task_raises_not_found(service, task_repo, checklist_repo) -> None:
    task_1 = task_repo.seed(creator_id=uuid.uuid4())
    task_2 = task_repo.seed(creator_id=uuid.uuid4())
    item = checklist_repo.seed(task_1.id)

    with pytest.raises(NotFoundError):
        service.delete_item(task_2.id, item.id)

    # o item original continua intacto na tarefa 1
    assert checklist_repo.get_by_task_and_id(task_1.id, item.id) is not None


def test_delete_item_nonexistent_task_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.delete_item(uuid.uuid4(), uuid.uuid4())
