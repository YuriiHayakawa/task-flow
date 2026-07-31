"""T113 [US13] — testes unitários de `AdminService`: listagem paginada,
filtro por `is_active`, ativação/desativação, isolado do banco via
repository em memória (Fake), mesmo padrão de outros Services desta base."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.services.admin_service import AdminService


class _FakeSession:
    def commit(self) -> None:
        pass

    def refresh(self, _obj: object) -> None:
        pass


class FakeUserRepository:
    def __init__(self) -> None:
        self.db = _FakeSession()
        self.users: dict[uuid.UUID, User] = {}
        self._next_created_at = datetime.now(timezone.utc)

    def seed(
        self,
        *,
        name: str = "Usuário",
        email: str = "user@example.com",
        is_active: bool = True,
    ) -> User:
        user = User(
            id=uuid.uuid4(),
            name=name,
            email=email,
            password_hash="hash",
            is_active=is_active,
            is_system_admin=False,
        )
        user.created_at = self._next_created_at
        self._next_created_at += timedelta(seconds=1)
        self.users[user.id] = user
        return user

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.users.get(user_id)

    def update(self, user: User) -> User:
        return user

    def list_all(
        self, *, is_active: bool | None, page: int, page_size: int
    ) -> tuple[list[User], int]:
        items = sorted(self.users.values(), key=lambda u: (u.created_at, u.id))
        if is_active is not None:
            items = [user for user in items if user.is_active == is_active]
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total


@pytest.fixture()
def user_repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture()
def admin_service(user_repo: FakeUserRepository) -> AdminService:
    return AdminService(user_repo)


# --- list_users --------------------------------------------------------------


def test_list_users_returns_all_when_no_filter(admin_service: AdminService, user_repo: FakeUserRepository) -> None:
    user_repo.seed(name="Ana", email="ana@example.com")
    user_repo.seed(name="Beto", email="beto@example.com")

    items, total = admin_service.list_users(is_active=None, page=1, page_size=20)

    assert total == 2
    assert len(items) == 2


def test_list_users_filters_by_is_active_true(admin_service: AdminService, user_repo: FakeUserRepository) -> None:
    user_repo.seed(name="Ativo", email="ativo@example.com", is_active=True)
    user_repo.seed(name="Inativo", email="inativo@example.com", is_active=False)

    items, total = admin_service.list_users(is_active=True, page=1, page_size=20)

    assert total == 1
    assert items[0].name == "Ativo"


def test_list_users_filters_by_is_active_false(admin_service: AdminService, user_repo: FakeUserRepository) -> None:
    user_repo.seed(name="Ativo", email="ativo2@example.com", is_active=True)
    user_repo.seed(name="Inativo", email="inativo2@example.com", is_active=False)

    items, total = admin_service.list_users(is_active=False, page=1, page_size=20)

    assert total == 1
    assert items[0].name == "Inativo"


def test_list_users_paginates(admin_service: AdminService, user_repo: FakeUserRepository) -> None:
    for i in range(5):
        user_repo.seed(name=f"Usuario {i}", email=f"usuario{i}@example.com")

    first_page, total = admin_service.list_users(is_active=None, page=1, page_size=2)
    second_page, _ = admin_service.list_users(is_active=None, page=2, page_size=2)

    assert total == 5
    assert len(first_page) == 2
    assert len(second_page) == 2
    assert {u.id for u in first_page}.isdisjoint({u.id for u in second_page})


def test_list_users_empty_when_no_users(admin_service: AdminService) -> None:
    items, total = admin_service.list_users(is_active=None, page=1, page_size=20)

    assert items == []
    assert total == 0


# --- set_user_active -----------------------------------------------------------


def test_set_user_active_deactivates(admin_service: AdminService, user_repo: FakeUserRepository) -> None:
    user = user_repo.seed(is_active=True)

    updated = admin_service.set_user_active(user.id, False)

    assert updated.is_active is False


def test_set_user_active_reactivates(admin_service: AdminService, user_repo: FakeUserRepository) -> None:
    user = user_repo.seed(is_active=False)

    updated = admin_service.set_user_active(user.id, True)

    assert updated.is_active is True


def test_set_user_active_nonexistent_raises_not_found(admin_service: AdminService) -> None:
    with pytest.raises(NotFoundError):
        admin_service.set_user_active(uuid.uuid4(), False)
