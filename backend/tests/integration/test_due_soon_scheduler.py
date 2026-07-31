"""T102 [US11] — impede execução simultânea do job `DUE_SOON`: uma "segunda
instância" simulada mantém o advisory lock manualmente; `run_due_soon_job()`
detecta que o lock já está em uso e não processa nada; liberado o lock, uma
nova chamada processa normalmente.

Cobre: research.md #2 ("Como evitar execução duplicada").

MUST usar conexões independentes reais (não a `db_session` compartilhada da
fixture) — mesmo padrão de `test_workspace_ownership.py`: dados de apoio são
criados e commitados de verdade numa conexão própria, pois `run_due_soon_job`
abre sua PRÓPRIA conexão via `engine.connect()` e não enxergaria nada criado
numa transação não commitada."""

import uuid
from datetime import date

from sqlalchemy import create_engine, insert, text

from app.core.config import settings
from app.core.scheduler import run_due_soon_job
from app.core.security import hash_password
from app.enums.task_priority import TaskPriority
from app.enums.task_status import TaskStatus
from app.models.task import Task
from app.models.user import User


def _setup_committed_task_due_today() -> uuid.UUID:
    """Cria usuário e tarefa com prazo vencendo hoje numa transação própria,
    commitada de verdade — precisa estar visível para a conexão
    independente que `run_due_soon_job()` abre."""
    engine = create_engine(settings.DATABASE_URL)
    user_id = uuid.uuid4()
    task_id = uuid.uuid4()
    with engine.begin() as connection:
        connection.execute(
            insert(User),
            [
                {
                    "id": user_id,
                    "name": "Usuario Due Soon Scheduler",
                    "email": f"due-soon-scheduler-{user_id}@example.com",
                    "password_hash": hash_password("supersecret123"),
                    "is_active": True,
                    "is_system_admin": False,
                }
            ],
        )
        connection.execute(
            insert(Task),
            [
                {
                    "id": task_id,
                    "title": "Tarefa Due Soon Scheduler",
                    "status": TaskStatus.PENDING,
                    "priority": TaskPriority.MEDIUM,
                    "due_date": date.today(),
                    "assignee_id": user_id,
                    "creator_id": user_id,
                    "workspace_id": None,
                    "project_id": None,
                }
            ],
        )
    engine.dispose()
    return task_id


def test_run_due_soon_job_skips_when_lock_already_held(db_session):
    task_id = _setup_committed_task_due_today()

    lock_engine = create_engine(settings.DATABASE_URL)
    lock_connection = lock_engine.connect()
    lock_connection.execute(
        text("SELECT pg_advisory_lock(:key)"), {"key": settings.DUE_SOON_LOCK_KEY}
    )
    try:
        run_due_soon_job()  # deve retornar cedo, sem processar nada

        task = db_session.get(Task, task_id)
        assert task is not None
        assert task.due_soon_notified_for is None
    finally:
        lock_connection.execute(
            text("SELECT pg_advisory_unlock(:key)"), {"key": settings.DUE_SOON_LOCK_KEY}
        )
        lock_connection.close()
        lock_engine.dispose()


def test_run_due_soon_job_processes_normally_after_lock_released(db_session):
    task_id = _setup_committed_task_due_today()

    lock_engine = create_engine(settings.DATABASE_URL)
    lock_connection = lock_engine.connect()
    lock_connection.execute(
        text("SELECT pg_advisory_lock(:key)"), {"key": settings.DUE_SOON_LOCK_KEY}
    )
    run_due_soon_job()  # bloqueado enquanto o lock manual está ativo
    lock_connection.execute(
        text("SELECT pg_advisory_unlock(:key)"), {"key": settings.DUE_SOON_LOCK_KEY}
    )
    lock_connection.close()
    lock_engine.dispose()

    run_due_soon_job()  # agora o lock está livre — processa normalmente

    task = db_session.get(Task, task_id)
    assert task is not None
    assert task.due_soon_notified_for == task.due_date
