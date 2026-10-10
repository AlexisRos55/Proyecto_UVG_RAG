from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.dto.auth_dto import LoginRequest, RegisterStudentRequest
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.application.use_cases.register_student import RegisterStudentUseCase
from app.application.use_cases.start_guest_session import StartGuestSessionUseCase
from app.infrastructure.entrypoints.api.dependencies import (
    get_authenticate_use_case,
    get_register_use_case,
    get_start_guest_session_use_case,
)
from app.infrastructure.entrypoints.api.schemas.auth_schemas import (
    AuthResponseSchema,
    LoginRequestSchema,
    RegisterRequestSchema,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponseSchema, status_code=201)
async def register(
    payload: RegisterRequestSchema,
    use_case: Annotated[RegisterStudentUseCase, Depends(get_register_use_case)],
) -> AuthResponseSchema:
    session = await use_case.execute(
        RegisterStudentRequest(email=payload.email, plain_password=payload.password)
    )
    return AuthResponseSchema.from_session(session)


@router.post("/login", response_model=AuthResponseSchema)
async def login(
    payload: LoginRequestSchema,
    use_case: Annotated[AuthenticateUserUseCase, Depends(get_authenticate_use_case)],
) -> AuthResponseSchema:
    session = await use_case.execute(
        LoginRequest(email=payload.email, plain_password=payload.password)
    )
    return AuthResponseSchema.from_session(session)


@router.post("/guest", response_model=AuthResponseSchema, status_code=201)
async def start_guest_session(
    use_case: Annotated[StartGuestSessionUseCase, Depends(get_start_guest_session_use_case)],
) -> AuthResponseSchema:
    """Modo invitado (ADR-0019): sesión temporal sin correo ni contraseña."""
    return AuthResponseSchema.from_session(await use_case.execute())
