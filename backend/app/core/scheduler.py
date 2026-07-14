import asyncio

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def run_due_soon_job() -> None:
    """Placeholder — lógica real chega na Fase 13 (US11), quando
    NotificationService.generate_due_soon_notifications() existir (research.md #2).
    Até lá, o loop roda sem efeito colateral algum."""
    logger.debug("run_due_soon_job: placeholder, NotificationService ainda não implementado")


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
