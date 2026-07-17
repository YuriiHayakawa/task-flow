"""T056 [US3] — testes unitários de `WorkspaceMemberService`: só o Owner
promove/rebaixa/remove Admin; ninguém altera ou remove o Owner por outra via.
Isolado do banco via repositories em memória (Fake), no mesmo padrão de
`tests/unit/test_task_service.py`."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from app.core.exceptions import (
    BusinessRuleViolationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.enums.workspace_role import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.services.workspace_member_service import WorkspaceMemberService


class _FakeSession:
    def commit(self) -> None:
        pass

    def refresh(self, _obj: object) -> None:
        pass


class FakeWorkspaceMemberRepository:
    def __init__(self) -> None:
        self.db = _FakeSession()
        self.members: dict[tuple[uuid.UUID, uuid.UUID], WorkspaceMember] = {}

    def seed(self, workspace_id: uuid.UUID, user_id: uuid.UUID, role: WorkspaceRole) -> WorkspaceMember:
        member = WorkspaceMember(id=uuid.uuid4(), workspace_id=workspace_id, user_id=user_id, role=role)
        member.created_at = datetime.now(timezone.utc)
        self.members[(workspace_id, user_id)] = member
        return member

    def create(self, member: WorkspaceMember) -> WorkspaceMember:
        member.id = member.id or uuid.uuid4()
        member.created_at = datetime.now(timezone.utc)
        self.members[(member.workspace_id, member.user_id)] = member
        return member

    def get_role(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> WorkspaceRole | None:
        member = self.members.get((workspace_id, user_id))
        return member.role if member else None

    def get_owner_for_update(self, workspace_id: uuid.UUID) -> WorkspaceMember | None:
        for member in self.members.values():
            if member.workspace_id == workspace_id and member.role == WorkspaceRole.OWNER:
                return member
        return None

    def get_member_for_update(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        return self.members.get((workspace_id, user_id))

    def list_by_workspace(self, workspace_id: uuid.UUID) -> list[WorkspaceMember]:
        return [m for m in self.members.values() if m.workspace_id == workspace_id]

    def update(self, member: WorkspaceMember) -> WorkspaceMember:
        return member

    def delete(self, member: WorkspaceMember) -> None:
        self.members.pop((member.workspace_id, member.user_id), None)


class FakeWorkspaceRepository:
    def __init__(self) -> None:
        self.db = _FakeSession()
        self.workspaces: dict[uuid.UUID, Workspace] = {}

    def seed(self, workspace_id: uuid.UUID, name: str = "Workspace") -> Workspace:
        now = datetime.now(timezone.utc)
        workspace = Workspace(id=workspace_id, name=name, description=None)
        workspace.created_at = now
        workspace.updated_at = now
        self.workspaces[workspace_id] = workspace
        return workspace

    def get_by_id(self, workspace_id: uuid.UUID) -> Workspace | None:
        return self.workspaces.get(workspace_id)


class FakeUserRepository:
    def __init__(self) -> None:
        self.db = _FakeSession()
        self.users: dict[uuid.UUID, User] = {}

    def seed(self, user_id: uuid.UUID, email: str = "user@example.com") -> User:
        user = User(
            id=user_id,
            name="Fake User",
            email=email,
            password_hash="x",
            is_active=True,
            is_system_admin=False,
        )
        self.users[user_id] = user
        return user

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.users.get(user_id)


@dataclass
class _FakeActiveTask:
    id: uuid.UUID
    title: str


class FakeTaskRepository:
    def __init__(self) -> None:
        self.db = _FakeSession()
        self.active_tasks: list = []

    def list_active_by_assignee_in_workspace(self, _workspace_id: uuid.UUID, _assignee_id: uuid.UUID):
        return self.active_tasks


@pytest.fixture()
def member_repo() -> FakeWorkspaceMemberRepository:
    return FakeWorkspaceMemberRepository()


@pytest.fixture()
def workspace_repo() -> FakeWorkspaceRepository:
    return FakeWorkspaceRepository()


@pytest.fixture()
def user_repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture()
def task_repo() -> FakeTaskRepository:
    return FakeTaskRepository()


@pytest.fixture()
def service(
    member_repo: FakeWorkspaceMemberRepository,
    workspace_repo: FakeWorkspaceRepository,
    user_repo: FakeUserRepository,
    task_repo: FakeTaskRepository,
) -> WorkspaceMemberService:
    return WorkspaceMemberService(member_repo, workspace_repo, user_repo, task_repo)


# --- update_role: só o Owner promove/rebaixa; Owner nunca é alvo -------------


def test_owner_can_promote_member_to_admin(service, member_repo, user_repo) -> None:
    workspace_id, owner_id, member_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    member_repo.seed(workspace_id, owner_id, WorkspaceRole.OWNER)
    member_repo.seed(workspace_id, member_id, WorkspaceRole.MEMBER)
    user_repo.seed(member_id, email="member@example.com")

    result = service.update_role(workspace_id, member_id, WorkspaceRole.ADMIN)

    assert result.role == WorkspaceRole.ADMIN


def test_update_role_rejects_owner_as_target(service, member_repo) -> None:
    workspace_id, owner_id = uuid.uuid4(), uuid.uuid4()
    member_repo.seed(workspace_id, owner_id, WorkspaceRole.OWNER)

    with pytest.raises(ForbiddenError):
        service.update_role(workspace_id, owner_id, WorkspaceRole.ADMIN)


def test_update_role_missing_member_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.update_role(uuid.uuid4(), uuid.uuid4(), WorkspaceRole.ADMIN)


# --- remove_member: hierarquia de quem pode remover quem --------------------


def test_remove_member_rejects_owner_target(service, member_repo) -> None:
    workspace_id, owner_id = uuid.uuid4(), uuid.uuid4()
    member_repo.seed(workspace_id, owner_id, WorkspaceRole.OWNER)

    with pytest.raises(ForbiddenError):
        service.remove_member(workspace_id, owner_id, caller_role=WorkspaceRole.OWNER)


def test_remove_admin_requires_caller_to_be_owner(service, member_repo) -> None:
    workspace_id, admin_id = uuid.uuid4(), uuid.uuid4()
    member_repo.seed(workspace_id, admin_id, WorkspaceRole.ADMIN)

    with pytest.raises(ForbiddenError):
        service.remove_member(workspace_id, admin_id, caller_role=WorkspaceRole.ADMIN)


def test_owner_can_remove_admin(service, member_repo) -> None:
    workspace_id, admin_id = uuid.uuid4(), uuid.uuid4()
    member_repo.seed(workspace_id, admin_id, WorkspaceRole.ADMIN)

    service.remove_member(workspace_id, admin_id, caller_role=WorkspaceRole.OWNER)

    assert member_repo.get_role(workspace_id, admin_id) is None


def test_remove_member_blocked_by_active_tasks(service, member_repo, task_repo) -> None:
    workspace_id, member_id = uuid.uuid4(), uuid.uuid4()
    member_repo.seed(workspace_id, member_id, WorkspaceRole.MEMBER)
    task_repo.active_tasks = [_FakeActiveTask(id=uuid.uuid4(), title="Tarefa ativa")]

    with pytest.raises(ConflictError):
        service.remove_member(workspace_id, member_id, caller_role=WorkspaceRole.OWNER)


# --- transfer_ownership: reconfirmação sob lock + candidato deve ser membro --


def test_transfer_ownership_rejects_when_caller_is_not_current_owner(
    service, member_repo, workspace_repo
) -> None:
    workspace_id = uuid.uuid4()
    real_owner_id, impostor_id, candidate_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    member_repo.seed(workspace_id, real_owner_id, WorkspaceRole.OWNER)
    member_repo.seed(workspace_id, candidate_id, WorkspaceRole.MEMBER)
    workspace_repo.seed(workspace_id)

    with pytest.raises(ConflictError):
        service.transfer_ownership(workspace_id, impostor_id, candidate_id)


def test_transfer_ownership_rejects_non_member_candidate(service, member_repo, workspace_repo) -> None:
    workspace_id, owner_id = uuid.uuid4(), uuid.uuid4()
    member_repo.seed(workspace_id, owner_id, WorkspaceRole.OWNER)
    workspace_repo.seed(workspace_id)

    with pytest.raises(BusinessRuleViolationError):
        service.transfer_ownership(workspace_id, owner_id, uuid.uuid4())


def test_transfer_ownership_success_flips_roles(service, member_repo, workspace_repo) -> None:
    workspace_id, owner_id, candidate_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    member_repo.seed(workspace_id, owner_id, WorkspaceRole.OWNER)
    member_repo.seed(workspace_id, candidate_id, WorkspaceRole.MEMBER)
    workspace_repo.seed(workspace_id)

    result = service.transfer_ownership(workspace_id, owner_id, candidate_id)

    assert result.my_role == WorkspaceRole.ADMIN
    assert member_repo.get_role(workspace_id, owner_id) == WorkspaceRole.ADMIN
    assert member_repo.get_role(workspace_id, candidate_id) == WorkspaceRole.OWNER
