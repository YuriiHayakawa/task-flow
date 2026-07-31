"""T090 [US8] — validação isolada de `TaskRepository.search`, antes de
Routes existirem: busca, filtros combináveis, ordenação (incl. prioridade
semântica), paginação real, visibilidade.

Cobre: FR-055 a FR-059, contracts/projects-and-tasks.md (`GET /tasks`)."""

from datetime import date, timedelta

from app.enums.task_priority import TaskPriority
from app.enums.task_sort_by import TaskSortBy
from app.enums.task_sort_order import TaskSortOrder
from app.enums.task_status import TaskStatus
from app.enums.workspace_role import WorkspaceRole
from app.repositories.task_repository import TaskRepository


def _search(repo, user, workspace_ids=(), **kwargs):
    defaults = dict(
        search=None,
        status=None,
        priority=None,
        workspace_id=None,
        project_id=None,
        assignee_id=None,
        sort_by=TaskSortBy.CREATED_AT,
        sort_order=TaskSortOrder.DESC,
        page=1,
        page_size=20,
    )
    defaults.update(kwargs)
    return repo.search(creator_id=user.id, workspace_ids=list(workspace_ids), **defaults)


# --- busca por título ----------------------------------------------------------


def test_search_by_title_ilike(db_session, make_user, make_task):
    user = make_user()
    make_task(creator=user, title="Organizar reunião")
    make_task(creator=user, title="Comprar material")
    repo = TaskRepository(db_session)

    items, total = _search(repo, user, search="reuni")

    assert total == 1
    assert items[0].title == "Organizar reunião"


def test_search_by_title_case_insensitive(db_session, make_user, make_task):
    user = make_user()
    make_task(creator=user, title="Organizar Reunião")
    repo = TaskRepository(db_session)

    items, total = _search(repo, user, search="REUNIÃO")

    assert total == 1


def test_search_no_match_returns_empty_without_error(db_session, make_user, make_task):
    user = make_user()
    make_task(creator=user, title="Qualquer coisa")
    repo = TaskRepository(db_session)

    items, total = _search(repo, user, search="termo-inexistente")

    assert items == []
    assert total == 0


# --- filtros combináveis --------------------------------------------------------


def test_filter_by_status(db_session, make_user, make_task):
    user = make_user()
    make_task(creator=user, title="A", status=TaskStatus.PENDING)
    make_task(creator=user, title="B", status=TaskStatus.DONE)
    repo = TaskRepository(db_session)

    items, total = _search(repo, user, status=TaskStatus.PENDING)

    assert total == 1
    assert items[0].title == "A"


def test_filter_by_priority(db_session, make_user, make_task):
    user = make_user()
    make_task(creator=user, title="Urgente", priority=TaskPriority.URGENT)
    make_task(creator=user, title="Baixa", priority=TaskPriority.LOW)
    repo = TaskRepository(db_session)

    items, total = _search(repo, user, priority=TaskPriority.URGENT)

    assert total == 1
    assert items[0].title == "Urgente"


def test_filter_by_workspace_and_project(
    db_session, make_user, make_workspace, make_project, make_task
):
    user = make_user()
    workspace = make_workspace(owner=user)
    project = make_project(workspace=workspace)
    make_task(creator=user, title="No projeto", workspace=workspace, project=project)
    make_task(creator=user, title="Direto no workspace", workspace=workspace)
    repo = TaskRepository(db_session)

    items, total = _search(
        repo, user, workspace_ids=[workspace.id], workspace_id=workspace.id, project_id=project.id
    )

    assert total == 1
    assert items[0].title == "No projeto"


def test_filter_by_assignee(db_session, make_user, make_workspace, add_workspace_member, make_task):
    owner = make_user()
    member = make_user(email="member-search@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    make_task(creator=owner, assignee=member, title="Do membro", workspace=workspace)
    make_task(creator=owner, assignee=owner, title="Do owner", workspace=workspace)
    repo = TaskRepository(db_session)

    items, total = _search(repo, owner, workspace_ids=[workspace.id], assignee_id=member.id)

    assert total == 1
    assert items[0].title == "Do membro"


def test_filters_combined_simultaneously(db_session, make_user, make_task):
    user = make_user()
    make_task(creator=user, title="Reunião urgente", status=TaskStatus.PENDING, priority=TaskPriority.URGENT)
    make_task(creator=user, title="Reunião comum", status=TaskStatus.PENDING, priority=TaskPriority.LOW)
    make_task(creator=user, title="Outra urgente", status=TaskStatus.DONE, priority=TaskPriority.URGENT)
    repo = TaskRepository(db_session)

    items, total = _search(
        repo, user, search="reuni", status=TaskStatus.PENDING, priority=TaskPriority.URGENT
    )

    assert total == 1
    assert items[0].title == "Reunião urgente"


# --- ordenação -------------------------------------------------------------------


def test_sort_by_due_date_ascending(db_session, make_user, make_task):
    user = make_user()
    today = date.today()
    make_task(creator=user, title="Depois", due_date=today + timedelta(days=5))
    make_task(creator=user, title="Antes", due_date=today + timedelta(days=1))
    repo = TaskRepository(db_session)

    items, _ = _search(repo, user, sort_by=TaskSortBy.DUE_DATE, sort_order=TaskSortOrder.ASC)

    assert [t.title for t in items] == ["Antes", "Depois"]


def test_sort_by_priority_semantic_not_alphabetic(db_session, make_user, make_task):
    """LOW < MEDIUM < HIGH < URGENT — nunca alfabético
    (HIGH, LOW, MEDIUM, URGENT seria o resultado errado)."""
    user = make_user()
    make_task(creator=user, title="Baixa", priority=TaskPriority.LOW)
    make_task(creator=user, title="Urgente", priority=TaskPriority.URGENT)
    make_task(creator=user, title="Alta", priority=TaskPriority.HIGH)
    make_task(creator=user, title="Média", priority=TaskPriority.MEDIUM)
    repo = TaskRepository(db_session)

    items, _ = _search(repo, user, sort_by=TaskSortBy.PRIORITY, sort_order=TaskSortOrder.ASC)

    assert [t.title for t in items] == ["Baixa", "Média", "Alta", "Urgente"]


def test_sort_by_priority_descending(db_session, make_user, make_task):
    user = make_user()
    make_task(creator=user, title="Baixa", priority=TaskPriority.LOW)
    make_task(creator=user, title="Urgente", priority=TaskPriority.URGENT)
    repo = TaskRepository(db_session)

    items, _ = _search(repo, user, sort_by=TaskSortBy.PRIORITY, sort_order=TaskSortOrder.DESC)

    assert [t.title for t in items] == ["Urgente", "Baixa"]


def test_sort_by_created_at_default_descending(db_session, make_user, make_task):
    user = make_user()
    task_1 = make_task(creator=user, title="Primeira")
    task_2 = make_task(creator=user, title="Segunda")
    task_1.created_at = task_1.created_at - timedelta(minutes=5)
    db_session.flush()
    repo = TaskRepository(db_session)

    items, _ = _search(repo, user)

    assert [t.title for t in items] == ["Segunda", "Primeira"]


def test_sort_deterministic_tiebreak_by_id_when_values_equal(db_session, make_user, make_task):
    user = make_user()
    tasks = [make_task(creator=user, title=f"T{i}") for i in range(3)]
    db_session.flush()
    tied_timestamp = tasks[0].created_at
    for task in tasks:
        task.created_at = tied_timestamp
    db_session.flush()
    repo = TaskRepository(db_session)

    items, _ = _search(repo, user)

    expected_order = sorted(tasks, key=lambda t: t.id)
    assert [t.id for t in items] == [t.id for t in expected_order]


# --- paginação -------------------------------------------------------------------


def test_pagination_page_size_and_total(db_session, make_user, make_task):
    user = make_user()
    for i in range(5):
        make_task(creator=user, title=f"Tarefa {i}")
    repo = TaskRepository(db_session)

    items_page_1, total = _search(repo, user, page=1, page_size=2)
    items_page_2, _ = _search(repo, user, page=2, page_size=2)
    items_page_3, _ = _search(repo, user, page=3, page_size=2)

    assert total == 5
    assert len(items_page_1) == 2
    assert len(items_page_2) == 2
    assert len(items_page_3) == 1
    # sem sobreposição entre páginas
    ids_1 = {t.id for t in items_page_1}
    ids_2 = {t.id for t in items_page_2}
    ids_3 = {t.id for t in items_page_3}
    assert ids_1.isdisjoint(ids_2)
    assert ids_1.isdisjoint(ids_3)
    assert ids_2.isdisjoint(ids_3)


# --- visibilidade (FR-059) -------------------------------------------------------


def test_never_returns_other_users_personal_tasks(db_session, make_user, make_task):
    user = make_user()
    other = make_user(email="other-search@example.com")
    make_task(creator=other, title="Tarefa alheia")
    repo = TaskRepository(db_session)

    items, total = _search(repo, user)

    assert total == 0


def test_includes_workspace_tasks_user_is_member_of(
    db_session, make_user, make_workspace, add_workspace_member, make_task
):
    owner = make_user()
    member = make_user(email="member-visibility@example.com")
    workspace = make_workspace(owner=owner)
    add_workspace_member(workspace=workspace, user=member, role=WorkspaceRole.MEMBER)
    make_task(creator=owner, title="Tarefa do workspace", workspace=workspace)
    repo = TaskRepository(db_session)

    items, total = _search(repo, member, workspace_ids=[workspace.id])

    assert total == 1
    assert items[0].title == "Tarefa do workspace"


def test_excludes_workspace_tasks_user_is_not_member_of(
    db_session, make_user, make_workspace, make_task
):
    owner = make_user()
    outsider = make_user(email="outsider-search@example.com")
    workspace = make_workspace(owner=owner)
    make_task(creator=owner, title="Tarefa alheia de workspace", workspace=workspace)
    repo = TaskRepository(db_session)

    # outsider não está em nenhum workspace -> workspace_ids vazio
    items, total = _search(repo, outsider, workspace_ids=[])

    assert total == 0


def test_filtering_by_workspace_not_a_member_of_returns_empty_not_error(
    db_session, make_user, make_workspace, make_task
):
    """FR-059: filtrar por um workspace do qual não se é membro nunca vaza
    dados — o filtro só existe dentro do escopo já visível."""
    owner = make_user()
    outsider = make_user(email="outsider-filter@example.com")
    workspace = make_workspace(owner=owner)
    make_task(creator=owner, title="Tarefa alheia", workspace=workspace)
    repo = TaskRepository(db_session)

    items, total = _search(repo, outsider, workspace_ids=[], workspace_id=workspace.id)

    assert total == 0
    assert items == []
