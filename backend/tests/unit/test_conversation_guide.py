"""Cómo acompaña el asistente: ofrecimientos, abstenciones útiles y reanudación (Fase 9.2)."""

from __future__ import annotations

from app.domain.services import conversation_guide as guide

AVAILABLE = ["requisitos", "cobertura", "procedimiento", "condiciones", "consecuencias", "plazo", "integrantes"]


def test_aspects_are_detected_from_article_titles() -> None:
    titles = ["Artículo 16. Requisitos", "Artículo 17. Cobertura", "Artículo 40. Sanciones"]
    assert guide.available_aspects(titles) == ["requisitos", "cobertura", "consecuencias"]


def test_the_offer_skips_what_was_already_asked_and_is_short() -> None:
    line = guide.offer_line(AVAILABLE, ("requisitos",))
    assert line == "Si quieres, también puedo explicarte la cobertura, cómo se solicita o las condiciones para mantenerla."


def test_the_system_offer_replaces_the_model_offer() -> None:
    answer = "Hay tres programas.\n\n¿Quieres conocer más detalles sobre alguno?"
    closed = guide.close_with_offer(answer, "Si quieres, también puedo explicarte los requisitos.")
    assert closed == "Hay tres programas.\n\nSi quieres, también puedo explicarte los requisitos."
    # Una respuesta de un solo párrafo nunca se recorta.
    assert guide.close_with_offer("¿Sabías que…?", "Oferta.").startswith("¿Sabías")
    assert guide.close_with_offer("Sin oferta.", "") == "Sin oferta."


def test_a_helpful_abstention_says_what_the_regulation_does_cover_briefly() -> None:
    text = guide.abstention("el cambio de carrera", "plazo", AVAILABLE, repeated=False)
    assert text.startswith("No encontré en la normativa una disposición que establezca los plazos del cambio de carrera.")
    described = text.split("Sí describe ")[1].split(".")[0]
    assert described.count(",") <= 1  # como máximo tres aspectos
    assert "«¿Cuáles son los requisitos del cambio de carrera?»" in text


def test_repeated_abstentions_shorten_redirect_and_never_echo() -> None:
    texts = [
        guide.abstention("el seguro estudiantil", "cobertura", [], repeated=streak > 0, corpus_overview="las becas", streak=streak)
        for streak in range(5)
    ]
    assert "tampoco" in texts[1]
    assert "Puedo ayudarte, en cambio, con las becas" in texts[2]
    assert len(set(texts)) == len(texts)
    assert all("seguro estudiantil" in text for text in texts)
    assert "de el " not in " ".join(texts)


def test_resume_recaps_and_offers_what_is_pending() -> None:
    text = guide.resume("las becas", ["requisitos"], AVAILABLE)
    assert text.startswith("Claro, sigamos con las becas. Hasta ahora vimos los requisitos.")
    assert "¿Qué te interesa?" in text


# --- Fase 10 --------------------------------------------------------------------------

MENU = (("las becas y ayudas financieras", "¿Qué becas hay para estudiantes del Altiplano?"), ("el calendario académico", "¿Cuándo inician las clases?"))


def test_a_lost_student_gets_concrete_questions_or_the_active_topic() -> None:
    fresh = guide.orientation(None, [], MENU)
    assert "«¿Qué becas hay para estudiantes del Altiplano?»" in fresh
    with_focus = guide.orientation("las becas y ayudas financieras", ["requisitos", "cobertura"], MENU)
    assert with_focus.startswith("Vamos paso a paso. Estábamos viendo las becas y ayudas financieras")
    assert "qué se necesita" in with_focus


def test_the_overview_offer_is_framed_by_goals_and_invites_personalisation() -> None:
    offer = guide.overview_offer(AVAILABLE, (), has_options=True)
    assert offer.startswith("¿Por dónde seguimos? Puedo contarte qué se necesita, cuánto cubre cada opción o cómo se tramita.")
    assert "Si me cuentas tu situación" in offer
    assert "Si me cuentas" not in guide.overview_offer(AVAILABLE, (), has_options=False)


def test_offers_skip_what_the_answer_already_explained() -> None:
    answer = "Cubre hasta el 50 % de las cuotas. Si incumples las políticas, pierdes el derecho."
    pending = guide.not_in_answer(["cobertura", "consecuencias", "requisitos"], answer)
    assert pending == ["requisitos"]


def test_example_questions_agree_in_number_and_contract() -> None:
    assert guide.example_question("procedimiento", "las Becas Trasciende") == "¿Cómo se solicitan las Becas Trasciende?"
    assert guide.example_question("requisitos", "el cambio de carrera") == "¿Cuáles son los requisitos del cambio de carrera?"


def test_premium_abstention_names_the_document_the_office_and_the_next_question() -> None:
    text = guide.abstention(
        "las Becas Trasciende", "plazo", AVAILABLE, repeated=False, covered=("requisitos",),
        document="Reglamento de ayudas financieras", office="la Dirección de Ayudas Financieras",
    )
    assert text.startswith("No encontré en el Reglamento de ayudas financieras una disposición que establezca los plazos de las Becas Trasciende.")
    assert "consultarlo con la Dirección de Ayudas Financieras" in text
    assert "«¿Cuánto cubren las Becas Trasciende?»" in text  # lo siguiente aún no tratado


def test_a_topic_mentioned_only_in_passing_is_described_precisely() -> None:
    text = guide.abstention(
        "el cambio de carrera", "duracion", ["cobertura", "consecuencias"], repeated=False,
        document="Reglamento de ayudas financieras", incidental=True,
    )
    assert text.startswith("El Reglamento de ayudas financieras menciona el cambio de carrera solo de paso")
    assert "por ejemplo" not in text  # no se sugieren preguntas que no tienen sentido para el tema


def test_an_uncovered_topic_never_says_no_information_and_opens_paths() -> None:
    text = guide.abstention("el seguro estudiantil", "cobertura", [], repeated=False, alternatives=MENU)
    assert not text.startswith("No encontré")
    assert "no forma parte de la documentación oficial" in text
    assert "«¿Qué becas hay para estudiantes del Altiplano?»" in text


def test_an_unmatched_message_asks_for_other_words_with_examples() -> None:
    text = guide.unmatched(MENU, struggling=False)
    assert "con otras palabras" in text and "Por ejemplo" in text
