"""T075 [US5] — validação isolada de `TaskMemberRepository`, antes de Service/
Routes existirem: persistência crua, sem regra de negócio (Constitution III).

Cobre: data-model.md (`TaskMember`), sem antecipar a matriz de autorização
completa da T074 (isso pertence a `test_task_members.py`, no bloco de
Service/Routes)."""

from sqlalchemy.exc import IntegrityError

from app.models.task_member import TaskMember
from app.repositories.task_member_repository import TaskMemberRepository


def test_create_and_get_by_task_and_user(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = TaskMemberRepository(db_session)

    created = repo.create(TaskMember(task_id=task.id, user_id=owner.id))

    assert created.id is not None
    found = repo.get_by_task_and_user(task.id, owner.id)
    assert found is not None
    assert found.id == created.id


def test_get_by_task_and_user_returns_none_when_absent(db_session, make_user, make_workspace, make_task):
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = TaskMemberRepository(db_session)

    assert repo.get_by_task_and_user(task.id, owner.id) is None


def test_exists_true_and_false(db_session, make_user, make_workspace, add_workspace_member, make_task):
    owner = make_user()
    member = make_user(email="member-exists@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member)
    task = make_task(creator=owner, workspace=workspace)
    repo = TaskMemberRepository(db_session)

    assert repo.exists(task.id, member.id) is False

    repo.create(TaskMember(task_id=task.id, user_id=member.id))

    assert repo.exists(task.id, member.id) is True


def test_list_by_task_scoped_to_correct_task_only(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    owner = make_user()
    member_a = make_user(email="member-a@example.com")
    member_b = make_user(email="member-b@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member_a)
    add_workspace_member(workspace=workspace, user=member_b)
    task_1 = make_task(creator=owner, workspace=workspace, title="Tarefa 1")
    task_2 = make_task(creator=owner, workspace=workspace, title="Tarefa 2")
    repo = TaskMemberRepository(db_session)

    repo.create(TaskMember(task_id=task_1.id, user_id=member_a.id))
    repo.create(TaskMember(task_id=task_2.id, user_id=member_b.id))

    rows_task_1 = repo.list_by_task(task_1.id)

    assert len(rows_task_1) == 1
    assert rows_task_1[0].user_id == member_a.id
    assert rows_task_1[0].name == member_a.name
    assert rows_task_1[0].email == member_a.email
    assert rows_task_1[0].added_at is not None


def test_list_by_task_empty_when_no_explicit_members(db_session, make_user, make_workspace, make_task):
    """Repository nunca fabrica uma linha para o assignee implícito — lista
    vazia é o resultado correto quando não há `TaskMember` explícito, mesmo
    que a tarefa tenha um responsável (isso é composto pelo Service)."""
    owner = make_user()
    workspace = make_workspace(owner=owner)
    task = make_task(creator=owner, workspace=workspace)
    repo = TaskMemberRepository(db_session)

    assert repo.list_by_task(task.id) == []


def test_delete_removes_member(db_session, make_user, make_workspace, add_workspace_member, make_task):
    owner = make_user()
    member = make_user(email="member-delete@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member)
    task = make_task(creator=owner, workspace=workspace)
    repo = TaskMemberRepository(db_session)
    created = repo.create(TaskMember(task_id=task.id, user_id=member.id))

    repo.delete(created)

    assert repo.get_by_task_and_user(task.id, member.id) is None


def test_duplicate_task_member_violates_unique_constraint(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    """UNIQUE(task_id, user_id) — última linha de defesa do banco; a
    prevenção "normal" via `exists()` é responsabilidade do Service (Bloco
    2), não deste teste."""
    owner = make_user()
    member = make_user(email="member-duplicate@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member)
    task = make_task(creator=owner, workspace=workspace)
    repo = TaskMemberRepository(db_session)
    repo.create(TaskMember(task_id=task.id, user_id=member.id))

    raised = False
    try:
        with db_session.begin_nested():
            repo.create(TaskMember(task_id=task.id, user_id=member.id))
    except IntegrityError:
        raised = True

    assert raised, "esperava IntegrityError da constraint UNIQUE(task_id, user_id)"
