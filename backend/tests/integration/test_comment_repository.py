"""T081 [US6] — validação isolada de `CommentRepository`, antes de Service/
Routes existirem: persistência crua, sem regra de negócio (Constitution III).

Cobre: data-model.md (`Comment`), sem antecipar autorização/notificação
(isso pertence ao `CommentService`, Bloco 2)."""

from app.models.comment import Comment
from app.repositories.comment_repository import CommentRepository


def test_create_persists_via_flush_not_commit(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = CommentRepository(db_session)

    comment = repo.create(Comment(task_id=task.id, author_id=owner.id, content="Olá"))

    assert comment.id is not None
    assert comment.created_at is not None
    # Ainda dentro da mesma transação (flush), visível a uma nova consulta:
    rows = repo.list_by_task(task.id)
    assert len(rows) == 1


def test_list_by_task_returns_flattened_author_fields(
    db_session, make_user, make_workspace, make_task
):
    owner = make_user(name="Dona Owner", email="owner-comment@example.com")
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = CommentRepository(db_session)
    repo.create(Comment(task_id=task.id, author_id=owner.id, content="Primeiro comentário"))

    rows = repo.list_by_task(task.id)

    assert len(rows) == 1
    row = rows[0]
    assert row.author_id == owner.id
    assert row.author_name == "Dona Owner"
    assert row.author_email == "owner-comment@example.com"
    assert row.content == "Primeiro comentário"
    assert row.created_at is not None


def test_list_by_task_ordered_by_created_at_ascending(
    db_session, make_user, make_workspace, make_task
):
    from datetime import datetime, timedelta, timezone

    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = CommentRepository(db_session)

    now = datetime.now(timezone.utc)
    c1 = Comment(task_id=task.id, author_id=owner.id, content="Primeiro")
    c2 = Comment(task_id=task.id, author_id=owner.id, content="Segundo")
    c3 = Comment(task_id=task.id, author_id=owner.id, content="Terceiro")
    db_session.add_all([c3, c1, c2])  # ordem de insercao embaralhada de proposito
    db_session.flush()
    c1.created_at = now - timedelta(minutes=2)
    c2.created_at = now - timedelta(minutes=1)
    c3.created_at = now
    db_session.flush()

    rows = repo.list_by_task(task.id)

    assert [row.content for row in rows] == ["Primeiro", "Segundo", "Terceiro"]


def test_list_by_task_deterministic_tiebreak_by_id_when_timestamps_equal(
    db_session, make_user, make_workspace, make_task
):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = CommentRepository(db_session)

    same_time_comments = [
        Comment(task_id=task.id, author_id=owner.id, content=f"Comentário {i}") for i in range(3)
    ]
    db_session.add_all(same_time_comments)
    db_session.flush()
    tied_timestamp = same_time_comments[0].created_at
    for comment in same_time_comments:
        comment.created_at = tied_timestamp
    db_session.flush()

    rows = repo.list_by_task(task.id)

    expected_order = sorted(same_time_comments, key=lambda c: c.id)
    assert [row.id for row in rows] == [c.id for c in expected_order]


def test_list_by_task_isolated_between_tasks(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task_1 = make_task(creator=owner, workspace=workspace, title="Tarefa 1")
    task_2 = make_task(creator=owner, workspace=workspace, title="Tarefa 2")
    repo = CommentRepository(db_session)
    repo.create(Comment(task_id=task_1.id, author_id=owner.id, content="Do task 1"))
    repo.create(Comment(task_id=task_2.id, author_id=owner.id, content="Do task 2"))

    rows_task_1 = repo.list_by_task(task_1.id)

    assert len(rows_task_1) == 1
    assert rows_task_1[0].content == "Do task 1"


def test_list_by_task_empty_when_no_comments(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = CommentRepository(db_session)

    assert repo.list_by_task(task.id) == []


def test_list_by_task_avoids_n_plus_one(db_session, make_user, make_workspace, make_task):
    """Confirma uma única consulta SQL (JOIN) para N comentários, não N+1 —
    conta as queries emitidas via evento do SQLAlchemy."""
    from sqlalchemy import event

    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = CommentRepository(db_session)
    for i in range(5):
        repo.create(Comment(task_id=task.id, author_id=owner.id, content=f"Comentário {i}"))

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
