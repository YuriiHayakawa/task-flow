from pydantic import BaseModel


class DashboardCounts(BaseModel):
    pending: int
    in_progress: int
    done: int
    overdue: int
    due_today: int


class DashboardSummary(BaseModel):
    """Resposta de `GET /api/v1/dashboard` (contracts/dashboard-and-notifications.md)."""

    counts: DashboardCounts
