import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.database.connection import engine
from app.repositories.notification_repository import NotificationRepository
from app.repositories.task_repository import TaskRepository
from app.services.notification_service import NotificationService

logger = get_logger(__name__)


def run_due_soon_job() -> None:
    """Execução síncrona de um tick do job periódico DUE_SOON (T105,
    research.md #2). Roda em uma thread do executor padrão via
    `asyncio.to_thread` (nunca diretamente na coroutine do loop principal —
    o código de negócio usa uma Sessão síncrona do SQLAlchemy e faria I/O
    bloqueante ali).

    Fluxo (research.md #2):
    1. Abre uma conexão dedicada — o advisory lock é vinculado à conexão
       física, que precisa permanecer aberta entre o LOCK e o UNLOCK.
    2. Tenta obter o lock (`pg_try_advisory_lock`); se outra execução já o
       detém, encerra sem processar nada (log `DEBUG`) — a conexão ainda é
       fechada no `finally` mais externo, mas o `UNLOCK` nunca é tentado
       (nunca liberamos um lock que não obtivemos).
    3. Se obtido, encerra explicitamente a transação implícita que o
       `SELECT pg_try_advisory_lock` acabou de abrir na conexão
       (`connection.commit()` — inofensivo: locks obtidos via
       `pg_try_advisory_lock`/`pg_advisory_lock`, ao contrário das variantes
       `_xact`, não são afetados por commit/rollback, só por unlock
       explícito ou fechamento da conexão). Sem isso, a `Session` criada no
       próximo passo "aderiria" a essa transação já em andamento em vez de
       possuí-la, e `session.commit()` não commitaria de verdade no
       Postgres — um bug real encontrado durante o teste de concorrência
       deste bloco (T102).
    4. Cria uma `Session` própria desta execução, vinculada à mesma conexão
       (agora livre de transação pendente).
    5. Gera as notificações `DUE_SOON` dentro de `try/except/finally`:
       sucesso → `commit()`; exceção → loga `ERROR` e reverte; em ambos os
       casos, a Session é sempre fechada ao final.
    6. Sempre (quando o lock foi obtido), em um `finally` externo aos passos
       4-5, libera o lock.
    7. Em um `finally` mais externo ainda, fecha a conexão — sempre, com ou
       sem lock obtido."""
    connection = engine.connect()
    try:
        got_lock = connection.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": settings.DUE_SOON_LOCK_KEY}
        ).scalar()
        if not got_lock:
            logger.debug("run_due_soon_job: lock não obtido, outra execução já está em andamento")
            return

        connection.commit()  # encerra a transação implícita do SELECT acima

        try:
            session = Session(bind=connection)
            try:
                service = NotificationService(
                    NotificationRepository(session), TaskRepository(session)
                )
                now = datetime.now(ZoneInfo(settings.APP_TIMEZONE))
                created = service.generate_due_soon_notifications(now=now)
                session.commit()
                logger.info(
                    "run_due_soon_job: concluído, %d notificação(ões) criada(s)", created
                )
            except Exception:
                session.rollback()
                logger.exception("run_due_soon_job: falha ao gerar notificações DUE_SOON")
            finally:
                session.close()
        finally:
            connection.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": settings.DUE_SOON_LOCK_KEY}
            )
    finally:
        connection.close()


async def due_soon_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(run_due_soon_job)
        except Exception:
            logger.exception("Falha ao executar o job periódico DUE_SOON")
        await asyncio.sleep(settings.DUE_SOON_CHECK_INTERVAL_SECONDS)


async def start_scheduler() -> asyncio.Task[None]:
    return asyncio.create_task(due_soon_loop())


async def stop_scheduler(task: asyncio.Task[None]) -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
