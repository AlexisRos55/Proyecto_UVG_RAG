from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.shared.exceptions.domain_errors import (
    DomainError,
    DuplicateUserError,
    InvalidCredentialsError,
    InvalidEmailDomainError,
    NotFoundError,
    UnauthorizedError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Translates domain exceptions into HTTP responses (docs/04-software-architecture.md, section 4).

    Routers never catch these themselves: a single, centralized mapping keeps that
    policy in one place instead of scattered across every endpoint.
    """

    @app.exception_handler(InvalidCredentialsError)
    async def _invalid_credentials(_: Request, exc: InvalidCredentialsError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(UnauthorizedError)
    async def _unauthorized(_: Request, exc: UnauthorizedError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(InvalidEmailDomainError)
    async def _invalid_email_domain(_: Request, exc: InvalidEmailDomainError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(DuplicateUserError)
    async def _duplicate_user(_: Request, exc: DuplicateUserError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
