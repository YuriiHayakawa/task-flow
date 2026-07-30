"""T076 [US5] — testes unitários de `TaskMemberService`: responsável como
participante implícito, invariantes de tarefa pessoal, duplicidade,
concorrência. Isolado do banco via repositories em memória (Fake), no mesmo
padrão de `tests/unit/test_workspace_member_service.py`."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BusinessRuleViolationError, ConflictError, NotFoundError
from app.enums.workspace_role import WorkspaceRole
from app.models.task import Task
from app.models.task_member import TaskMember
from app.models.user import User
from app.services.task_member_service import TaskMemberService


class _FakeSession:
    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def refresh(self, _obj: object) -> None:
        pass


@dataclass
class _FakeMemberRow:
    user_id: uuid.UUID
    name: str
    email: str
    added_at: datetime


class FakeTaskRepository:
    def __init__(self) -> None:
        self.db = _FakeSession()
        self.tasks: dict[uuid.UUID, Task] = {}

    def seed(
        self,
        *,
        creator_id: uuid.UUID,
        assignee_id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
    ) -> Task:
        task = Task(
            id=uuid.uuid4(),
            title="Tarefa",
            creator_id=creator_id,
            assignee_id=assignee_id or creator_id,
            workspace_id=workspace_id,
        )
        self.tasks[task.id] = task
        return task

    def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        return self.tasks.get(task_id)


class FakeWorkspaceMemberRepository:
    def __init__(self) -> None:
        self.roles: dict[tuple[uuid.UUID, uuid.UUID], WorkspaceRole] = {}

    def seed(self, workspace_id: uuid.UUID, user_id: uuid.UUID, role: WorkspaceRole) -> None:
        self.roles[(workspace_id, user_id)] = role

    def get_role(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> WorkspaceRole | None:
        return self.roles.get((workspace_id, user_id))


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}

    def seed(self, user_id: uuid.UUID, name: str = "User", email: str = "user@example.com") -> User:
        user = User(
            id=user_id, name=name, email=email, password_hash="x", is_active=True, is_system_admin=False
        )
        self.users[user_id] = user
        return user

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.users.get(user_id)


class FakeTaskMemberRepository:
    def __init__(self, user_repository: FakeUserRepository) -> None:
        self.db = _FakeSession()
        self.user_repository = user_repository
        self.members: dict[tuple[uuid.UUID, uuid.UUID], TaskMember] = {}
        self.raise_integrity_error_on_create = False

    def seed(self, task_id: uuid.UUID, user_id: uuid.UUID, added_at: datetime | None = None) -> TaskMember:
        member = TaskMember(id=uuid.uuid4(), task_id=task_id, user_id=user_id)
        member.created_at = added_at or datetime.now(timezone.utc)
        self.members[(task_id, user_id)] = member
        return member

    def create(self, member: TaskMember) -> TaskMember:
        if self.raise_integrity_error_on_create:
            raise IntegrityError("INSERT", {}, Exception("duplicate key value violates unique constraint"))
        member.id = member.id or uuid.uuid4()
        member.created_at = datetime.now(timezone.utc)
        self.members[(member.task_id, member.user_id)] = member
        return member

    def delete(self, member: TaskMember) -> None:
        self.members.pop((member.task_id, member.user_id), None)

    def exists(self, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return (task_id, user_id) in self.members

    def get_by_task_and_user(self, task_id: uuid.UUID, user_id: uuid.UUID) -> TaskMember | None:
        return self.members.get((task_id, user_id))

    def list_by_task(self, task_id: uuid.UUID) -> list[_FakeMemberRow]:
        rows = [
            _FakeMemberRow(
                user_id=user_id,
                name=self.user_repository.get_by_id(user_id).name,
                email=self.user_repository.get_by_id(user_id).email,
                added_at=member.created_at,
            )
            for (t_id, user_id), member in self.members.items()
            if t_id == task_id
        ]
        rows.sort(key=lambda row: row.added_at)
        return rows


@pytest.fixture()
def task_repo() -> FakeTaskRepository:
    return FakeTaskRepository()


@pytest.fixture()
def member_repo() -> FakeWorkspaceMemberRepository:
    return FakeWorkspaceMemberRepository()


@pytest.fixture()
def user_repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture()
def task_member_repo(user_repo: FakeUserRepository) -> FakeTaskMemberRepository:
    return FakeTaskMemberRepository(user_repo)


@pytest.fixture()
def service(
    task_member_repo: FakeTaskMemberRepository,
    task_repo: FakeTaskRepository,
    member_repo: FakeWorkspaceMemberRepository,
    user_repo: FakeUserRepository,
) -> TaskMemberService:
    return TaskMemberService(task_member_repo, task_repo, member_repo, user_repo)


# --- list_members ------------------------------------------------------------


def test_list_members_returns_only_implicit_assignee_when_no_explicit_members(
    service, task_repo, user_repo
) -> None:
    workspace_id, creator_id = uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=workspace_id)
    user_repo.seed(creator_id, name="Creator", email="creator@example.com")

    result = service.list_members(task.id)

    assert len(result) == 1
    assert result[0].user_id == creator_id
    assert result[0].added_at is None


def test_list_members_includes_explicit_members(
    service, task_repo, task_member_repo, user_repo
) -> None:
    workspace_id, creator_id, member_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=workspace_id)
    user_repo.seed(creator_id, name="Creator", email="creator@example.com")
    user_repo.seed(member_id, name="Member", email="member@example.com")
    task_member_repo.seed(task.id, member_id)

    result = service.list_members(task.id)

    user_ids = {member.user_id for member in result}
    assert user_ids == {creator_id, member_id}


def test_list_members_no_duplicate_when_assignee_has_explicit_row(
    service, task_repo, task_member_repo, user_repo
) -> None:
    """Se o responsável também tiver uma linha explícita, ele aparece UMA
    única vez, com o `added_at` REAL da linha — nunca `None`."""
    workspace_id, creator_id = uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=workspace_id)
    user_repo.seed(creator_id, name="Creator", email="creator@example.com")
    real_added_at = datetime.now(timezone.utc) - timedelta(days=3)
    task_member_repo.seed(task.id, creator_id, added_at=real_added_at)

    result = service.list_members(task.id)

    assert len(result) == 1
    assert result[0].user_id == creator_id
    assert result[0].added_at == real_added_at


def test_list_members_added_at_none_only_for_implicit_assignee(
    service, task_repo, task_member_repo, user_repo
) -> None:
    workspace_id, creator_id, member_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=workspace_id)
    user_repo.seed(creator_id)
    user_repo.seed(member_id, name="Member", email="member@example.com")
    task_member_repo.seed(task.id, member_id)

    result = service.list_members(task.id)

    by_id = {member.user_id: member for member in result}
    assert by_id[creator_id].added_at is None
    assert by_id[member_id].added_at is not None


def test_list_members_isolated_by_task(service, task_repo, task_member_repo, user_repo) -> None:
    workspace_id = uuid.uuid4()
    creator_id, member_a, member_b = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task_1 = task_repo.seed(creator_id=creator_id, workspace_id=workspace_id)
    task_2 = task_repo.seed(creator_id=creator_id, workspace_id=workspace_id)
    user_repo.seed(creator_id)
    user_repo.seed(member_a, name="A", email="a@example.com")
    user_repo.seed(member_b, name="B", email="b@example.com")
    task_member_repo.seed(task_1.id, member_a)
    task_member_repo.seed(task_2.id, member_b)

    result_1 = service.list_members(task_1.id)

    user_ids = {member.user_id for member in result_1}
    assert member_b not in user_ids
    assert member_a in user_ids


def test_list_members_personal_task_returns_only_creator(service, task_repo, user_repo) -> None:
    creator_id = uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=None)
    user_repo.seed(creator_id, name="Creator", email="creator@example.com")

    result = service.list_members(task.id)

    assert len(result) == 1
    assert result[0].user_id == creator_id
    assert result[0].added_at is None


def test_list_members_nonexistent_task_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.list_members(uuid.uuid4())


# --- add_member ----------------------------------------------------------


def test_add_member_valid_participant(service, task_repo, member_repo, user_repo) -> None:
    workspace_id, creator_id, candidate_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=workspace_id)
    member_repo.seed(workspace_id, candidate_id, WorkspaceRole.MEMBER)
    user_repo.seed(candidate_id, name="Candidate", email="candidate@example.com")

    result = service.add_member(task.id, candidate_id)

    assert result.user_id == candidate_id
    assert result.added_at is not None


def test_add_member_rejects_personal_task(service, task_repo) -> None:
    creator_id = uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=None)

    with pytest.raises(BusinessRuleViolationError):
        service.add_member(task.id, uuid.uuid4())


def test_add_member_rejects_user_not_member_of_workspace(service, task_repo) -> None:
    """Cobre tanto 'usuário existente mas não membro' quanto 'usuário
    inexistente' — ambos produzem `get_role() is None`, mesmo 400."""
    workspace_id, creator_id = uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=workspace_id)

    with pytest.raises(BusinessRuleViolationError):
        service.add_member(task.id, uuid.uuid4())


def test_add_member_rejects_assignee(service, task_repo, member_repo) -> None:
    workspace_id, creator_id, assignee_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id)
    member_repo.seed(workspace_id, assignee_id, WorkspaceRole.MEMBER)

    with pytest.raises(ConflictError):
        service.add_member(task.id, assignee_id)


def test_add_member_rejects_duplicate_explicit(
    service, task_repo, member_repo, task_member_repo, user_repo
) -> None:
    workspace_id, creator_id, candidate_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=workspace_id)
    member_repo.seed(workspace_id, candidate_id, WorkspaceRole.MEMBER)
    user_repo.seed(candidate_id)
    task_member_repo.seed(task.id, candidate_id)

    with pytest.raises(ConflictError):
        service.add_member(task.id, candidate_id)


def test_add_member_nonexistent_task_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.add_member(uuid.uuid4(), uuid.uuid4())


def test_add_member_no_persistence_before_validations_complete(
    service, task_repo, task_member_repo
) -> None:
    creator_id = uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=None)  # tarefa pessoal -> vai falhar
    candidate_id = uuid.uuid4()

    with pytest.raises(BusinessRuleViolationError):
        service.add_member(task.id, candidate_id)

    assert task_member_repo.exists(task.id, candidate_id) is False


def test_add_member_converts_integrity_error_to_conflict(
    service, task_repo, member_repo, task_member_repo, user_repo
) -> None:
    """Simula uma corrida de concorrência: `exists()` não pegou a
    duplicidade a tempo, mas o UNIQUE(task_id, user_id) do banco pegou no
    `create()`/commit — convertido para o mesmo `ConflictError`, nunca um
    erro genérico."""
    workspace_id, creator_id, candidate_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=workspace_id)
    member_repo.seed(workspace_id, candidate_id, WorkspaceRole.MEMBER)
    user_repo.seed(candidate_id)
    task_member_repo.raise_integrity_error_on_create = True

    with pytest.raises(ConflictError):
        service.add_member(task.id, candidate_id)


# --- remove_member ---------------------------------------------------------


def test_remove_member_success(service, task_repo, task_member_repo) -> None:
    workspace_id, creator_id, member_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=workspace_id)
    task_member_repo.seed(task.id, member_id)

    service.remove_member(task.id, member_id)

    assert task_member_repo.exists(task.id, member_id) is False


def test_remove_member_nonexistent_link_raises_not_found(service, task_repo) -> None:
    workspace_id, creator_id = uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=workspace_id)

    with pytest.raises(NotFoundError):
        service.remove_member(task.id, uuid.uuid4())


def test_remove_member_rejects_assignee(service, task_repo) -> None:
    workspace_id, creator_id, assignee_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id)

    with pytest.raises(BusinessRuleViolationError):
        service.remove_member(task.id, assignee_id)


def test_remove_member_rejects_personal_task(service, task_repo) -> None:
    creator_id = uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=None)

    with pytest.raises(BusinessRuleViolationError):
        service.remove_member(task.id, creator_id)


def test_remove_member_does_not_change_assignee_id(service, task_repo, task_member_repo) -> None:
    workspace_id, creator_id, assignee_id, member_id = (
        uuid.uuid4(),
        uuid.uuid4(),
        uuid.uuid4(),
        uuid.uuid4(),
    )
    task = task_repo.seed(creator_id=creator_id, assignee_id=assignee_id, workspace_id=workspace_id)
    task_member_repo.seed(task.id, member_id)

    service.remove_member(task.id, member_id)

    assert task.assignee_id == assignee_id


def test_remove_member_does_not_delete_task(service, task_repo, task_member_repo) -> None:
    workspace_id, creator_id, member_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    task = task_repo.seed(creator_id=creator_id, workspace_id=workspace_id)
    task_member_repo.seed(task.id, member_id)

    service.remove_member(task.id, member_id)

    assert task_repo.get_by_id(task.id) is not None


def test_remove_member_nonexistent_task_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.remove_member(uuid.uuid4(), uuid.uuid4())
