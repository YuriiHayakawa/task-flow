from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def today_in_app_timezone() -> date:
    """"Hoje" calculado na timezone da aplicação (`APP_TIMEZONE`), nunca em UTC
    puro (research.md #9) — evita que a virada de dia em UTC produza um "hoje"
    incorreto para usuários no fuso configurado. Reaproveitado pelo job
    periódico `DUE_SOON` (US11, research.md #2), evitando lógica de tempo
    duplicada."""
    return datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()
