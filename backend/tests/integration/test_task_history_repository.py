"""T109 [US12] — validação isolada de `TaskHistoryRepository`, antes de
Service/Routes existirem: persistência crua, sem regra de negócio
(Constitution III). Segue o mesmo padrão de `test_comment_repository.py`
(JOIN com `User`, campos achatados)."""

import uuid
from datetime import datetime, timedelta, timezone

from app.models.task_history_entry import TaskHistoryEntry
from app.repositories.task_history_repository import TaskHistoryRepository


def _make_entry(task_id: uuid.UUID, changed_by_id: uuid.UUID, **overrides) -> TaskHistoryEntry:
    defaults = {
        "task_id": task_id,
        "changed_by_id": changed_by_id,
        "field_changed": "status",
        "old_value": "PENDING",
        "new_value": "DONE",
    }
    defaults.update(overrides)
    return TaskHistoryEntry(**defaults)


def test_create_persists_via_flush_not_commit(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = TaskHistoryRepository(db_session)

    entry = repo.create(_make_entry(task.id, owner.id))

    assert entry.id is not None
    assert entry.changed_at is not None
    rows = repo.list_by_task(task.id)
    assert len(rows) == 1


def test_list_by_task_returns_flattened_author_fields(db_session, make_user, make_workspace, make_task):
    author = make_user(name="Autor Historico", email="autor-historico@example.com")
    workspace = make_workspace(owner=author)
    task = make_task(creator=author, workspace=workspace)
    repo = TaskHistoryRepository(db_session)
    repo.create(_make_entry(task.id, author.id, field_changed="priority", old_value="LOW", new_value="HIGH"))

    rows = repo.list_by_task(task.id)

    assert len(rows) == 1
    row = rows[0]
    assert row.changed_by_id == author.id
    assert row.changed_by_name == "Autor Historico"
    assert row.changed_by_email == "autor-historico@example.com"
    assert row.field_changed == "priority"
    assert row.old_value == "LOW"
    assert row.new_value == "HIGH"
    assert row.changed_at is not None


def test_list_by_task_ordered_by_changed_at_descending(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = TaskHistoryRepository(db_session)

    now = datetime.now(timezone.utc)
    e1 = _make_entry(task.id, owner.id, field_changed="status")
    e2 = _make_entry(task.id, owner.id, field_changed="priority")
    e3 = _make_entry(task.id, owner.id, field_changed="due_date")
    db_session.add_all([e2, e3, e1])  # ordem de insercao embaralhada de proposito
    db_session.flush()
    e1.changed_at = now - timedelta(minutes=2)
    e2.changed_at = now - timedelta(minutes=1)
    e3.changed_at = now
    db_session.flush()

    rows = repo.list_by_task(task.id)

    assert [row.field_changed for row in rows] == ["due_date", "priority", "status"]


def test_list_by_task_deterministic_tiebreak_by_id_when_timestamps_equal(
    db_session, make_user, make_workspace, make_task
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = TaskHistoryRepository(db_session)

    same_time_entries = [
        _make_entry(task.id, owner.id, field_changed=f"campo_{i}") for i in range(3)
    ]
    db_session.add_all(same_time_entries)
    db_session.flush()
    tied_timestamp = same_time_entries[0].changed_at
    for entry in same_time_entries:
        entry.changed_at = tied_timestamp
    db_session.flush()

    rows = repo.list_by_task(task.id)

    expected_order = sorted(same_time_entries, key=lambda e: e.id)
    assert [row.id for row in rows] == [e.id for e in expected_order]


def test_list_by_task_isolated_between_tasks(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task_1 = make_task(creator=owner, workspace=workspace, title="Tarefa 1")
    task_2 = make_task(creator=owner, workspace=workspace, title="Tarefa 2")
    repo = TaskHistoryRepository(db_session)
    repo.create(_make_entry(task_1.id, owner.id, field_changed="status"))
    repo.create(_make_entry(task_2.id, owner.id, field_changed="priority"))

    rows_task_1 = repo.list_by_task(task_1.id)

    assert len(rows_task_1) == 1
    assert rows_task_1[0].field_changed == "status"


def test_list_by_task_empty_when_no_entries(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = TaskHistoryRepository(db_session)

    assert repo.list_by_task(task.id) == []


def test_list_by_task_avoids_n_plus_one(db_session, make_user, make_workspace, make_task):
    """Confirma uma única consulta SQL (JOIN) para N entradas, não N+1 —
    mesmo padrão de `test_comment_repository.py`."""
    from sqlalchemy import event

    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = TaskHistoryRepository(db_session)
    for i in range(5):
        repo.create(_make_entry(task.id, owner.id, field_changed=f"campo_{i}"))

    query_count = 0

    def _count_queries(*_args, **_kwargs):
        nonlocal query_count
        query_count += 1

    event.listen(db_session.bind, "before_cursor_execute", _count_queries)
    try:
        rows = repo.list_by_task(task.id)
        assert len(rows) == 5
        assert query_count == 1
    finally:
        event.remove(db_session.bind, "before_cursor_execute", _count_queries)


def test_old_value_and_new_value_accept_none(db_session, make_user, make_workspace, make_task):
    """`due_date` nulo → nulo é uma transição válida (ex.: prazo removido) —
    ambos os campos são nullable (data-model.md)."""
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = TaskHistoryRepository(db_session)
    repo.create(
        _make_entry(task.id, owner.id, field_changed="due_date", old_value="2026-01-01", new_value=None)
    )

    rows = repo.list_by_task(task.id)

    assert rows[0].new_value is None
