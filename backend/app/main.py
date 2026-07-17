from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.scheduler import start_scheduler, stop_scheduler
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.tasks import router as tasks_router
from app.routes.workspace_members import router as workspace_members_router
from app.routes.workspaces import router as workspaces_router


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
api_router.include_router(auth_router)
api_router.include_router(tasks_router)
api_router.include_router(dashboard_router)
api_router.include_router(workspaces_router)
api_router.include_router(workspace_members_router)
app.include_router(api_router)
