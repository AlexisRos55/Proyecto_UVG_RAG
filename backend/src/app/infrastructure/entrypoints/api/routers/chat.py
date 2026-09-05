from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.dto.chat_dto import AnswerQueryRequest
from app.application.use_cases.answer_student_query import AnswerStudentQueryUseCase
from app.domain.entities.user import User
from app.domain.ports.conversation_repository_port import ConversationRepositoryPort
from app.infrastructure.entrypoints.api.dependencies import (
    get_answer_query_use_case,
    get_conversation_repository,
    get_current_user,
)
from app.infrastructure.entrypoints.api.schemas.chat_schemas import (
    AnswerResponseSchema,
    AskQuestionRequestSchema,
    ConversationSchema,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=AnswerResponseSchema)
async def ask_question(
    payload: AskQuestionRequestSchema,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[AnswerStudentQueryUseCase, Depends(get_answer_query_use_case)],
) -> AnswerResponseSchema:
    response = await use_case.execute(
        AnswerQueryRequest(user_id=current_user.id, question=payload.question)
    )
    return AnswerResponseSchema.from_dto(response)


@router.get("/history", response_model=list[ConversationSchema])
async def get_history(
    current_user: Annotated[User, Depends(get_current_user)],
    conversation_repository: Annotated[
        ConversationRepositoryPort, Depends(get_conversation_repository)
    ],
) -> list[ConversationSchema]:
    conversations = await conversation_repository.get_history(current_user.id)
    return [ConversationSchema.from_entity(c) for c in conversations]
