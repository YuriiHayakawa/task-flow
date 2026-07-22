"""Fixtures compartilhadas de teste (T036).

ATENÇÃO: `DATABASE_URL` (via `.env`/ambiente) MUST apontar para um banco Postgres
descartável dedicado a testes ao rodar esta suíte — a fixture de sessão aplica
`alembic upgrade head` no início e `alembic downgrade base` no final. Nunca aponte
para o banco de desenvolvimento.
"""

from collections.abc import Generator
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.database.session import get_db
from app.enums.task_priority import TaskPriority
from app.enums.task_status import TaskStatus
from app.enums.workspace_role import WorkspaceRole
from app.main import app
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember

BACKEND_DIR = Path(__file__).resolve().parent.parent
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"

# Nomes de banco que a suíte MUST NOT tocar sob nenhuma hipótese — "taskflow" é o
# banco de desenvolvimento (as mesmas migrações são aplicadas nele fora dos testes).
_FORBIDDEN_DATABASE_NAMES = {"taskflow", "postgres", "template0", "template1"}


def _guard_test_database_or_abort(database_url: str) -> str:
    """Aborta a sessão inteira de testes (antes de qualquer migração/DDL) se
    `DATABASE_URL` não apontar claramente para um banco de testes descartável.

    Regra: o nome do banco MUST NOT ser um dos bancos reservados (`taskflow`,
    `postgres`, `template0/1`) e MUST conter "test" no nome (ex.: `taskflow_test`).
    Isso nunca deve depender apenas de o desenvolvedor lembrar de configurar a
    variável de ambiente certa — a suíte recusa-se a rodar sem essa confirmação.
    """
    database_name = (make_url(database_url).database or "").lower()

    if not database_name or database_name in _FORBIDDEN_DATABASE_NAMES or "test" not in database_name:
        pytest.exit(
            "ABORTADO: DATABASE_URL não aponta para um banco de teste reconhecível "
            f"(banco detectado: {database_name!r}). Esperado algo como 'taskflow_test'. "
            "A suíte nunca deve rodar migrações destrutivas (alembic downgrade base) "
            "contra o banco de desenvolvimento 'taskflow'.",
            returncode=1,
        )
    return database_name


@pytest.fixture(scope="session")
def _migrated_database() -> Generator[None, None, None]:
    """Aplica as 4 migrações agrupadas uma única vez para toda a sessão de testes,
    e reverte tudo ao final. Só executa depois de confirmar que `DATABASE_URL`
    aponta para um banco de teste descartável (nunca o de desenvolvimento)."""
    _guard_test_database_or_abort(settings.DATABASE_URL)
    alembic_cfg = Config(str(ALEMBIC_INI))
    command.upgrade(alembic_cfg, "head")
    yield
    command.downgrade(alembic_cfg, "base")


@pytest.fixture()
def db_session(_migrated_database: None) -> Generator[Session, None, None]:
    """Cada teste roda dentro de uma transação isolada, revertida ao final — garante
    independência entre testes sem precisar remigrar o schema a cada um."""
    engine = create_engine(settings.DATABASE_URL)
    connection: Connection = engine.connect()
    transaction = connection.begin()
    testing_session_local = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = testing_session_local()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """`TestClient` com `get_db` sobrescrito para compartilhar a mesma transação
    isolada do teste — o que a rota grava é visível às asserções do teste."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db_session: Session):
    def _make_user(
        *,
        name: str = "Test User",
        email: str = "user@example.com",
        password: str = "supersecret123",
        is_active: bool = True,
        is_system_admin: bool = False,
    ) -> User:
        user = User(
            name=name,
            email=email.lower(),
            password_hash=hash_password(password),
            is_active=is_active,
            is_system_admin=is_system_admin,
        )
        db_session.add(user)
        db_session.flush()
        return user

    return _make_user


@pytest.fixture()
def make_workspace(db_session: Session):
    def _make_workspace(
        *, owner: User, name: str = "Test Workspace", description: str | None = None
    ) -> Workspace:
        workspace = Workspace(name=name, description=description)
        db_session.add(workspace)
        db_session.flush()

        membership = WorkspaceMember(
            workspace_id=workspace.id, user_id=owner.id, role=WorkspaceRole.OWNER
        )
        db_session.add(membership)
        db_session.flush()
        return workspace

    return _make_workspace


@pytest.fixture()
def add_workspace_member(db_session: Session):
    def _add_workspace_member(
        *, workspace: Workspace, user: User, role: WorkspaceRole = WorkspaceRole.MEMBER
    ) -> WorkspaceMember:
        membership = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=role)
        db_session.add(membership)
        db_session.flush()
        return membership

    return _add_workspace_member


@pytest.fixture()
def make_project(db_session: Session):
    def _make_project(
        *, workspace: Workspace, name: str = "Test Project", description: str | None = None
    ) -> Project:
        project = Project(workspace_id=workspace.id, name=name, description=description)
        db_session.add(project)
        db_session.flush()
        return project

    return _make_project


@pytest.fixture()
def make_task(db_session: Session):
    def _make_task(
        *,
        creator: User,
        assignee: User | None = None,
        title: str = "Test Task",
        workspace: Workspace | None = None,
        project: Project | None = None,
        status: TaskStatus = TaskStatus.PENDING,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: date | None = None,
    ) -> Task:
        resolved_workspace_id = workspace.id if workspace else (project.workspace_id if project else None)
        task = Task(
            title=title,
            creator_id=creator.id,
            assignee_id=(assignee or creator).id,
            workspace_id=resolved_workspace_id,
            project_id=project.id if project else None,
            status=status,
            priority=priority,
            due_date=due_date,
        )
        db_session.add(task)
        db_session.flush()
        return task

    return _make_task


@pytest.fixture()
def auth_headers():
    def _auth_headers(user: User) -> dict[str, str]:
        token = create_access_token(str(user.id))
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers
