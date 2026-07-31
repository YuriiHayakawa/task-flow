"""T097 [US10] — validação isolada de `AttachmentRepository`, antes de
Service/Routes existirem: persistência crua, sem regra de negócio
(Constitution III). Segue o mesmo padrão de `test_comment_repository.py`
(JOIN com `User`, campos achatados) e `test_checklist_item_repository.py`
(`get_by_task_and_id` escopado por tarefa)."""

import uuid
from datetime import datetime, timedelta, timezone

from app.models.attachment import Attachment
from app.repositories.attachment_repository import AttachmentRepository


def _make_attachment(task_id: uuid.UUID, uploaded_by_id: uuid.UUID, **overrides) -> Attachment:
    defaults = {
        "task_id": task_id,
        "uploaded_by_id": uploaded_by_id,
        "original_filename": "documento.pdf",
        "storage_path": f"{uuid.uuid4()}.pdf",
        "content_type": "application/pdf",
        "size_bytes": 1024,
    }
    defaults.update(overrides)
    return Attachment(**defaults)


def test_create_persists_via_flush_not_commit(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = AttachmentRepository(db_session)

    attachment = repo.create(_make_attachment(task.id, owner.id))

    assert attachment.id is not None
    assert attachment.created_at is not None
    rows = repo.list_by_task(task.id)
    assert len(rows) == 1


def test_list_by_task_returns_flattened_uploader_fields(
    db_session, make_user, make_workspace, make_task
):
    uploader = make_user(name="Ana Uploader", email="ana-uploader@example.com")
    workspace = make_workspace(owner=uploader)
    task = make_task(creator=uploader, workspace=workspace)
    repo = AttachmentRepository(db_session)
    repo.create(_make_attachment(task.id, uploader.id, original_filename="relatorio.pdf"))

    rows = repo.list_by_task(task.id)

    assert len(rows) == 1
    row = rows[0]
    assert row.uploaded_by_id == uploader.id
    assert row.uploaded_by_name == "Ana Uploader"
    assert row.uploaded_by_email == "ana-uploader@example.com"
    assert row.original_filename == "relatorio.pdf"
    assert row.content_type == "application/pdf"
    assert row.size_bytes == 1024
    assert row.created_at is not None


def test_list_by_task_ordered_by_created_at_ascending(
    db_session, make_user, make_workspace, make_task
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = AttachmentRepository(db_session)

    now = datetime.now(timezone.utc)
    a1 = _make_attachment(task.id, owner.id, original_filename="primeiro.pdf")
    a2 = _make_attachment(task.id, owner.id, original_filename="segundo.pdf")
    a3 = _make_attachment(task.id, owner.id, original_filename="terceiro.pdf")
    db_session.add_all([a3, a1, a2])  # ordem de insercao embaralhada de proposito
    db_session.flush()
    a1.created_at = now - timedelta(minutes=2)
    a2.created_at = now - timedelta(minutes=1)
    a3.created_at = now
    db_session.flush()

    rows = repo.list_by_task(task.id)

    assert [row.original_filename for row in rows] == ["primeiro.pdf", "segundo.pdf", "terceiro.pdf"]


def test_list_by_task_deterministic_tiebreak_by_id_when_timestamps_equal(
    db_session, make_user, make_workspace, make_task
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = AttachmentRepository(db_session)

    same_time_attachments = [
        _make_attachment(task.id, owner.id, original_filename=f"anexo-{i}.pdf") for i in range(3)
    ]
    db_session.add_all(same_time_attachments)
    db_session.flush()
    tied_timestamp = same_time_attachments[0].created_at
    for attachment in same_time_attachments:
        attachment.created_at = tied_timestamp
    db_session.flush()

    rows = repo.list_by_task(task.id)

    expected_order = sorted(same_time_attachments, key=lambda a: a.id)
    assert [row.id for row in rows] == [a.id for a in expected_order]


def test_list_by_task_isolated_between_tasks(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task_1 = make_task(creator=owner, workspace=workspace, title="Tarefa 1")
    task_2 = make_task(creator=owner, workspace=workspace, title="Tarefa 2")
    repo = AttachmentRepository(db_session)
    repo.create(_make_attachment(task_1.id, owner.id, original_filename="do-task-1.pdf"))
    repo.create(_make_attachment(task_2.id, owner.id, original_filename="do-task-2.pdf"))

    rows_task_1 = repo.list_by_task(task_1.id)

    assert len(rows_task_1) == 1
    assert rows_task_1[0].original_filename == "do-task-1.pdf"


def test_list_by_task_empty_when_no_attachments(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = AttachmentRepository(db_session)

    assert repo.list_by_task(task.id) == []


def test_list_by_task_avoids_n_plus_one(db_session, make_user, make_workspace, make_task):
    """Confirma uma única consulta SQL (JOIN) para N anexos, não N+1 — conta
    as queries emitidas via evento do SQLAlchemy (mesmo padrão de
    `test_comment_repository.py`)."""
    from sqlalchemy import event

    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = AttachmentRepository(db_session)
    for i in range(5):
        repo.create(_make_attachment(task.id, owner.id, original_filename=f"anexo-{i}.pdf"))

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


def test_get_by_task_and_id_found(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = AttachmentRepository(db_session)
    attachment = repo.create(_make_attachment(task.id, owner.id))

    found = repo.get_by_task_and_id(task.id, attachment.id)

    assert found is not None
    assert found.id == attachment.id


def test_get_by_task_and_id_returns_none_for_attachment_of_another_task(
    db_session, make_user, make_workspace, make_task
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task_1 = make_task(creator=owner, workspace=workspace, title="Tarefa 1")
    task_2 = make_task(creator=owner, workspace=workspace, title="Tarefa 2")
    repo = AttachmentRepository(db_session)
    attachment = repo.create(_make_attachment(task_1.id, owner.id))

    found = repo.get_by_task_and_id(task_2.id, attachment.id)

    assert found is None


def test_get_by_task_and_id_returns_none_when_nonexistent(
    db_session, make_user, make_workspace, make_task
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = AttachmentRepository(db_session)

    assert repo.get_by_task_and_id(task.id, uuid.uuid4()) is None


def test_delete_removes_attachment(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = AttachmentRepository(db_session)
    attachment = repo.create(_make_attachment(task.id, owner.id))

    repo.delete(attachment)

    assert repo.get_by_task_and_id(task.id, attachment.id) is None
