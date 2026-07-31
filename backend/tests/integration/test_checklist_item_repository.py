"""T093 [US9] — validação isolada de `ChecklistItemRepository`, antes de
Service/Routes existirem: persistência crua, sem regra de negócio
(Constitution III)."""

from app.models.checklist_item import ChecklistItem
from app.repositories.checklist_item_repository import ChecklistItemRepository


def test_create_persists_via_flush_not_commit(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = ChecklistItemRepository(db_session)

    item = repo.create(ChecklistItem(task_id=task.id, description="Passo 1"))

    assert item.id is not None
    assert item.is_done is False
    assert item.completed_at is None
    items = repo.list_by_task(task.id)
    assert len(items) == 1


def test_list_by_task_ordered(db_session, make_user, make_workspace, make_task):
    from datetime import timedelta

    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = ChecklistItemRepository(db_session)
    item_1 = repo.create(ChecklistItem(task_id=task.id, description="Primeiro"))
    item_2 = repo.create(ChecklistItem(task_id=task.id, description="Segundo"))
    item_1.created_at = item_1.created_at - timedelta(minutes=5)
    db_session.flush()

    items = repo.list_by_task(task.id)

    assert [i.description for i in items] == ["Primeiro", "Segundo"]


def test_list_by_task_isolated_between_tasks(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task_1 = make_task(creator=owner, workspace=workspace, title="Tarefa 1")
    task_2 = make_task(creator=owner, workspace=workspace, title="Tarefa 2")
    repo = ChecklistItemRepository(db_session)
    repo.create(ChecklistItem(task_id=task_1.id, description="Do task 1"))
    repo.create(ChecklistItem(task_id=task_2.id, description="Do task 2"))

    items_task_1 = repo.list_by_task(task_1.id)

    assert len(items_task_1) == 1
    assert items_task_1[0].description == "Do task 1"


def test_list_by_task_empty_when_no_items(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = ChecklistItemRepository(db_session)

    assert repo.list_by_task(task.id) == []


def test_get_by_task_and_id_found(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = ChecklistItemRepository(db_session)
    item = repo.create(ChecklistItem(task_id=task.id, description="Item"))

    found = repo.get_by_task_and_id(task.id, item.id)

    assert found is not None
    assert found.id == item.id


def test_get_by_task_and_id_returns_none_for_item_of_another_task(
    db_session, make_user, make_workspace, make_task
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task_1 = make_task(creator=owner, workspace=workspace, title="Tarefa 1")
    task_2 = make_task(creator=owner, workspace=workspace, title="Tarefa 2")
    repo = ChecklistItemRepository(db_session)
    item = repo.create(ChecklistItem(task_id=task_1.id, description="Item da tarefa 1"))

    found = repo.get_by_task_and_id(task_2.id, item.id)

    assert found is None


def test_get_by_task_and_id_returns_none_when_nonexistent(db_session, make_user, make_workspace, make_task):
    import uuid

    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = ChecklistItemRepository(db_session)

    assert repo.get_by_task_and_id(task.id, uuid.uuid4()) is None


def test_update_flushes_not_commits(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = ChecklistItemRepository(db_session)
    item = repo.create(ChecklistItem(task_id=task.id, description="Item"))

    item.is_done = True
    updated = repo.update(item)

    assert updated.is_done is True
    reloaded = repo.get_by_task_and_id(task.id, item.id)
    assert reloaded is not None
    assert reloaded.is_done is True


def test_delete_removes_item(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = ChecklistItemRepository(db_session)
    item = repo.create(ChecklistItem(task_id=task.id, description="Item"))

    repo.delete(item)

    assert repo.get_by_task_and_id(task.id, item.id) is None
