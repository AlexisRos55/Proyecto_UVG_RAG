import pytest

from app.domain.value_objects.verified_answer import VerificationConfidence
from app.infrastructure.adapters.llm.single_call_verification_adapter import (
    SingleCallVerificationAdapter,
)
from app.shared.exceptions.domain_errors import VerificationFailedError
from tests.fakes.fake_llm_port import FakeLLMPort
from tests.fakes.fake_rag_ports import make_retrieved_chunk


@pytest.mark.asyncio
async def test_parses_grounded_answer_from_structured_output() -> None:
    llm = FakeLLMPort(
        response_content={
            "answer_text": "El proceso de reincorporación se solicita en la oficina de registro.",
            "is_grounded": True,
            "confidence": "high",
            "unsupported_claims": [],
        }
    )
    adapter = SingleCallVerificationAdapter(llm_port=llm)
    chunks = [make_retrieved_chunk("Reincorporación: art. 12...", score=0.9)]

    result = await adapter.answer("¿Cómo me reincorporo?", chunks)

    assert result.is_grounded is True
    assert result.confidence is VerificationConfidence.HIGH
    assert "reincorporación" in result.answer_text.lower()
    assert llm.call_count == 1  # ADR-0005: una sola llamada


@pytest.mark.asyncio
async def test_parses_non_grounded_answer_with_unsupported_claims() -> None:
    llm = FakeLLMPort(
        response_content={
            "answer_text": "No puedo confirmar el monto exacto de la beca.",
            "is_grounded": False,
            "confidence": "low",
            "unsupported_claims": ["monto exacto de la beca"],
        }
    )
    adapter = SingleCallVerificationAdapter(llm_port=llm)
    chunks = [make_retrieved_chunk("Existen becas disponibles.", score=0.5)]

    result = await adapter.answer("¿Cuánto cubre la beca?", chunks)

    assert result.is_grounded is False
    assert result.unsupported_claims == ("monto exacto de la beca",)


@pytest.mark.asyncio
async def test_includes_all_context_chunks_in_the_prompt() -> None:
    llm = FakeLLMPort(
        response_content={
            "answer_text": "x",
            "is_grounded": True,
            "confidence": "medium",
            "unsupported_claims": [],
        }
    )
    adapter = SingleCallVerificationAdapter(llm_port=llm)
    chunks = [
        make_retrieved_chunk("Fragmento uno sobre seguros.", score=0.8),
        make_retrieved_chunk("Fragmento dos sobre becas.", score=0.7),
    ]

    await adapter.answer("¿Qué cubre el seguro?", chunks)

    assert "Fragmento uno sobre seguros." in llm.last_user_prompt
    assert "Fragmento dos sobre becas." in llm.last_user_prompt
    assert "¿Qué cubre el seguro?" in llm.last_user_prompt


@pytest.mark.asyncio
async def test_raises_verification_failed_error_on_malformed_output() -> None:
    llm = FakeLLMPort(response_content={"answer_text": "incompleto"})
    adapter = SingleCallVerificationAdapter(llm_port=llm)
    chunks = [make_retrieved_chunk("contexto", score=0.9)]

    with pytest.raises(VerificationFailedError):
        await adapter.answer("pregunta", chunks)
