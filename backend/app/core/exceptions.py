from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base para exceções de domínio traduzidas para o envelope de erro padrão
    (Constitution X) — rotas nunca tratam essas exceções ad-hoc, apenas as levantam."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "BUSINESS_RULE_VIOLATION"

    def __init__(self, message: str, details: list[dict[str, Any]] | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class NotAuthenticatedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "NOT_AUTHENTICATED"


class InvalidCredentialsError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "INVALID_CREDENTIALS"


class AccountDisabledError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "ACCOUNT_DISABLED"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"


class BusinessRuleViolationError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "BUSINESS_RULE_VIOLATION"


def _error_response(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(loc) for loc in error["loc"]), "issue": error["msg"]}
            for error in exc.errors()
        ]
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "Dados inválidos.",
            details,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.error("Erro interno não tratado: %s", exc.__class__.__name__)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "Erro interno do servidor.",
        )
