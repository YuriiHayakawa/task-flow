from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    scheduler_task = await start_scheduler()
    try:
        yield
    finally:
        await stop_scheduler(scheduler_task)


app = FastAPI(title="TaskFlow API", lifespan=lifespan)

register_exception_handlers(app)

# Mount point único para todas as rotas de negócio (Fases 3+) — evita repetir
# prefix="/api/v1" em cada app.include_router(...) futuro.
api_router = APIRouter(prefix="/api/v1")
app.include_router(api_router)
